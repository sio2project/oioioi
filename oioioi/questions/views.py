import datetime
import calendar

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.utils.text import Truncator

from oioioi.base.menu import menu_registry
from oioioi.base.utils import jsonify
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.utils.user_selection import get_user_hints_view
from oioioi.contests.utils import can_enter_contest, is_contest_admin, \
    visible_rounds, contest_exists
from oioioi.questions.utils import get_categories, log_addition, \
    unanswered_questions
from oioioi.questions.forms import AddContestMessageForm, AddReplyForm, \
    FilterMessageForm, FilterMessageAdminForm
from oioioi.questions.models import Message, MessageView, ReplyTemplate, \
    new_question_signal


def visible_messages(request, author=None, category=None):
    rounds_ids = [round.id for round in visible_rounds(request)]
    q_expression = Q(round_id__in=rounds_ids)
    if author:
        q_expression = q_expression & Q(author=author)
    if category:
        # pylint: disable=unpacking-non-sequence
        category_type, category_id = category
        if category_type == 'p':
            q_expression = q_expression & Q(problem_instance__id=category_id)
        elif category_type == 'r':
            q_expression = q_expression & Q(round__id=category_id,
                                            problem_instance=None)
    messages = Message.objects.filter(q_expression).order_by('-date')
    if not is_contest_admin(request):
        q_expression = Q(kind='PUBLIC')
        if request.user.is_authenticated():
            q_expression = q_expression \
                    | (Q(author=request.user) & Q(kind='QUESTION')) \
                    | Q(top_reference__author=request.user)
        messages = messages.filter(q_expression, date__lte=request.timestamp)
    return messages.select_related('top_reference', 'author',
            'problem_instance', 'problem_instance__problem')


def new_messages(request, messages=None):
    if not request.user.is_authenticated():
        return messages.none()
    if messages is None:
        messages = visible_messages(request)
    return messages.exclude(messageview__user=request.user) \
            .exclude(author=request.user)


def request_time_seconds(request):
    return calendar.timegm(request.timestamp.timetuple())


def messages_template_context(request, messages):
    replied_ids = frozenset(m.top_reference_id for m in messages)
    new_ids = new_messages(request, messages).values_list('id', flat=True)

    if is_contest_admin(request):
        unanswered = unanswered_questions(messages)
    else:
        unanswered = []

    to_display = [{
            'message': m,
            'link_message': m.top_reference
                    if m.top_reference in messages else m,
            'needs_reply': m in unanswered,
            'read': m.id not in new_ids,
        } for m in messages if m.id not in replied_ids]

    def key(entry):
        return entry['needs_reply'], entry['message'].date
    to_display.sort(key=key, reverse=True)
    return to_display


@menu_registry.register_decorator(_("Questions and news"), lambda request:
        reverse('contest_messages', kwargs={'contest_id': request.contest.id}),
    order=450)
@enforce_condition(contest_exists & can_enter_contest)
def messages_view(request):
    if is_contest_admin(request):
        form = FilterMessageAdminForm(request, request.GET)
    else:
        form = FilterMessageForm(request, request.GET)

    if form.is_valid():
        category = form.cleaned_data['category']
        author = form.cleaned_data.get('author')
        messages = messages_template_context(
            request, visible_messages(request, author, category))
    else:
        messages = messages_template_context(
            request, visible_messages(request))

    return TemplateResponse(request, 'questions/list.html',
        {'records': messages, 'form': form,
         'questions_on_page': getattr(settings, 'QUESTIONS_ON_PAGE', 30),
         'categories': get_categories(request)})


