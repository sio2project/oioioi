from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from oioioi.base import admin
from oioioi.base.admin import system_admin_menu_registry
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.admin import UserListFilter
from oioioi.submitsqueue.models import QueuedSubmit


class SystemSubmitsQueueAdmin(admin.ModelAdmin):
    list_display = ['state', 'contest', 'problem_instance',
                    'user', 'creation_date', 'celery_task_id']
    list_filter = ['state']

    def has_add_permission(self, request):
        return False


admin.site.register(QueuedSubmit, SystemSubmitsQueueAdmin)
system_admin_menu_registry.register('queuedsubmit_admin',
        _("Submits Queue"), lambda request:
        reverse('oioioiadmin:submitsqueue_queuedsubmit_changelist'),
        order=60)


class ContestQueuedSubmit(QueuedSubmit):
    class Meta(object):
        proxy = True
        verbose_name = _("Contest Queued Submit")


class ContestSubmitsQueueAdmin(SystemSubmitsQueueAdmin):
    def __init__(self, *args, **kwargs):
        super(ContestSubmitsQueueAdmin, self).__init__(*args, **kwargs)
        self.list_display = [x for x in self.list_display if x != 'contest']
        self.list_filter = self.list_filter + [UserListFilter]


admin.site.register(ContestQueuedSubmit, ContestSubmitsQueueAdmin)
contest_admin_menu_registry.register('queuedsubmit_admin',
        _("Submits Queue"), lambda request:
        reverse('oioioiadmin:submitsqueue_contestqueuedsubmit_changelist'),
        order=60)
