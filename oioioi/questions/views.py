import calendar
from datetime import UTC, datetime

from django.apps import apps
from django.conf import settings
from django.contrib import messages as django_messages
from django.core.exceptions import PermissionDenied, ValidationError
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
from oioioi.base.utils.user_selection import UserSelectionField, get_user_hints_view
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    is_contest_archived,
    is_contest_basicadmin,
    visible_rounds,
)
from oioioi.questions.forms import (
    AddContestMessageForm,
    AddPrivateMessageForm,
    AddPrivateReplyForm,
    AddQuestionMessageForm,
    AddReplyForm,
    FilterMessageAdminForm,
    FilterMessageForm,
    NewsMessageForm,
    get_active_contest_participants,
    get_selected_private_message_recipients,
)
from oioioi.questions.mails import new_question_signal
from oioioi.questions.models import Message, MessageView, QuestionSubscription, ReplyTemplate
from oioioi.questions.utils import (
    get_add_question_message,
    get_categories,
    get_news_message,
    log_addition,
    unanswered_questions,
)


def visible_messages(request, author=None, category=None, kind=None):
    rounds_ids = [round.id for round in visible_rounds(request)]
    q_expression = Q(round_id__in=rounds_ids)
    if author:
        q_expression = q_expression & Q(author=author)
    if category:
        category_type, _, category_id = category.partition("_")
        if category_type == "p":
            q_expression = q_expression & Q(problem_instance__id=category_id)
        elif category_type == "r":
            q_expression = q_expression & Q(round__id=category_id, problem_instance=None)
    if kind:
        q_expression = q_expression & Q(kind=kind)
    messages = Message.objects.filter(q_expression).order_by("-date")
    if not is_contest_basicadmin(request):
        q_expression = Q(kind="PUBLIC")
        if request.user.is_authenticated:
            q_expression = (
                q_expression
                | (Q(author=request.user) & Q(kind="QUESTION"))
                | Q(top_reference__author=request.user)
                | Q(kind="PRIVATE", recipients=request.user)
            )
        q_time = (
            Q(date__lte=request.timestamp)
            & (Q(pub_date__isnull=True) | Q(pub_date__lte=request.timestamp))
            & ((Q(top_reference__isnull=True)) | Q(top_reference__pub_date__isnull=True) | Q(top_reference__pub_date__lte=request.timestamp))
        )
        messages = messages.filter(q_expression, q_time).distinct()

    return messages.select_related("top_reference", "author", "problem_instance", "round", "problem_instance__problem")


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
    new_ids = new_messages(request, messages).values_list("id", flat=True)

    if is_contest_basicadmin(request):
        unanswered = unanswered_questions(messages)
    else:
        unanswered = []

    def make_entry(message):
        link_message = message.top_reference if message.top_reference in messages else message
        if message.top_reference_id is not None and message.top_reference.kind == "PRIVATE":
            link = message.get_absolute_url()
        else:
            link = reverse("message", kwargs={"contest_id": request.contest.id, "message_id": link_message.id})
        return {
            "message": message,
            "link": link,
            "link_message": link_message,
            "needs_reply": message in unanswered,
            "read": message.id not in new_ids,
        }

    to_display = [make_entry(message) for message in messages if message.id not in replied_ids]

    def key(entry):
        return entry["needs_reply"], entry["message"].get_user_date()

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

    category = form.cleaned_data.get("category")
    author = form.cleaned_data.get("author")
    message_type = form.cleaned_data.get("message_type", FilterMessageForm.TYPE_ALL_MESSAGES)
    message_kind = "PUBLIC" if message_type == FilterMessageForm.TYPE_PUBLIC_ANNOUNCEMENTS else None

    all_errors = ["{}: {}".format(form.fields[field].label, ",".join(errors)) for field, errors in form.errors.items()]
    are_all_values_default = (
        (not category or category == FilterMessageForm.TYPE_ALL_CATEGORIES)
        and (not message_type or message_type == FilterMessageForm.TYPE_ALL_MESSAGES)
        and not author
    )
    form = create_form(initial=form.cleaned_data)

    return (
        {
            "author": author,
            "category": category,
            "kind": message_kind,
        },
        {
            "form": form,
            "display_labels": False,
            "all_errors": all_errors,
            "are_all_values_default": are_all_values_default,
        },
    )


