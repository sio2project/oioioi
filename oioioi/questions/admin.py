from django.core.urlresolvers import reverse
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.utils.text import get_text_list
from django.utils.translation import ugettext_lazy as _
from oioioi.base import admin
from oioioi.base.utils import ObjectWithMixins
from oioioi.questions.forms import ChangeContestMessageForm
from oioioi.questions.models import Message

class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'topic', 'author']
    fields = ['date', 'author', 'contest', 'round', 'problem_instance',
        'kind', 'topic', 'content']
    readonly_fields = ['date', 'author', 'contest', 'round',
        'problem_instance']

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

    def change_view(self, request, object_id, form_url='', extra_context=None):
        message = get_object_or_404(Message, id=object_id)

        if request.method == 'POST':
            form = ChangeContestMessageForm(message.kind, request,
                                            request.POST, instance=message)
            if form.is_valid():
                if form.changed_data:
                    change_message = _("Changed %s.") % \
                        get_text_list(form.changed_data, _("and"))
                else:
                    change_message = _("No fields changed.")
                form.save()
                super(MessageAdmin, self).log_change(request, message,
                                                     change_message)
                return redirect('contest_messages',
                                contest_id=request.contest.id)
        else:
            form = ChangeContestMessageForm(message.kind, request,
                                            instance=message)
        return TemplateResponse(request, 'admin/questions/change_message.html',
                                {'form': form, 'message': message})

admin.site.register(Message, MessageAdmin)
