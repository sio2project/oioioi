from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.text import get_text_list
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.base.permissions import is_superuser
from oioioi.contests.admin import ContestAdmin, contest_site
from oioioi.contests.models import Contest, ContestPermission
from oioioi.contests.utils import is_contest_basicadmin
from oioioi.questions.forms import ChangeContestMessageForm
from oioioi.questions.models import Message, MessageNotifierConfig, ReplyTemplate


class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'topic', 'author']
    fields = [
        'date',
        'author',
        'contest',
        'round',
        'problem_instance',
        'kind',
        'topic',
        'content',
    ]
    readonly_fields = ['date', 'author', 'contest', 'round', 'problem_instance']

    def has_add_permission(self, request):
        return is_contest_basicadmin(request)

    def has_change_permission(self, request, obj=None):
        if obj and not obj.contest:
            return False
        return self.has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_queryset(self, request):
        queryset = super(MessageAdmin, self).get_queryset(request)
        queryset = queryset.filter(contest=request.contest)
        return queryset

    def add_view(self, request, form_url='', extra_context=None):
        return redirect('add_contest_message', contest_id=request.contest.id)

    def get_custom_list_select_related(self):
        return super(MessageAdmin, self).get_custom_list_select_related() + [
            'author',
            'problem_instance',
            'contest',
        ]

    def change_view(self, request, object_id, form_url='', extra_context=None):
        message = get_object_or_404(Message, id=object_id)

        if not self.has_change_permission(request, message):
            raise PermissionDenied

        if request.method == 'POST':
            form = ChangeContestMessageForm(
                message.kind, request, request.POST, instance=message
            )
            if form.is_valid():
                if form.changed_data:
                    change_message = _("Changed %s.") % get_text_list(
                        form.changed_data, _("and")
                    )
                else:
                    change_message = _("No fields changed.")

                if (
                    'kind' in form.changed_data
                    and form.cleaned_data['kind'] == 'PUBLIC'
                ):
                    msg = form.save(commit=False)
                    msg.mail_sent = False
                    msg.save()
                else:
                    form.save()

                super(MessageAdmin, self).log_change(request, message, change_message)
                return redirect('contest_messages', contest_id=request.contest.id)
        else:
            form = ChangeContestMessageForm(message.kind, request, instance=message)
        return TemplateResponse(
            request,
            'admin/questions/change_message.html',
            {'form': form, 'message': message},
        )

    def response_delete(self, request):
        super(MessageAdmin, self).response_delete(request)
        return redirect('contest_messages', contest_id=request.contest.id)


contest_site.contest_register(Message, MessageAdmin)


class MessageNotifierConfigInline(admin.TabularInline):
    model = MessageNotifierConfig
    extra = 0
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return is_contest_basicadmin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_basicadmin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_basicadmin(request)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        contest_admin_perm = (
            ContestPermission.objects.filter(contest=request.contest)
            .filter(permission='contests.contest_admin')
            .select_related('user')
        )
        admin_ids = [p.user_id for p in contest_admin_perm]

        if request.user.is_superuser:
            admin_ids += [u.id for u in User.objects.filter(is_superuser=True)]
        elif is_contest_basicadmin(request):
            added = MessageNotifierConfig.objects.filter(contest=request.contest)
            admin_ids += [request.user.id] + [conf.user_id for conf in added]
        else:
            admin_ids = []

        if db_field.name == 'user':
            kwargs['queryset'] = User.objects.filter(id__in=admin_ids).order_by(
                'username'
            )

        return super(MessageNotifierConfigInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class MessageNotifierContestAdminMixin(object):
    """Adds :class:`~oioioi.questions.models.MessageNotifierConfig` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(MessageNotifierContestAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = self.inlines + [MessageNotifierConfigInline]


ContestAdmin.mix_in(MessageNotifierContestAdminMixin)


class ReplyTemplateAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        if is_superuser(request):
            return ['visible_name', 'content', 'contest', 'usage_count']
        return ['visible_name', 'content', 'usage_count']

    def get_list_filter(self, request):
        if is_superuser(request):
            return ['contest']
        return []

    def get_readonly_fields(self, request, obj=None):
        fields = []
        if obj is None:
            fields.append('usage_count')
        return fields

    def get_form(self, request, obj=None, **kwargs):
        if not self.has_change_permission(request, obj):
            return super(ReplyTemplateAdmin, self).get_form(request, obj, **kwargs)

        form = super(ReplyTemplateAdmin, self).get_form(request, obj, **kwargs)
        if 'contest' in form.base_fields:
            if not is_superuser(request):
                qs = Contest.objects.filter(pk=request.contest.pk)
                form.base_fields['contest']._set_queryset(qs)
                form.base_fields['contest'].required = True
                form.base_fields['contest'].empty_label = None
            form.base_fields['contest'].initial = request.contest
        return form

    def has_add_permission(self, request):
        # Correct object contest ensured by form.
        return is_contest_basicadmin(request)

    def has_change_permission(self, request, obj=None):
        if obj:
            return is_superuser(request) or (
                is_contest_basicadmin(request) and obj.contest == request.contest
            )
        return self.has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_queryset(self, request):
        queryset = super(ReplyTemplateAdmin, self).get_queryset(request)
        if not is_superuser(request):
            queryset = queryset.filter(contest=request.contest)
        return queryset


contest_site.contest_register(ReplyTemplate, ReplyTemplateAdmin)
