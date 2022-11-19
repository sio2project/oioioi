from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base import admin
from oioioi.contests.admin import ContestAdmin
from oioioi.quiz.models import QuizQuestion, QuizAnswer, QuizInstance


class QuzAnswerAdminInline(admin.StackedInline):
    model = QuizAnswer
    extra = 0
    inline_classes = ('collapse open',)


class QuizAdmin(admin.ModelAdmin):
    inlines = (QuzAnswerAdminInline,)


admin.site.register(QuizQuestion, QuizAdmin)
admin.system_admin_menu_registry.register(
    'quiz',
    _("Quiz"),
    lambda request: reverse('oioioiadmin:quiz_quizquestion_changelist'),
    order=10
)


class QuizInstanceInline(admin.TabularInline):
    model = QuizInstance


class QuizInstanceAdminMixin(object):
    """Adds :class:`oioioi.quiz.models.QuizInstance` to an admin panel.
    """

    def __init__(self, *args, **kwargs):
        super(QuizInstanceAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = self.inlines + [QuizInstanceInline]


ContestAdmin.mix_in(QuizInstanceAdminMixin)
