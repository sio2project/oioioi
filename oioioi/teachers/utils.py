from oioioi.participants.models import Participant
from oioioi.teachers.models import ContestTeacher, Teacher
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def get_user_teacher_obj(user):
    try:
        return user.teacher
    except Teacher.DoesNotExist:
        return None


def is_user_already_in_contest(user, contest):
    teacher = get_user_teacher_obj(user)

    if user.participant_set.filter(contest=contest) or \
       (teacher and
       teacher.contestteacher_set.filter(contest=contest)):
        return True

    return False


def validate_can_add_user_to_contest(user, contest, member_type):
    exists = False

    if not is_user_already_in_contest(user, contest):
        if member_type == 'pupil':
            exists = len(Participant.objects.filter(
                contest=contest, user=user
            )) > 0
        elif member_type == 'teacher':
            if teacher := get_user_teacher_obj(user):
                exists = len(ContestTeacher.objects.filter(
                    contest=contest, teacher=teacher
                )) > 0
            else:
                raise ValidationError(
                    _("User is not a teacher: \'%(user)s\'")
                    % {"user": user })
        else:
            raise ValueError("Invalid member type")
    else:
        exists = True

    if exists:
        raise ValidationError(
            _("User is already added: \'%(user)s\'")
            % { "user": user })


def add_user_to_contest_as(user, contest, member_type):
    validate_can_add_user_to_contest(user, contest, member_type)
    created = False

    if member_type == 'pupil':
        Participant.objects.get_or_create(
            contest=contest, user=user
        )
    elif member_type == 'teacher':
        teacher = get_user_teacher_obj(user)
        ContestTeacher.objects.get_or_create(
            contest=contest, teacher=teacher
        )
