from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_unicode

# taken from django.contrib.admin.options.ModelAdmin
def log_addition(request, object):
    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(object).pk,
        object_id=object.pk,
        object_repr=force_unicode(object),
        action_flag=ADDITION
    )
