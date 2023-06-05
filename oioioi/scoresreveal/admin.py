from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.base.admin import NO_CATEGORY
from oioioi.base.forms import AlwaysChangedModelForm
from oioioi.contests.admin import ProblemInstanceAdmin, SubmissionAdmin
from oioioi.contests.utils import is_contest_admin
from oioioi.scoresreveal.models import ScoreRevealConfig
from oioioi.scoresreveal.utils import is_revealed


class RevealedFilter(SimpleListFilter):
    title = _("revealed")
    parameter_name = 'revealed'

    def lookups(self, request, model_admin):
        return ((1, _("Yes")), (0, _("No")))

    def queryset(self, request, queryset):
        if self.value():
            isnull = self.value() == '0'
            return queryset.filter(revealed__isnull=isnull)
        else:
            return queryset


class ScoresRevealConfigInline(admin.TabularInline):
    model = ScoreRevealConfig
    can_delete = True
    extra = 0
    form = AlwaysChangedModelForm


class ScoresRevealProblemInstanceAdminMixin(object):
    """Adds `ScoreRevealConfigForInstance` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(ScoresRevealProblemInstanceAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (ScoresRevealConfigInline,)


ProblemInstanceAdmin.mix_in(ScoresRevealProblemInstanceAdminMixin)


class ScoresRevealSubmissionAdminMixin(object):
    """Adds reveal info and filter to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(ScoresRevealSubmissionAdminMixin, self).__init__(*args, **kwargs)

    def get_list_display(self, request):
        return super(ScoresRevealSubmissionAdminMixin, self).get_list_display(
            request
        ) + ['reveal_display']

    def get_list_filter(self, request):
        return super(ScoresRevealSubmissionAdminMixin, self).get_list_filter(
            request
        ) + [RevealedFilter]

    def reveal_display(self, instance):
        return is_revealed(instance)

    reveal_display.short_description = _("Revealed")
    reveal_display.admin_order_field = 'revealed'
    reveal_display.boolean = True

    def get_custom_list_select_related(self):
        return super(
            ScoresRevealSubmissionAdminMixin, self
        ).get_custom_list_select_related() + ['revealed']


SubmissionAdmin.mix_in(ScoresRevealSubmissionAdminMixin)
