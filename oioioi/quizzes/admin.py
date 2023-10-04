from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from nested_admin import nested
from nested_admin.formsets import NestedInlineFormSet

import oioioi.contests.admin
from oioioi.base.admin import NO_CATEGORY
from oioioi.contests.current_contest import reverse
from oioioi.quizzes.models import (
    Quiz,
    QuizAnswer,
    QuizAnswerPicture,
    QuizQuestion,
    QuizQuestionPicture,
)

# If there was a need to get rid of nested_admin, you can create dummy inlines,
# that add links to ModelAdmin with nested inlines on another page,
# see how QuizInline works.


class QuizAnswerFormset(NestedInlineFormSet):
    def clean(self):
        super(QuizAnswerFormset, self).clean()
        is_empty = True
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                is_empty = False
        if is_empty:
            raise ValidationError(_("A question needs at least one answer."))


class QuizPictureInline(nested.NestedStackedInline):
    extra = 0

    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


class QuizQuestionPictureInline(QuizPictureInline):
    model = QuizQuestionPicture


class QuizAnswerPictureInline(QuizPictureInline):
    model = QuizAnswerPicture


class QuizAnswerInline(nested.NestedTabularInline):
    model = QuizAnswer
    formset = QuizAnswerFormset
    sortable_field_name = 'order'
    extra = 0
    inlines = (QuizAnswerPictureInline,)

    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class QuizQuestionInline(nested.NestedStackedInline):
    model = QuizQuestion
    sortable_field_name = 'order'
    extra = 0
    inlines = (QuizAnswerInline, QuizQuestionPictureInline,)

    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


class QuizModelAdmin(nested.NestedModelAdmin):
    model = Quiz
    inlines = (QuizQuestionInline,)

    class Media(object):
        css = {'all': ('quizzes/quizadmin.css',)}

    def __init__(self, parent_model, admin_site):
        super(QuizModelAdmin, self).__init__(parent_model, admin_site)
        self.exclude = [f.name for f in Quiz._meta.get_fields()]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return request.user.is_superuser
        # because Quiz questions are bound to the Quiz and not QuizInstance,
        # only the owner (author) can edit them
        # otherwise someone could add the Quiz to contest to get edit
        # perimssion and their changes would propagate to all other instances
        return obj.author == request.user or request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


# This is required to be able to generate a link to editing quiz questions
oioioi.contests.admin.contest_site.register(Quiz, QuizModelAdmin)


class QuizInline(admin.StackedInline):
    model = Quiz
    fields = []  # < this doesn't exclude the fields
    readonly_fields = ['edit']
    category = NO_CATEGORY

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def edit(self, instance):
        url = reverse('oioioiadmin:quizzes_quiz_change', args=[instance.pk])
        return mark_safe(
            u'<a href="{url}">{text}</a>'.format(url=url, text=_("Edit quiz questions"))
        )

    def __init__(self, parent_model, admin_site):
        super(QuizInline, self).__init__(parent_model, admin_site)
        self.exclude = [f.name for f in Quiz._meta.get_fields()]


class QuizAdminMixin(object):
    """Adds :class:`~oioioi.quizzes.models.Quiz` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(QuizAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (QuizInline,)
