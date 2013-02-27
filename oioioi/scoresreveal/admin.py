from django.utils.translation import ugettext_lazy as _
from oioioi.base import admin
from oioioi.contests.admin import SubmissionAdmin
from oioioi.scoresreveal.utils import is_revealed
from oioioi.scoresreveal.models import ScoreRevealConfig


class ScoresRevealConfigInline(admin.TabularInline):
    model = ScoreRevealConfig
    can_delete = True
    extra = 0

class ScoresRevealProgrammingProblemAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(ScoresRevealProgrammingProblemAdminMixin, self) \
            .__init__(*args, **kwargs)
        self.inlines = self.inlines + [ScoresRevealConfigInline]

class ScoresRevealSubmissionAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(ScoresRevealSubmissionAdminMixin, self).__init__(*args, **kwargs)
        self.list_display = self.list_display + ['reveal_display']

    def reveal_display(self, instance):
        return is_revealed(instance)
    reveal_display.short_description = _("Revealed")
    reveal_display.admin_order_field = 'revealed'
    reveal_display.boolean = True

SubmissionAdmin.mix_in(ScoresRevealSubmissionAdminMixin)