from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.base.forms import AlwaysChangedModelForm
from oioioi.contests.admin import ContestAdmin, ProblemInstanceAdmin, SubmissionAdmin
from oioioi.scoresreveal.models import ScoreRevealConfig
from oioioi.scoresreveal.utils import get_scores_reveal_config_universal, is_revealed


class RevealedFilter(SimpleListFilter):
    title = _("revealed")
    parameter_name = "revealed"

    def lookups(self, request, model_admin):
        return ((1, _("Yes")), (0, _("No")))

    def queryset(self, request, queryset):
        if self.value():
            isnull = self.value() == "0"
            return queryset.filter(revealed__isnull=isnull)
        else:
            return queryset


class ScoresRevealConfigInline(admin.TabularInline):
    model = ScoreRevealConfig
    can_delete = True
    extra = 0
    form = AlwaysChangedModelForm
    exclude = ("contest",)


class ScoresRevealProblemInstanceAdminMixin:
    """Adds `ScoreRevealConfigForInstance` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (ScoresRevealConfigInline,)

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        contest = getattr(obj, "contest", None)
        if not contest:
            return inline_instances
        if get_scores_reveal_config_universal(contest) is None:
            additional_description = _(" (no contest-wide default set)")
        else:
            additional_description = _(" (overriding contest-wide default)")

        for inline in inline_instances:
            if isinstance(inline, ScoresRevealConfigInline):
                inline.verbose_name += additional_description
                inline.verbose_name_plural += additional_description
        return inline_instances


ProblemInstanceAdmin.mix_in(ScoresRevealProblemInstanceAdminMixin)


class ScoresRevealContestConfigInline(admin.TabularInline):
    model = ScoreRevealConfig
    extra = 0
    form = AlwaysChangedModelForm
    category = _("Advanced")
    exclude = ("problem_instance",)


class ScoresRevealContestConfigAdminMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (ScoresRevealContestConfigInline,)


ContestAdmin.mix_in(ScoresRevealContestConfigAdminMixin)


class ScoresRevealSubmissionAdminMixin:
    """Adds reveal info and filter to an admin panel."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_list_display(self, request):
        return super().get_list_display(request) + ["reveal_display"]

    def get_list_filter(self, request):
        return super().get_list_filter(request) + [RevealedFilter]

    def reveal_display(self, instance):
        return is_revealed(instance)

    reveal_display.short_description = _("Revealed")
    reveal_display.admin_order_field = "revealed"
    reveal_display.boolean = True

    def get_custom_list_select_related(self):
        return super().get_custom_list_select_related() + ["revealed"]


SubmissionAdmin.mix_in(ScoresRevealSubmissionAdminMixin)
