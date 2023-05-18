from django import forms
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.user_selection import UserSelectionField
from oioioi.contests.controllers import ContestController
from oioioi.contests.models import Submission
from oioioi.contests.utils import is_contest_admin, visible_problem_instances
from oioioi.teams.models import TeamMembership, TeamsConfig


class TeamsMixinForContestController(object):
    """Mixin for contests containing teams. Gives information about
    permissions to modifications of teams.
    """

    @property
    def teams_admin(self):
        from oioioi.teams.admin import TeamsAdmin

        return TeamsAdmin

    def can_modify_team(self, request):
        try:
            tm = TeamMembership.objects.get(
                user=request.user, team__contest=request.contest
            )
            did_submit = Submission.objects.filter(user=tm.team.user).exists()
        except TeamMembership.DoesNotExist:
            did_submit = Submission.objects.filter(
                user=request.user, problem_instance__contest=request.contest
            ).exists()
        try:
            tconfig = request.contest.teamsconfig
            if not tconfig.enabled or did_submit:
                return False
            after_start = (
                tconfig.modify_begin_date is None
            ) or request.timestamp >= tconfig.modify_begin_date
            before_end = (
                tconfig.modify_end_date is None
            ) or request.timestamp <= tconfig.modify_end_date
            return after_start and before_end
        except TeamsConfig.DoesNotExist:
            return False

    def max_size_of_team(self):
        return self.contest.teamsconfig.max_team_size

    def filter_my_visible_submissions(self, request, queryset, filter_user=True):
        if not request.user.is_authenticated:
            return queryset.none()
        if not filter_user:
            raise NotImplementedError

        try:
            tm = TeamMembership.objects.get(
                user=request.user, team__contest=request.contest
            )
            qs = queryset.filter(
                user=tm.team.user,
                problem_instance__in=visible_problem_instances(request),
            )
            filter_user = False
        except TeamMembership.DoesNotExist:
            qs = queryset

        return super(
            TeamsMixinForContestController, self
        ).filter_my_visible_submissions(request, qs, filter_user)

    def adjust_submission_form(self, request, form, problem_instance):
        super(TeamsMixinForContestController, self).adjust_submission_form(
            request, form, problem_instance
        )
        try:
            tm = TeamMembership.objects.get(
                user_id=request.user.id, team__contest=request.contest
            )
            if not is_contest_admin(request):
                form.fields['user'] = UserSelectionField(
                    initial=tm.team.user,
                    label=_("Team name"),
                    widget=forms.TextInput(attrs={'readonly': 'readonly'}),
                    help_text=_(
                        "You are in the team, so submission will"
                        " be sent as the team."
                    ),
                )

                def clean_user():
                    user = form.cleaned_data['user']
                    try:
                        tm = TeamMembership.objects.get(
                            user=request.user, team__contest=request.contest
                        )
                        if user != tm.team.user:
                            raise forms.ValidationError(
                                _("You can't submit a solution for another team!")
                            )
                        return user
                    except TeamMembership.DoesNotExist:
                        raise forms.ValidationError(_("Team does not exist"))

                form.clean_user = clean_user
            else:
                form.fields['team'] = forms.CharField(
                    initial=tm.team.name,
                    label=_("Team name"),
                    widget=forms.TextInput(attrs={'readonly': 'readonly'}),
                    help_text=_(
                        "You are in the team, but you are also the "
                        "admin, so you can send solution as the "
                        "team user or as yourself."
                    ),
                )
        except TeamMembership.DoesNotExist:
            pass

    def create_submission(self, request, problem_instance, form_data, **kwargs):
        submission = super(TeamsMixinForContestController, self).create_submission(
            request, problem_instance, form_data, **kwargs
        )
        if not is_contest_admin:
            try:
                tm = TeamMembership.objects.get(
                    user=request.user, team__contest=request.contest
                )
                submission.user = tm.team.user
                submission.save()
            except TeamMembership.DoesNotExist:
                pass
        return submission


ContestController.mix_in(TeamsMixinForContestController)
