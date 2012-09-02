from oioioi.base import admin
from djcelery.models import TaskState, WorkerState
from djcelery.admin import TaskMonitor, WorkerMonitor

admin.site.register(TaskState, TaskMonitor)
admin.site.register(WorkerState, WorkerMonitor)
