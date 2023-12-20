import calendar
from datetime import datetime, timezone

from django.conf import settings
from django.contrib import messages as django_messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.utils import jsonify
from oioioi.base.utils.user_selection import get_user_hints_view
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    is_contest_basicadmin,
    visible_rounds,
)
from oioioi.questions.forms import (
    AddContestMessageForm,
    AddReplyForm,
    FilterMessageAdminForm,
    FilterMessageForm,
)
from oioioi.questions.mails import new_question_signal
from oioioi.questions.models import (
    Message,
    MessageView,
    QuestionSubscription,
    ReplyTemplate,
)
from oioioi.questions.utils import get_categories, log_addition, unanswered_questions


def visible_messages(request, author=None, category=None, kind=None):
    rounds_ids = [round.id for round in visible_rounds(request)]
    q_expression = Q(round_id__in=rounds_ids)
    if author:
        q_expression = q_expression & Q(author=author)
    if category:
        category_type, _, category_id = category.partition('_')
        if category_type == 'p':
            q_expression = q_expression & Q(problem_instance__id=category_id)
        elif category_type == 'r':
            q_expression = q_expression & Q(
                round__id=category_id, problem_instance=None
            )
    if kind:
        q_expression = q_expression & Q(kind=kind)
    messages = Message.objects.filter(q_expression).order_by('-date')
    if not is_contest_basicadmin(request):
        q_expression = Q(kind='PUBLIC')
        if request.user.is_authenticated:
            q_expression = (
                q_expression
                | (Q(author=request.user) & Q(kind='QUESTION'))
                | Q(top_reference__author=request.user)
            )
        q_time = (
            Q(date__lte=request.timestamp)
            & ((Q(pub_date__isnull=True) | Q(pub_date__lte=request.timestamp)))
            & (
                (Q(top_reference__isnull=True))
                | Q(top_reference__pub_date__isnull=True)
                | Q(top_reference__pub_date__lte=request.timestamp)
            )
        )
        messages = messages.filter(q_expression, q_time)

    return messages.select_related(
        'top_reference', 'author', 'problem_instance', 'problem_instance__problem'
    )


def new_messages(request, messages=None):
    if not request.user.is_authenticated:
        return messages.none()
    if messages is None:
        messages = visible_messages(request)
    return messages.exclude(messageview__user=request.user).exclude(author=request.user)


def request_time_seconds(request):
    return calendar.timegm(request.timestamp.timetuple())


def messages_template_context(request, messages):
    replied_ids = frozenset(m.top_reference_id for m in messages)
    new_ids = new_messages(request, messages).values_list('id', flat=True)

    if is_contest_basicadmin(request):
        unanswered = unanswered_questions(messages)
    else:
        unanswered = []

    to_display = [
        {
            'message': m,
            'link_message': m.top_reference if m.top_reference in messages else m,
            'needs_reply': m in unanswered,
            'read': m.id not in new_ids,
        }
        for m in messages
        if m.id not in replied_ids
    ]

    def key(entry):
        return entry['needs_reply'], entry['message'].get_user_date()

    to_display.sort(key=key, reverse=True)
    return to_display


def process_filter_form(request):
    def create_form(*args, **kwargs):
        if is_contest_basicadmin(request):
            return FilterMessageAdminForm(request, *args, **kwargs)
        else:
            return FilterMessageForm(request, *args, **kwargs)

    form = create_form(request.GET)
    form.is_valid()

    category = form.cleaned_data.get('category')
    author = form.cleaned_data.get('author')
    message_type = form.cleaned_data.get(
        'message_type', FilterMessageForm.TYPE_ALL_MESSAGES
    )
    message_kind = (
        'PUBLIC'
        if message_type == FilterMessageForm.TYPE_PUBLIC_ANNOUNCEMENTS
        else None
    )

    all_errors = [
        '%s: %s' % (form.fields[field].label, ','.join(errors))
        for field, errors in form.errors.items()
    ]
    are_all_values_default = (
        (not category or category == FilterMessageForm.TYPE_ALL_CATEGORIES)
        and (not message_type or message_type == FilterMessageForm.TYPE_ALL_MESSAGES)
        and not author
    )
    form = create_form(initial=form.cleaned_data)

    return (
        {
            'author': author,
            'category': category,
            'kind': message_kind,
        },
        {
            'form': form,
            'display_labels': False,
            'all_errors': all_errors,
            'are_all_values_default': are_all_values_default,
        },
    )


