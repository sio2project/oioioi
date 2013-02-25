from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from oioioi.base import admin
from oioioi.base.utils import ObjectWithMixins
from oioioi.questions.models import Message

class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'topic', 'author']
    fields = ['date', 'author', 'contest', 'round', 'problem_instance',
        'kind', 'topic', 'content']
    readonly_fields = ['date', 'author', 'contest', 'round',
        'problem_instance', 'kind']

    def has_add_permission(self, request):
        return request.user.has_perm('contests.contest_admin', request.contest)

    def has_change_permission(self, request, obj=None):
        if obj and not obj.contest:
            return False
        return self.has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def queryset(self, request):
        queryset = super(MessageAdmin, self).queryset(request)
        queryset = queryset.filter(contest=request.contest)
        return queryset

    def add_view(self, request, form_url='', extra_context=None):
        return redirect('add_contest_message', contest_id=request.contest.id)

    def get_list_select_related(self):
        return super(MessageAdmin, self).get_list_select_related() \
                + ['author', 'problem_instance', 'contest']

admin.site.register(Message, MessageAdmin)
