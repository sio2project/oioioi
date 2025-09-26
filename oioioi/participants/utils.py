from collections import deque

import unicodecsv
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields.related import ForeignKey, OneToOneField
from django.http import HttpResponse
from django.utils.encoding import force_str

from oioioi.base.permissions import make_request_condition
from oioioi.base.utils import request_cached
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant


def is_contest_with_participants(contest):
    rcontroller = contest.controller.registration_controller()
    return isinstance(rcontroller, ParticipantsController)


def is_onsite_contest(contest):
    if not is_contest_with_participants(contest):
        return False
    from oioioi.participants.admin import OnsiteRegistrationParticipantAdmin

    rcontroller = contest.controller.registration_controller()
    padmin = rcontroller.participant_admin
    return padmin and issubclass(padmin, OnsiteRegistrationParticipantAdmin)


@make_request_condition
def contest_has_participants(request):
    return is_contest_with_participants(request.contest)


@make_request_condition
def has_participants_admin(request):
    rcontroller = request.contest.controller.registration_controller()
    return getattr(rcontroller, "participant_admin", None) is not None


@make_request_condition
def contest_is_onsite(request):
    return is_onsite_contest(request.contest)


@request_cached
def get_participant(request):
    try:
        return Participant.objects.get(contest=request.contest, user=request.user)
    except Participant.DoesNotExist:
        return None


@make_request_condition
@request_cached
def can_register(request):
    if get_participant(request) is not None:
        return False
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.can_register(request)


@make_request_condition
@request_cached
def can_edit_registration(request):
    participant = get_participant(request)
    if participant is None:
        return False
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.can_edit_registration(request, participant)


@make_request_condition
@request_cached
def can_unregister(request):
    participant = get_participant(request)
    if participant is None:
        return False
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.can_unregister(request, participant)


@make_request_condition
@request_cached
def is_participant(request):
    rcontroller = request.contest.controller.registration_controller()
    qs = User.objects.filter(id=request.user.id)
    return rcontroller.filter_participants(qs).exists()


def _fold_registration_models_tree(object):
    """Function for serialize_participants_data. Walks over model of
    the object, gets models related to the model and lists
    all their fields."""
    result = []
    objects_used = set()
    objects_used.add(object)

    # https://docs.djangoproject.com/en/1.9/ref/models/meta/#migrating-old-meta-api
    def get_all_related_objects(_meta):
        return [f for f in _meta.get_fields() if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete]

    objs = deque()
    for rel in get_all_related_objects(object._meta):
        if hasattr(object, rel.get_accessor_name()):
            objs.append(getattr(object, rel.get_accessor_name()))

    while objs:
        current = objs.popleft()
        if current is None:
            continue
        objects_used.add(current)

        for field in current._meta.fields:
            if field.remote_field is not None and getattr(current, field.name) not in objects_used:
                objs.append(getattr(current, field.name))

    for obj in objects_used:
        for field in obj._meta.fields:
            if not field.auto_created:
                if field.remote_field is None:
                    result += [(obj, field)]

    return result


def get_related_paths(model, prefix="", depth=5, visited=None):
    if visited is None:
        visited = set()
    if model in visited or depth == 0:
        return []

    visited.add(model)
    paths = []
    try:
        for field in model._meta.get_fields():
            if isinstance(field, (ForeignKey, OneToOneField)) and not field.auto_created:
                related_model = field.related_model
                if related_model == Participant:
                    continue  # skip backward pointer to Participant

                full_path = f"{prefix}__{field.name}" if prefix else field.name
                paths.append(full_path)

                paths.extend(get_related_paths(related_model, prefix=full_path, depth=depth - 1, visited=visited))
    finally:
        visited.remove(model)

    return paths


def serialize_participants_data(request):
    """Serializes all personal data of participants to a table."""
    participant = Participant.objects.filter(contest=request.contest).first()
    if participant is None:
        return {"no_participants": True}

    try:  # Check if registration model exists
        registration_model_instance = participant.registration_model
        registration_model_class = registration_model_instance.__class__
        registration_model_name = registration_model_instance._meta.get_field("participant").remote_field.related_name

        related = get_related_paths(registration_model_class, prefix=registration_model_name, depth=10)
        related.extend(["user", "contest", registration_model_name])
        participants = Participant.objects.filter(contest=request.contest).select_related(*related)
    except ObjectDoesNotExist:  # It doesn't, so no need to select anything
        participants = Participant.objects.filter(contest=request.contest)

    display_email = request.contest.controller.show_email_in_participants_data

    keys = ["username", "user ID", "first name", "last name"] + (["email address"] if display_email else [])

    def key_name(attr):
        (obj, field) = attr
        return str(obj.__class__.__name__) + ": " + field.verbose_name.title()

    folded_participants = [(participant, _fold_registration_models_tree(participant)) for participant in participants]

    set_of_keys = set(keys)
    for participant, folded in folded_participants:
        for key in map(key_name, folded):
            if key not in set_of_keys:
                set_of_keys.add(key)
                keys.append(key)

    def key_value(attr):
        (obj, field) = attr
        return (key_name((obj, field)), field.value_to_string(obj))

    data = []
    for participant, folded in folded_participants:
        values = dict(list(map(key_value, folded)))
        values["username"] = participant.user.username
        values["user ID"] = participant.user.id
        values["first name"] = participant.user.first_name
        values["last name"] = participant.user.last_name
        if display_email:
            values["email address"] = participant.user.email
        data.append([values.get(key, "") for key in keys])

    return {"keys": keys, "data": data}


def render_participants_data_csv(request, name):
    data = serialize_participants_data(request)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=%s-%s.csv" % (
        name,
        "personal-data",
    )
    if "no_participants" not in data:
        writer = unicodecsv.writer(response)
        writer.writerow(list(map(force_str, data["keys"])))
        for row in data["data"]:
            writer.writerow(list(map(force_str, row)))
    return response