@menu_registry.register_decorator(
    _("Questions and news"),
    lambda request: reverse(
        'contest_messages', kwargs={'contest_id': request.contest.id}
    ),
    order=450,
)
@enforce_condition(contest_exists & can_enter_contest)
def messages_view(request):
    vmsg_kwargs, template_kwargs = process_filter_form(request)
    messages = messages_template_context(
        request, visible_messages(request, **vmsg_kwargs)
    )

    if request.user.is_authenticated:
        subscribe_records = QuestionSubscription.objects.filter(
            contest=request.contest, user=request.user
        )
        already_subscribed = len(subscribe_records) > 0
        no_email = request.user.email is None
    else:
        already_subscribed = None
        no_email = None

    return TemplateResponse(
        request,
        'questions/list.html',
        {
            'records': messages,
            'questions_on_page': getattr(settings, 'QUESTIONS_ON_PAGE', 30),
            'categories': get_categories(request),
            'already_subscribed': already_subscribed,
            'no_email': no_email,
            'onsite': request.contest.controller.is_onsite(),
            **template_kwargs,
        },
    )


@enforce_condition(contest_exists & can_enter_contest)
def all_messages_view(request):
    def make_entry(m):
        return {
            'message': m,
            'replies': [],
            'timestamp': m.get_user_date(),  # only for messages ordering
            'is_new': m in new_msgs,
            'has_new_message': m in new_msgs,  # only for messages ordering
            'needs_reply': m in unanswered,
        }

    vmsg_kwargs, template_kwargs = process_filter_form(request)
    vmessages = visible_messages(request, **vmsg_kwargs)
    new_msgs = frozenset(new_messages(request, vmessages))
    unanswered = unanswered_questions(vmessages)
    tree = {m.id: make_entry(m) for m in vmessages if m.top_reference is None}

    for m in vmessages:
        if m.id in tree:
            continue
        entry = make_entry(m)
        if m.top_reference_id in tree:
            parent = tree[m.top_reference_id]
            parent['replies'].append(entry)
            parent['timestamp'] = max(parent['timestamp'], entry['timestamp'])
            parent['has_new_message'] = max(
                parent['has_new_message'], entry['has_new_message']
            )
        else:
            tree[m.id] = entry

    if is_contest_basicadmin(request):
        sort_key = lambda x: (x['needs_reply'], x['has_new_message'], x['timestamp'])
    else:
        sort_key = lambda x: (x['has_new_message'], x['needs_reply'], x['timestamp'])
    tree_list = sorted(list(tree.values()), key=sort_key, reverse=True)
    for entry in tree_list:
        entry['replies'].sort(key=sort_key, reverse=True)

    if request.user.is_authenticated:
        mark_messages_read(request.user, vmessages)

    return TemplateResponse(
        request,
        'questions/tree.html',
        {
            'tree_list': tree_list,
            **template_kwargs,
        },
    )


def mark_messages_read(user, messages):
    for m in messages:
        try:
            MessageView.objects.get_or_create(message=m, user=user)
        except IntegrityError:
            # get_or_create does not guarantee race-free execution, so we
            # silently ignore the IntegrityError from the unique index
            pass


@enforce_condition(contest_exists & is_contest_basicadmin)
@require_POST
def toggle_question_read(request, message_id, read):
    error = None
    with transaction.atomic():
        try:
            question = Message.objects.select_for_update().get(
                id=message_id,
                contest_id=request.contest.id,
                kind='QUESTION',
            )
        except Message.DoesNotExist:
            raise Http404
        if read:
            if not question.marked_read_by:
                question.marked_read_by = request.user
            else:
                error = _("This question has already been marked read!")
        else:
            if question.marked_read_by:
                question.marked_read_by = None
            else:
                error = _("This question has already been marked unread!")
        question.save()
    if error:
        django_messages.error(request, error)
    else:
        django_messages.success(request, _("Success!"))
    return redirect('message', message_id=message_id)


@enforce_condition(contest_exists & can_enter_contest)
def message_visit_view(request, message_id):
    message = get_object_or_404(Message, id=message_id, contest_id=request.contest.id)
    vmessages = visible_messages(request)
    if message.top_reference_id is None:
        replies = list(vmessages.filter(top_reference=message))
        replies.sort(key=Message.get_user_date)
    else:
        replies = []
    if request.user.is_authenticated:
        mark_messages_read(request.user, [message] + replies)
    return HttpResponse('OK', 'text/plain', 201)


