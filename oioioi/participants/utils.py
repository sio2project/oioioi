import unicodecsv

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils.encoding import force_unicode

from oioioi.base.permissions import make_request_condition
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.base.utils import request_cached


def is_contest_with_participants(contest):
    rcontroller = contest.controller.registration_controller()
    return isinstance(rcontroller, ParticipantsController)


@make_request_condition
def contest_has_participants(request):
    return is_contest_with_participants(request.contest)


@request_cached
def get_participant(request):
    try:
        return Participant.objects.get(contest=request.contest,
                                       user=request.user)
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
    objects_used = [object]
    objs = [getattr(object, rel.get_accessor_name())
            for rel in object._meta.get_all_related_objects()
            if hasattr(object, rel.get_accessor_name())]
    while objs:
        current = objs.pop(0)
        objects_used.append(current)
        for field in current._meta.fields:
                if field.rel is not None and \
                   getattr(current, field.name) not in objects_used:
                    objs.append(getattr(current, field.name))

    for obj in objects_used:
        for field in obj._meta.fields:
            if not field.auto_created:
                if field.rel is None:
                    result += [(obj, field)]
    return result


def serialize_participants_data(participants):
    """Serializes all personal data of participants to a table.
       :param participants: A QuerySet from table participants.
    """
    if not participants.exists():
        return {'no_participants': True}

    keys = ['username', 'first name', 'last name']

    def key_name((obj, field)):
        return str(obj.__class__.__name__) + ": " + \
                field.verbose_name.title()

    set_of_keys = set(keys)
    for participant in participants:
        for key in map(key_name, _fold_registration_models_tree(participant)):
            if key not in set_of_keys:
                set_of_keys.add(key)
                keys.append(key)

    def key_value((obj, field)):
        return (key_name((obj, field)), field.value_to_string(obj))

    data = []
    for participant in participants:
        values = dict(map(key_value, _fold_registration_models_tree(participant)))
        values['username'] = participant.user.username
        values['first name'] = participant.user.first_name
        values['last name'] = participant.user.last_name
        data.append([values.get(key, '') for key in keys])

    return {'keys': keys, 'data': data}


def render_participants_data_csv(participants, name):
    data = serialize_participants_data(participants)
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename=%s-%s.csv' % \
        (name, "personal-data")
    if not 'no_participants' in data:
        writer = unicodecsv.writer(response)
        writer.writerow(map(force_unicode, data['keys']))
        for row in data['data']:
            writer.writerow(map(force_unicode, row))
    return response