@menu_registry.register_decorator(
    _("Questions and news"),
    lambda request: reverse("contest_messages", kwargs={"contest_id": request.contest.id}),
    order=450,
)
@enforce_condition(contest_exists & can_enter_contest)
def messages_view(request):
    vmsg_kwargs, template_kwargs = process_filter_form(request)
    messages = messages_template_context(request, visible_messages(request, **vmsg_kwargs))

    if request.user.is_authenticated:
        subscribe_records = QuestionSubscription.objects.filter(contest=request.contest, user=request.user)
        already_subscribed = len(subscribe_records) > 0
        no_email = request.user.email is None
    else:
        already_subscribed = None
        no_email = None

    return TemplateResponse(
        request,
        "questions/list.html",
        {
            "records": messages,
            "questions_on_page": getattr(settings, "QUESTIONS_ON_PAGE", 30),
            "categories": get_categories(request),
            "already_subscribed": already_subscribed,
            "no_email": no_email,
            "onsite": request.contest.controller.is_onsite(),
            "message": get_news_message(request),
            "is_contest_archived": is_contest_archived(request),
            **template_kwargs,
        },
    )


@enforce_condition(contest_exists & can_enter_contest)
def all_messages_view(request):
    def make_entry(m):
        return {
            "message": m,
            "replies": [],
            "timestamp": m.get_user_date(),  # only for messages ordering
            "is_new": m in new_msgs,
            "has_new_message": m in new_msgs,  # only for messages ordering
            "needs_reply": m in unanswered,
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
            parent["replies"].append(entry)
            parent["timestamp"] = max(parent["timestamp"], entry["timestamp"])
            parent["has_new_message"] = max(parent["has_new_message"], entry["has_new_message"])
        else:
            tree[m.id] = entry

    if is_contest_basicadmin(request):

        def sort_key(x):
            return (x["needs_reply"], x["has_new_message"], x["timestamp"])
    else:

        def sort_key(x):
            return (x["has_new_message"], x["needs_reply"], x["timestamp"])

    tree_list = sorted(tree.values(), key=sort_key, reverse=True)
    for entry in tree_list:
        entry["replies"].sort(key=sort_key, reverse=True)

    if request.user.is_authenticated:
        mark_messages_read(request.user, vmessages)

    return TemplateResponse(
        request,
        "questions/tree.html",
        {
            "tree_list": tree_list,
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
                kind="QUESTION",
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
    return redirect("message", message_id=message_id)


@enforce_condition(contest_exists & can_enter_contest)
def message_visit_view(request, message_id):
    message = get_object_or_404(Message, id=message_id, contest_id=request.contest.id)
    vmessages = visible_messages(request)
    if not vmessages.filter(id=message_id).exists():
        raise PermissionDenied
    if message.top_reference_id is None:
        replies = list(vmessages.filter(top_reference=message))
        if message.kind == "PRIVATE" and not is_contest_basicadmin(request):
            replies = [reply for reply in replies if reply.recipients.filter(id=request.user.id).exists()]
        replies.sort(key=Message.get_user_date)
    else:
        replies = []
    if request.user.is_authenticated:
        mark_messages_read(request.user, [message] + replies)
    return HttpResponse("OK", "text/plain", 201)


def _private_message_root(message):
    if message.kind == "PRIVATE" and message.top_reference_id is None:
        return message
    if message.top_reference_id is not None and message.top_reference.kind == "PRIVATE" and message.top_reference.top_reference_id is None:
        return message.top_reference
    return None


def _private_conversation_recipient(request, requested_message, message, recipient_id):
    is_admin = is_contest_basicadmin(request)
    if recipient_id is not None:
        recipient = get_object_or_404(message.recipients, id=recipient_id)
    elif requested_message.top_reference_id is not None:
        recipient = requested_message.recipients.first()
    elif not is_admin:
        recipient = request.user
    elif message.recipients.count() == 1:
        recipient = message.recipients.first()
    else:
        recipient = None

    if recipient is not None and not message.recipients.filter(id=recipient.id).exists():
        raise PermissionDenied
    if not is_admin and recipient != request.user:
        raise PermissionDenied
    return recipient


@enforce_condition(contest_exists & can_enter_contest)
def message_view(request, message_id, recipient_id=None):
    requested_message = get_object_or_404(Message, id=message_id, contest_id=request.contest.id)
    vmessages = visible_messages(request)
    if not vmessages.filter(id=requested_message.id).exists():
        raise PermissionDenied

    message = _private_message_root(requested_message) or requested_message
    conversation_recipient = None
    private_recipients = None
    if message.kind == "PRIVATE" and message.top_reference_id is None:
        conversation_recipient = _private_conversation_recipient(request, requested_message, message, recipient_id)
        if conversation_recipient is None:
            replies = []
            private_recipients = message.recipients.order_by("username")
        else:
            replies = list(vmessages.filter(top_reference=message, recipients=conversation_recipient))
    elif message.top_reference_id is None:
        replies = list(vmessages.filter(top_reference=message))
    else:
        replies = []

    if message.top_reference_id is None:
        replies.sort(key=Message.get_user_date)

    private_message_published = message.pub_date is None or message.pub_date <= request.timestamp
    private_conversation = message.kind == "PRIVATE" and message.top_reference_id is None and conversation_recipient is not None and private_message_published
    can_reply_to_question = is_contest_basicadmin(request) and message.kind == "QUESTION"
    if (private_conversation or can_reply_to_question) and message.can_have_replies and not is_contest_archived(request):
        form_class = AddPrivateReplyForm if private_conversation else AddReplyForm
        if request.method == "POST":
            form = form_class(request, request.POST)

            if request.POST.get("just_reload") != "yes" and form.is_valid():
                instance = form.save(commit=False)
                instance.top_reference = message
                instance.author = request.user
                instance.date = request.timestamp
                if private_conversation:
                    instance.kind = "PRIVATE"
                    with transaction.atomic():
                        instance.save()
                        instance.recipients.set([conversation_recipient])
                else:
                    instance.save()

                log_addition(request, instance)
                if private_conversation:
                    return redirect(instance.get_absolute_url())
                return redirect("contest_messages", contest_id=request.contest.id)
            elif request.POST.get("just_reload") == "yes":
                form.is_bound = False
        else:
            form = form_class(
                request,
                initial={
                    "topic": _("Re: %s") % message.topic,
                },
            )
    else:
        form = None
    if request.user.is_authenticated:
        mark_messages_read(request.user, [message] + replies)
    display_user = conversation_recipient or message.author
    if private_recipients is not None:
        display_user = None
    return TemplateResponse(
        request,
        "questions/message.html",
        {
            "message": message,
            "replies": replies,
            "form": form,
            "reply_to_id": message.top_reference_id or message.id,
            "timestamp": request_time_seconds(request),
            "conversation_recipient": conversation_recipient,
            "display_user": display_user,
            "private_recipients": private_recipients,
        },
    )


@enforce_condition(not_anonymous & contest_exists & is_contest_basicadmin & ~is_contest_archived)
def add_private_message_view(request):
    if request.method == "POST":
        form = AddPrivateMessageForm(request, request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.author = request.user
            instance.kind = "PRIVATE"
            instance.date = request.timestamp
            with transaction.atomic():
                instance.save()
                form.save_recipients(instance)
            log_addition(request, instance)
            return redirect("contest_messages", contest_id=request.contest.id)
    else:
        form = AddPrivateMessageForm(request)

    return TemplateResponse(
        request,
        "questions/add.html",
        {
            "form": form,
            "private_message": True,
            "title": _("Send private message"),
        },
    )


@enforce_condition(not_anonymous & contest_exists & can_enter_contest & ~is_contest_archived)
def add_contest_message_view(request):
    is_admin = is_contest_basicadmin(request)
    if request.method == "POST":
        form = AddContestMessageForm(request, request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.author = request.user
            if is_admin:
                instance.kind = "PUBLIC"
            else:
                instance.kind = "QUESTION"
                instance.pub_date = None
            instance.date = request.timestamp
            instance.save()
            if instance.kind == "QUESTION":
                new_question_signal.send(sender=Message, request=request, instance=instance)
            log_addition(request, instance)
            return redirect("contest_messages", contest_id=request.contest.id)

    else:
        initial = {}
        for field in ("category", "topic", "content"):
            if field in request.GET:
                initial[field] = request.GET[field]
        form = AddContestMessageForm(request, initial=initial)

    if is_admin:
        title = _("Add news")
    else:
        title = _("Ask question")

    return TemplateResponse(
        request,
        "questions/add.html",
        {
            "form": form,
            "title": title,
            "is_news": is_admin,
            "message": get_add_question_message(request),
        },
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def get_messages_authors_view(request):
    queryset = visible_messages(request)
    return get_user_hints_view(request, "substr", queryset, "author")


@enforce_condition(contest_exists & is_contest_basicadmin)
def get_private_message_recipients_view(request):
    queryset = get_active_contest_participants(request)
    return get_user_hints_view(request, "substr", queryset)


@jsonify
@enforce_condition(contest_exists & is_contest_basicadmin)
def get_private_message_recipients_preview_view(request):
    active_participants = get_active_contest_participants(request)
    recipient_field = UserSelectionField(queryset=active_participants, required=False)
    try:
        recipient = recipient_field.clean(request.GET.get("recipient"))
    except ValidationError:
        recipient = None
    group_ids = [group_id for group_id in request.GET.getlist("groups[]") if group_id.isdigit()]
    groups = ()
    if apps.is_installed("oioioi.usergroups"):
        from oioioi.usergroups.models import UserGroup

        groups = UserGroup.objects.filter(contests=request.contest, id__in=group_ids)
    recipients = get_selected_private_message_recipients(request, recipient, groups).order_by("username")
    return [{"username": recipient.username, "full_name": recipient.get_full_name()} for recipient in recipients]


@jsonify
@enforce_condition(contest_exists & is_contest_basicadmin)
def get_reply_templates_view(request):
    templates = ReplyTemplate.objects.filter(Q(contest=request.contest.id) | Q(contest__isnull=True)).order_by("-usage_count")
    return [{"id": t.id, "name": t.visible_name, "content": t.content} for t in templates]


@enforce_condition(contest_exists & is_contest_basicadmin)
def increment_template_usage_view(request, template_id=None):
    try:
        template = ReplyTemplate.objects.filter(id=template_id).filter(Q(contest=request.contest.id) | Q(contest__isnull=True)).get()
    except ReplyTemplate.DoesNotExist:
        raise Http404

    template.usage_count += 1
    template.save()
    return HttpResponse("OK", content_type="text/plain")


@jsonify
@enforce_condition(contest_exists)
def check_new_messages_view(request, topic_id):
    timestamp = int(request.GET["timestamp"])
    date = datetime.fromtimestamp(timestamp, tz=UTC)
    output = [
        [
            x.topic,
            Truncator(x.content).chars(settings.MEANTIME_ALERT_MESSAGE_SHORTCUT_LENGTH),
            x.id,
        ]
        for x in visible_messages(request).filter(top_reference_id=topic_id).filter(date__gte=date)
    ]
    return {"timestamp": request_time_seconds(request), "messages": output}


@require_http_methods(["GET", "POST"])
@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def subscription(request):
    mgr = QuestionSubscription.objects
    ctxt = {"contest": request.contest, "user": request.user}
    entries = mgr.filter(**ctxt)
    subscribed = entries.exists()

    if request.method == "POST":
        should_add = request.POST["add_subscription"] == "true"
        incorrect = should_add == subscribed

        if incorrect:
            return HttpResponseBadRequest(f"Inconsistent POST request, should_add = {should_add}, subscribed = {subscribed}")
        elif not should_add:
            entries.delete()
        else:
            QuestionSubscription.objects.create(**ctxt)

        return HttpResponse("OK")
    else:
        # request.method == 'GET', enforced by decorator
        return HttpResponse(subscribed)


@enforce_condition(contest_exists & is_contest_basicadmin)
def news_edit_view(request):
    instance = get_news_message(request)
    if request.method == "POST":
        form = NewsMessageForm(request, request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect("contest_messages", contest_id=request.contest.id)
    else:
        form = NewsMessageForm(request, instance=instance)
    return TemplateResponse(
        request,
        "public_message/edit.html",
        {"form": form, "title": _("Edit news message")},
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def add_edit_message_view(request):
    instance = get_add_question_message(request)
    if request.method == "POST":
        form = AddQuestionMessageForm(request, request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect("contest_messages", contest_id=request.contest.id)
    else:
        form = AddQuestionMessageForm(request, instance=instance)
    return TemplateResponse(
        request,
        "public_message/edit.html",
        {"form": form, "title": _("Edit add question message")},
    )
