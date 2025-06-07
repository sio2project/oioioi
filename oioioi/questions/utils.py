from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.public_message import get_public_message
from oioioi.contests.utils import visible_problem_instances, visible_rounds
from oioioi.questions.models import NewsMessage, AddQuestionMessage


# taken from django.contrib.admin.options.ModelAdmin
def log_addition(request, object):
    LogEntry.objects.log_actions(
        user_id=request.user.pk,
        queryset=(object,),
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
        message__isnull=True,
        top_reference__isnull=True,
        marked_read_by__isnull=True,
        kind='QUESTION'
    )


def get_news_message(request):
    return get_public_message(
        request,
        NewsMessage,
        'questions_news_message'
    )


def get_add_question_message(request):
    return get_public_message(
        request,
        AddQuestionMessage,
        'add_question_message',
    )
