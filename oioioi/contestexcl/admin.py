from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.contestexcl.forms import ExclusivenessConfigForm
from oioioi.contestexcl.models import ExclusivenessConfig
from oioioi.contests.admin import ContestAdmin


class ExclusivenessConfigInline(admin.TabularInline):
    model = ExclusivenessConfig
    extra = 0
    form = ExclusivenessConfigForm
    fields = ('enabled', 'start_date', 'end_date', 'disable')
    category = _("Advanced")

    def get_fields(self, request, obj=None):
        fields = super(ExclusivenessConfigInline, self).get_fields(request, obj)
        # Superadmins don't need to see the disable field
        if obj and request.user.is_superuser:
            return [f for f in fields if f != 'disable']
        return fields

    def get_readonly_fields(self, request, obj=None):
        # Contest admins should only be able to change the disable field
        if obj and not request.user.is_superuser:
            return [f for f in self.get_fields(request, obj) if f != 'disable']
        return []

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        # Most fields are protected by get_readonly_fields
        return (
            request.user.is_superuser
            or not obj  # This is confusing but for some reason is correct
            or obj.exclusivenessconfig_set.filter(enabled=True).exists()
        )

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class ContestAdminWithExclusivenessInlineMixin(object):
    """Adds :class:`~oioioi.contestexcl.models.ExclusivenessConfig` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(ContestAdminWithExclusivenessInlineMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (ExclusivenessConfigInline,)

    def _warn_on_contestexcl_overlap(self, request, ex_confs):
        for obj in ex_confs:
            qs = ExclusivenessConfig.objects.get_active_between(
                obj.start_date, obj.end_date
            ).select_related('contest')
            qs = [ex_conf for ex_conf in qs if ex_conf.contest != request.contest]
            if qs:
                contest_names = ', '.join([ex_conf.contest.name for ex_conf in qs])
                msg = (
                    _(
                        "The following contests' exclusion times"
                        " overlap with the current one: %s. Watch out, because"
                        " it may cause conflicts!"
                    )
                    % contest_names
                )
                messages.warning(request, msg)

    def _warn_on_not_exclusive_rounds(self, request, ex_confs):
        ex_confs.sort(key=lambda ex_conf: ex_conf.start_date)

        # For each round check separately that it is entirely exclusive
        for round in request.contest.round_set.all():
            round_not_excl_dates = []
            round_excl_end_date = round.start_date
            for ex_conf in ex_confs:
                # Check if there's a gap before the next excl config
                if ex_conf.start_date > round_excl_end_date:
                    round_not_excl_dates.append(
                        (round_excl_end_date, ex_conf.start_date)
                    )
                    round_excl_end_date = ex_conf.start_date

                # Update how much of the round is covered by the next config
                if ex_conf.end_date:
                    round_excl_end_date = max(round_excl_end_date, ex_conf.end_date)
                else:
                    break

                # Check if the round was covered entirely
                if round.end_date and round_excl_end_date >= round.end_date:
                    break
            else:
                round_not_excl_dates.append((round_excl_end_date, round.end_date))

            if round_not_excl_dates:
                # Default to first date if there are no future dates
                first_future_date = round_not_excl_dates[0]
                for date in round_not_excl_dates:
                    if not date[1] or date[1] >= timezone.now():
                        first_future_date = date
                        break

                if not first_future_date[1]:
                    msg = _(
                        "Exclusiveness configs usually cover entire rounds,"
                        " but currently round \"%s\" is not exclusive from"
                        " %s! Please verify that your exclusiveness"
                        " configs are correct."
                    ) % (round.name, first_future_date[0])
                else:
                    msg = _(
                        "Exclusiveness configs usually cover entire rounds,"
                        " but currently round \"%s\" is not exclusive from"
                        " %s to %s! Please verify that your exclusiveness"
                        " configs are correct."
                    ) % (round.name, first_future_date[0], first_future_date[1])
                messages.warning(request, msg)

    def save_formset(self, request, form, formset, change):
        instances = formset.save()

        ex_confs = []
        for obj in instances:
            if isinstance(obj, ExclusivenessConfig) and obj.enabled:
                ex_confs.append(obj)

        if ex_confs:
            self._warn_on_contestexcl_overlap(request, ex_confs)
            self._warn_on_not_exclusive_rounds(request, ex_confs)


ContestAdmin.mix_in(ContestAdminWithExclusivenessInlineMixin)
