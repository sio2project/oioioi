from django.contrib.auth.models import User
from django.template.loader import render_to_string

from oioioi.contestexcl.middleware import ExclusiveContestsMiddleware
from oioioi.participants.utils import is_contest_with_participants


class ExclusiveContestsWithParticipantsMiddlewareMixin(object):
    """This middleware mixin passes an additional selector to the
       :class:`~oioioi.contestexcl.middleware.ExclusiveContestsMiddleware`
       when the :mod:`~oioioi.participants` application is used.

       Now, a contest with
       :class:`~oioioi.contestexcl.models.ExclusivenessConfig`
       which has participants is exclusive only for its participants.

       Note that this feature makes greater sense when combined with automatic
       login, see :class:`oioioi.ipdnsauth.middleware.IpDnsAuthMiddleware`.
    """

    def process_view(self, request, view_func,
                     view_args, view_kwargs, selector=None):

        if not self._check_requirements(request):
            return

        def _participants_selector(user, contest):
            if is_contest_with_participants(contest):
                if user.is_anonymous:
                    return False
                rcontroller = contest.controller.registration_controller()
                qs = User.objects.filter(id=user.id)
                if qs.filter(participant__contest=contest,
                             participant__status='BANNED').exists():
                    return True
                return rcontroller.filter_participants(qs).exists()
            return True

        if selector is None:
            final_selector = _participants_selector
        else:
            final_selector = lambda user, contest: \
                _participants_selector(user, contest) \
                and selector(user, contest)

        return super(ExclusiveContestsWithParticipantsMiddlewareMixin, self) \
            .process_view(request, view_func, view_args, view_kwargs,
                          selector=final_selector)

    def _error_email_message(self, context):
        return render_to_string(
            'participants/exclusive-contests-error-email.txt',
            context
        )
ExclusiveContestsMiddleware \
    .mix_in(ExclusiveContestsWithParticipantsMiddlewareMixin)
