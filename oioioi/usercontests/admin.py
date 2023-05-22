from functools import partial

from django import forms
from django.conf import settings
from django.forms.models import modelform_factory
from django.shortcuts import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.menu import personal_menu_registry
from oioioi.base.permissions import make_request_condition
from oioioi.contests.admin import ContestAdmin, RoundInline
from oioioi.usercontests.forms import UserContestForm
from oioioi.usercontests.models import UserContest


@make_request_condition
def use_usercontest_admin_form(request):
    """Since the special usercontest version of Django admin has limited
    functionality, we only want to use it for 'regular' users - that is
    users who otherwise couldn't create their own contests.
    In essence, if the user can already create contests in some other way
    (or usercontests are disabled) this function should return False.
    """
    if settings.ARCHIVE_USERCONTESTS:
        return False

    user = request.user
    return not (user.is_superuser or user.has_perm('teachers.teacher'))


if 'oioioi.simpleui' not in settings.INSTALLED_APPS:
    personal_menu_registry.register(
        'create_contest',
        _("New contest"),
        lambda request: reverse('oioioiadmin:contests_contest_add'),
        use_usercontest_admin_form,
        order=10,
    )
else:
    personal_menu_registry.register(
        'user_dashboard',
        _("Contests"),
        lambda request: reverse('simpleui_user_dashboard'),
        use_usercontest_admin_form,
        order=5,
    )


class UserRoundInlineFormset(RoundInline.formset):
    def clean(self):
        super(UserRoundInlineFormset, self).clean()

        if not hasattr(settings, 'USER_CONTEST_TIMEOUT'):
            return
        for form in self.forms:
            if 'end_date' not in form.cleaned_data.keys():
                continue
            if form.cleaned_data['end_date'] is None:
                raise forms.ValidationError(
                    _("Please provide round end date."), code='invalid'
                )
            if form.cleaned_data['end_date'] > settings.USER_CONTEST_TIMEOUT:
                raise forms.ValidationError(
                    _(
                        "Round \'%(round_name)s\' \
                         has to end before %(end_contests)s."
                    ),
                    params={
                        "round_name": form.cleaned_data['name'],
                        "end_contests": settings.USER_CONTEST_TIMEOUT.strftime(
                            '%Y-%m-%d %H:%M:%S %Z'
                        ),
                    },
                    code='invalid',
                )


class UserRoundInline(RoundInline):
    formset = UserRoundInlineFormset


class UserContestAdminMixin(object):
    def is_owner(self, user, contest):
        return UserContest.objects.filter(user=user, contest=contest).exists()

    def has_add_permission(self, request):
        if not use_usercontest_admin_form(request):
            return super(UserContestAdminMixin, self).has_add_permission(request)

        return True

    def get_fieldsets(self, request, obj=None):
        if obj or not use_usercontest_admin_form(request):
            return super(UserContestAdminMixin, self).get_fieldsets(request, obj)

        fields = list(UserContestForm().base_fields.keys())
        return [(None, {'fields': fields})]

    def save_model(self, request, obj, form, change):
        if change or not use_usercontest_admin_form(request):
            return super(UserContestAdminMixin, self).save_model(
                request, obj, form, change
            )

        obj.controller_name = 'oioioi.usercontests.controllers.UserContestController'
        ret = super(UserContestAdminMixin, self).save_model(request, obj, form, change)
        UserContest.objects.create(contest=obj, user=request.user)
        return ret

    def get_form(self, request, obj=None, **kwargs):
        if obj or not use_usercontest_admin_form(request):
            return super(UserContestAdminMixin, self).get_form(request, obj, **kwargs)

        return modelform_factory(
            self.model,
            form=UserContestForm,
            formfield_callback=partial(self.formfield_for_dbfield, request=request),
        )

    def get_inline_instances(self, request, obj=None):
        if not use_usercontest_admin_form(request):
            return super(UserContestAdminMixin, self).get_inline_instances(request, obj)

        _inlines = super(UserContestAdminMixin, self).get_inline_instances(request, obj)
        custom_inline = UserRoundInline(self.model, self.admin_site)
        modified_inlines = []
        for inline in _inlines:
            if isinstance(inline, RoundInline):
                modified_inlines.append(custom_inline)
            else:
                modified_inlines.append(inline)

        return modified_inlines


ContestAdmin.mix_in(UserContestAdminMixin)
