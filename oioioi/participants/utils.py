import unicodecsv
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils.encoding import force_str

from oioioi.base.permissions import make_request_condition
from oioioi.base.utils import request_cached
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.contests.models import RegistrationStatus


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
    return getattr(rcontroller, 'participant_admin', None) is not None


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
    #todo: needs adding Registration_Status to all type of contest after this delete can_register
    #return rcontroller.registration_status(request) == RegistrationStatus.OPEN
    return rcontroller.can_register()


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
    objects_used = [object]

    # https://docs.djangoproject.com/en/1.9/ref/models/meta/#migrating-old-meta-api
    def get_all_related_objects(_meta):
        return [
            f
            for f in _meta.get_fields()
            if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete
        ]

    objs = [
        getattr(object, rel.get_accessor_name())
        for rel in get_all_related_objects(object._meta)
        if hasattr(object, rel.get_accessor_name())
    ]
    while objs:
        current = objs.pop(0)
        if current is None:
            continue
        objects_used.append(current)

        for field in current._meta.fields:
            if (
                field.remote_field is not None
                and getattr(current, field.name) not in objects_used
            ):
                objs.append(getattr(current, field.name))

    for obj in objects_used:
        for field in obj._meta.fields:
            if not field.auto_created:
                if field.remote_field is None:
                    result += [(obj, field)]
    return result


def serialize_participants_data(request, participants):
    """Serializes all personal data of participants to a table.
    :param participants: A QuerySet from table participants.
    """

    if not participants.exists():
        return {'no_participants': True}

    display_email = request.contest.controller.show_email_in_participants_data

    keys = ['username', 'user ID', 'first name', 'last name'] + (
        ['email address'] if display_email else []
    )

    def key_name(attr):
        (obj, field) = attr
        return str(obj.__class__.__name__) + ": " + field.verbose_name.title()

    set_of_keys = set(keys)
    for participant in participants:
        for key in map(key_name, _fold_registration_models_tree(participant)):
            if key not in set_of_keys:
                set_of_keys.add(key)
                keys.append(key)

    def key_value(attr):
        (obj, field) = attr
        return (key_name((obj, field)), field.value_to_string(obj))

    data = []
    for participant in participants:
        values = dict(list(map(key_value, _fold_registration_models_tree(participant))))
        values['username'] = participant.user.username
        values['user ID'] = participant.user.id
        values['first name'] = participant.user.first_name
        values['last name'] = participant.user.last_name
        if display_email:
            values['email address'] = participant.user.email
        data.append([values.get(key, '') for key in keys])

    return {'keys': keys, 'data': data}


def render_participants_data_csv(request, participants, name):
    data = serialize_participants_data(request, participants)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s-%s.csv' % (
        name,
        "personal-data",
    )
    if 'no_participants' not in data:
        writer = unicodecsv.writer(response)
        writer.writerow(list(map(force_str, data['keys'])))
        for row in data['data']:
            writer.writerow(list(map(force_str, row)))
    return response