@enforce_condition(contest_exists & can_enter_contest)
def message_view(request, message_id):
    message = get_object_or_404(Message, id=message_id, contest_id=request.contest.id)
    vmessages = visible_messages(request)
    if not vmessages.filter(id=message_id):
        raise PermissionDenied
    if message.top_reference_id is None:
        replies = list(vmessages.filter(top_reference=message))
        replies.sort(key=Message.get_user_date)
    else:
        replies = []
    if (
        is_contest_basicadmin(request)
        and message.kind == 'QUESTION'
        and message.can_have_replies
    ):
        if request.method == 'POST':
            form = AddReplyForm(request, request.POST)

            if request.POST.get('just_reload') != 'yes' and form.is_valid():
                instance = form.save(commit=False)
                instance.top_reference = message
                instance.author = request.user
                instance.date = request.timestamp
                instance.save()

                log_addition(request, instance)
                return redirect('contest_messages', contest_id=request.contest.id)
            elif request.POST.get('just_reload') == 'yes':
                form.is_bound = False
        else:
            form = AddReplyForm(
                request,
                initial={
                    'topic': _("Re: %s") % message.topic,
                },
            )
    else:
        form = None
    if request.user.is_authenticated:
        mark_messages_read(request.user, [message] + replies)
    return TemplateResponse(
        request,
        'questions/message.html',
        {
            'message': message,
            'replies': replies,
            'form': form,
            'reply_to_id': message.top_reference_id or message.id,
            'timestamp': request_time_seconds(request),
        },
    )


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def add_contest_message_view(request):
    is_admin = is_contest_basicadmin(request)
    if request.method == 'POST':
        form = AddContestMessageForm(request, request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.author = request.user
            if is_admin:
                instance.kind = 'PUBLIC'
            else:
                instance.kind = 'QUESTION'
                instance.pub_date = None
            instance.date = request.timestamp
            instance.save()
            if instance.kind == 'QUESTION':
                new_question_signal.send(
                    sender=Message, request=request, instance=instance
                )
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

    return TemplateResponse(
        request,
        'questions/add.html',
        {'form': form, 'title': title, 'is_news': is_admin},
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def get_messages_authors_view(request):
    queryset = visible_messages(request)
    return get_user_hints_view(request, 'substr', queryset, 'author')


@jsonify
@enforce_condition(contest_exists & is_contest_basicadmin)
def get_reply_templates_view(request):
    templates = ReplyTemplate.objects.filter(
        Q(contest=request.contest.id) | Q(contest__isnull=True)
    ).order_by('-usage_count')
    return [
        {'id': t.id, 'name': t.visible_name, 'content': t.content} for t in templates
    ]


@enforce_condition(contest_exists & is_contest_basicadmin)
def increment_template_usage_view(request, template_id=None):
    try:
        template = (
            ReplyTemplate.objects.filter(id=template_id)
            .filter(Q(contest=request.contest.id) | Q(contest__isnull=True))
            .get()
        )
    except ReplyTemplate.DoesNotExist:
        raise Http404

    template.usage_count += 1
    template.save()
    return HttpResponse('OK', content_type='text/plain')


@jsonify
@enforce_condition(contest_exists)
def check_new_messages_view(request, topic_id):
    timestamp = int(request.GET['timestamp'])
    # utcfromtimestamp returns a naive datetime
    date = datetime.utcfromtimestamp(timestamp).replace(tzinfo=timezone.utc)
    output = [
        [
            x.topic,
            Truncator(x.content).chars(settings.MEANTIME_ALERT_MESSAGE_SHORTCUT_LENGTH),
            x.id,
        ]
        for x in visible_messages(request)
        .filter(top_reference_id=topic_id)
        .filter(date__gte=date)
    ]
    return {'timestamp': request_time_seconds(request), 'messages': output}


@require_http_methods(["GET", "POST"])
@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def subscription(request):
    mgr = QuestionSubscription.objects
    ctxt = {'contest': request.contest, 'user': request.user}
    entries = mgr.filter(**ctxt)
    subscribed = entries.exists()

    if request.method == 'POST':
        should_add = request.POST['add_subscription'] == 'true'
        incorrect = should_add == subscribed

        if incorrect:
            return HttpResponseBadRequest(
                "Inconsistent POST request, "
                "should_add = {}, subscribed = {}".format(should_add, subscribed)
            )
        elif not should_add:
            entries.delete()
        else:
            QuestionSubscription.objects.create(**ctxt)

        return HttpResponse("OK")
    else:
        # request.method == 'GET', enforced by decorator
        return HttpResponse(subscribed)
