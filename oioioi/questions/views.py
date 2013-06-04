import json
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.contests.utils import can_enter_contest, is_contest_admin, \
        visible_rounds, contest_exists
from oioioi.questions.utils import log_addition, unanswered_questions
from oioioi.questions.forms import AddContestMessageForm, AddReplyForm, \
        FilterMessageForm, FilterMessageAdminForm
from oioioi.questions.models import Message, MessageView, new_question_signal


def visible_messages(request, author=None, category=None):
    rounds_ids = [round.id for round in visible_rounds(request)]
    q_expression = Q(round_id__in=rounds_ids)
    if author:
        q_expression = q_expression & Q(author=author)
    if category:
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


@menu_registry.register_decorator(_("Messages"), lambda request:
        reverse('contest_messages', kwargs={'contest_id': request.contest.id}),
    order=450)
@enforce_condition(contest_exists & can_enter_contest)
def messages_view(request, contest_id):
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
         'num_hints': getattr(settings, 'NUM_HINTS', 10)})


@enforce_condition(contest_exists & can_enter_contest)
def message_view(request, contest_id, message_id):
    message = get_object_or_404(Message, id=message_id)
    vmessages = visible_messages(request)
    if not vmessages.filter(id=message_id):
        raise PermissionDenied
    if message.top_reference_id is None:
        replies = list(vmessages.filter(top_reference=message).all())
    else:
        replies = []
    if request.user.is_authenticated():
        for m in [message] + replies:
            try:
                MessageView.objects.get_or_create(message=m, user=request.user)
            except IntegrityError:
                # get_or_greate does not guarantee race-free execution, so we
                # silently ignore the IntegrityError from the unique index
                pass
    return TemplateResponse(request, 'questions/message.html',
                {'message': message, 'replies': replies,
                    'reply_to_id': message.top_reference_id or message.id})


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def add_contest_message_view(request, contest_id):
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
            return redirect('contest_messages', contest_id=contest_id)

    else:
        form = AddContestMessageForm(request)

    if is_admin:
        title = _("Add announcement")
    else:
        title = _("Ask question")

    return TemplateResponse(request, 'questions/add.html',
            {'form': form, 'title': title, 'is_announcement': is_admin})


def quote_for_reply(content):
    lines = content.strip().split('\n')
    return ''.join('> ' + l for l in lines)


@enforce_condition(contest_exists & is_contest_admin)
def add_reply_view(request, contest_id, message_id):
    question = get_object_or_404(Message, id=message_id,
            contest_id=contest_id, kind='QUESTION')
    if request.method == 'POST':
        form = AddReplyForm(request, request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.top_reference = question
            instance.author = request.user
            instance.date = request.timestamp
            instance.save()
            log_addition(request, instance)
            return redirect('contest_messages', contest_id=contest_id)
    else:
        form = AddReplyForm(request, initial={
                'topic': _("Re: ") + question.topic,
                'content': quote_for_reply(question.content),
            })

    return TemplateResponse(request, 'questions/add.html',
            {'form': form, 'title': _("Reply"), 'is_reply': True,
             'question': question})


@enforce_condition(contest_exists & is_contest_admin)
def get_messages_authors_view(request, contest_id):
    if len(request.REQUEST.get('substr', '')) < 1:
        raise Http404
    substr = request.REQUEST['substr'].split()

    if len(substr) > 2:
        q_expression = Q(author__first_name__icontains=' '.join(substr[:- 1]),
                         author__last_name__icontains=substr[- 1])
    elif len(substr) == 2:
        q_expression = Q(author__first_name__icontains=substr[0],
                         author__last_name__icontains=substr[1]) | \
                       Q(author__first_name__icontains=' '.join(substr))
    else:
        q_expression = Q(author__username__icontains=substr[0]) | \
                       Q(author__first_name__icontains=substr[0]) | \
                       Q(author__last_name__icontains=substr[0])

    users = visible_messages(request).filter(q_expression).order_by('author') \
        .values('author').distinct().values_list('author__username',
        'author__first_name', 'author__last_name')[:getattr(settings,
                                                            'NUM_HINTS', 10)]
    users = ['%s (%s %s)' % u for u in users]
    return HttpResponse(json.dumps(users), content_type='application/json')
