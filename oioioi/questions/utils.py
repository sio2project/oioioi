from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.utils import visible_problem_instances, visible_rounds


# taken from django.contrib.admin.options.ModelAdmin
def log_addition(request, object):
    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(object).pk,
        object_id=object.pk,
        object_repr=force_text(object),
        action_flag=ADDITION,
    )


def get_categories(request):
    categories = [
        ('p_%d' % (pi.id,), _("Problem %s") % (pi.problem.name,))
        for pi in visible_problem_instances(request)
    ]
    categories += [
        ('r_%d' % (round.id,), _("General, %s") % (round.name,))
        for round in visible_rounds(request)
    ]
    return categories


def get_category(message):
    if message.problem_instance:
        return 'p_%d' % message.problem_instance.id
    if message.round:
        return 'r_%d' % message.round.id
    return None


def unanswered_questions(messages):
    return messages.filter(
        message__isnull=True, top_reference__isnull=True, kind='QUESTION'
    )
