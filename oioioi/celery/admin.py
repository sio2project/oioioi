from djcelery.admin import TaskMonitor, WorkerMonitor
from djcelery.models import TaskState, WorkerState

from oioioi.base import admin

admin.site.register(TaskState, TaskMonitor)
admin.site.register(WorkerState, WorkerMonitor)
