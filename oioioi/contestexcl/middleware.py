from django.conf import settings
from django.contrib import auth, messages
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.mail import mail_admins
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils import ObjectWithMixins, is_ajax
from oioioi.base.utils.loaders import load_modules
from oioioi.contestexcl.models import ExclusivenessConfig
from oioioi.contests.middleware import activate_contest
from oioioi.contests.models import Contest


class ExclusiveContestsMiddleware(ObjectWithMixins):
    """Middleware which checks whether the user participate in an
    exclusive contest, which is a contest that blocks other contests,
    and sets the current contest to that contest.

    It works as follows:

    #. If ONLY_DEFAULT_CONTEST is set, only the default contest is taken
       into account.
    #. All contests with active
       :class:`~oioioi.contestexcl.models.ExclusivenessConfig` instance are
       acquired from the database.
    #. They are filtered with a special selector function, which by default
       checks if the user is not a contest admin. In addition,
       ``process_view`` accepts another selector function as an argument.
       If it is present, the contest list is filtered with a logical
       conjunction of the default selector and the selector passed
       as an argument (it may be useful with mixins).
    #. If there is only one contest left, the ``request.contest`` variable
       is set to this contest or a redirect is made if necessary.
    #. If there is more than one contest left, the user is logged out,
       an error message is displayed and an e-mail describing the situation
       is sent to the administrators.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs, selector=None):

        if not self._check_requirements(request):
            return

        def _default_selector(user, contest):
            return not user.has_perm('contests.contest_admin', contest)

        if selector is None:
            final_selector = _default_selector
        else:
            final_selector = lambda user, contest: _default_selector(
                user, contest
            ) and selector(user, contest)

        if settings.ONLY_DEFAULT_CONTEST and \
                (request.user is None or not request.user.is_superuser):
            qs = [Contest.objects.get(id=settings.DEFAULT_CONTEST)]
        else:
            qs = ExclusivenessConfig.objects.get_active(
                request.timestamp
            ).select_related('contest')
            qs = [ex_cf.contest for ex_cf in qs]
            qs = [cnst for cnst in qs if final_selector(request.user, cnst)]

        if len(qs) > 1:
            self._send_error_email(request, qs)
            activate_contest(request, None)
            auth.logout(request)
            return TemplateResponse(
                request, 'contestexcl/exclusive-contests-error.html'
            )
        elif len(qs) == 1:
            contest = qs[0]
            if request.contest != contest:
                if is_ajax(request):
                    raise PermissionDenied
                else:
                    messages.info(
                        request,
                        _(
                            "You have been redirected to this contest,"
                            " because you are not currently allowed to access"
                            " other contests."
                        ),
                    )
                    return redirect(
                        reverse(
                            'default_contest_view', kwargs={'contest_id': contest.id}
                        )
                    )
            request.contest_exclusive = True
        else:
            request.contest_exclusive = False

    def _check_requirements(self, request):
        if not hasattr(request, 'timestamp'):
            raise ImproperlyConfigured(
                "oioioi.base.middleware.TimestampingMiddleware is required."
                " If you have it installed check if it comes before"
                "ExclusiveContestsMiddleware in your MIDDLEWARE"
                "setting"
            )

        if not hasattr(request, 'contest'):
            raise ImproperlyConfigured(
                "oioioi.contests.middleware.CurrentContestMiddleware is"
                " required. If you have it installed check if it comes before "
                "ExclusiveContestsMiddleware in your MIDDLEWARE"
                "setting"
            )

        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "django.contrib.auth.middleware.AuthenticationMiddleware is"
                "required. If you have it installed check if it comes before "
                "ExclusiveContestsMiddleware in your MIDDLEWARE"
                "setting"
            )

        return request.contest

    def _send_error_email(self, request, contests):
        context = self._error_email_context(request, contests)
        message = self._error_email_message(context)
        subject = render_to_string('contestexcl/exclusive-contests-error-subject.txt')
        subject = ' '.join(subject.strip().splitlines())
        mail_admins(subject, message)

    def _error_email_message(self, context):
        return render_to_string(
            'contestexcl/exclusive-contests-error-email.txt', context
        )

    def _error_email_context(self, request, contests):
        contests_data = [(cnst.name, cnst.id) for cnst in contests]
        return {'contests': contests_data, 'username': request.user.username}


# This causes adding all mixins to ExclusiveContestMiddleware.
# This is needed as middlewares are instantiated before importing
# INSTALLED_APPS, so mixins would be late.
load_modules('middleware')