@enforce_condition(contest_exists & can_enter_contest)
def message_view(request, message_id):
    message = get_object_or_404(Message, id=message_id,
            contest_id=request.contest.id)
    vmessages = visible_messages(request)
    if not vmessages.filter(id=message_id):
        raise PermissionDenied
    if message.top_reference_id is None:
        replies = list(vmessages.filter(top_reference=message)
                       .order_by('date'))
    else:
        replies = []
    if is_contest_admin(request) and message.kind == 'QUESTION' and \
            message.can_have_replies:
        if request.method == 'POST':
            form = AddReplyForm(request, request.POST)
            if request.POST.get('just_reload') != 'yes' and form.is_valid():
                instance = form.save(commit=False)
                instance.top_reference = message
                instance.author = request.user
                instance.date = request.timestamp
                instance.save()
                log_addition(request, instance)
                return redirect('contest_messages',
                        contest_id=request.contest.id)
            elif request.POST.get('just_reload') == 'yes':
                form.is_bound = False
        else:
            form = AddReplyForm(request, initial={
                    'topic': _("Re: ") + message.topic,
                })
    else:
        form = None
    if request.user.is_authenticated():
        for m in [message] + replies:
            try:
                MessageView.objects.get_or_create(message=m, user=request.user)
            except IntegrityError:
                # get_or_create does not guarantee race-free execution, so we
                # silently ignore the IntegrityError from the unique index
                pass
    return TemplateResponse(request, 'questions/message.html',
            {'message': message, 'replies': replies, 'form': form,
                 'reply_to_id': message.top_reference_id or message.id,
                 'timestamp': request_time_seconds(request)})


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def add_contest_message_view(request):
    is_admin = is_contest_admin(request)
    if request.method == 'POST':
        form = AddContestMessageForm(request, request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.author = request.user
            if is_admin:
                instance.kind = 'PUBLIC'
            else:
                instance.kind = 'QUESTION'
            instance.date = request.timestamp
            instance.save()
            if instance.kind == 'QUESTION':
                new_question_signal.send(sender=Message, request=request,
                                         instance=instance)
            log_addition(request, instance)
            return redirect('contest_messages', contest_id=request.contest.id)

    else:
        initial = {}
        for field in ('category', 'topic', 'content'):
            if field in request.GET:
                initial[field] = request.GET[field]
        form = AddContestMessageForm(request, initial=initial)

    if is_admin:
        title = _("Add news")
    else:
        title = _("Ask question")

    return TemplateResponse(request, 'questions/add.html',
            {'form': form, 'title': title, 'is_news': is_admin})


@enforce_condition(contest_exists & is_contest_admin)
def get_messages_authors_view(request):
    queryset = visible_messages(request)
    return get_user_hints_view(request, 'substr', queryset, 'author')


@jsonify
@enforce_condition(contest_exists & is_contest_admin)
def get_reply_templates_view(request):
    templates = ReplyTemplate.objects \
            .filter(Q(contest=request.contest.id) | Q(contest__isnull=True)) \
            .order_by('-usage_count')
    return [{'id': t.id, 'name': t.visible_name, 'content': t.content}
            for t in templates]


@enforce_condition(contest_exists & is_contest_admin)
def increment_template_usage_view(request, template_id=None):
    try:
        template = ReplyTemplate.objects.filter(id=template_id) \
                                        .filter(Q(contest=request.contest.id) |
                                                Q(contest__isnull=True)).get()
    except ReplyTemplate.DoesNotExist:
        raise Http404

    template.usage_count += 1
    template.save()
    return HttpResponse('OK', content_type='text/plain')


@jsonify
@enforce_condition(contest_exists)
def check_new_messages_view(request, topic_id):
    timestamp = request.GET['timestamp']
    unix_date = datetime.datetime.fromtimestamp(int(timestamp))
    output = [[x.topic,
              Truncator(x.content)
              .chars(settings.MEANTIME_ALERT_MESSAGE_SHORTCUT_LENGTH),
              x.id]
              for x in visible_messages(request)
              .filter(top_reference_id=topic_id)
              .filter(date__gte=unix_date)]
    return {'timestamp': request_time_seconds(request), 'messages': output}
