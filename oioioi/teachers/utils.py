from enum import Enum

from oioioi.participants.models import Participant
from oioioi.teachers.models import ContestTeacher, Teacher


def get_user_teacher_obj(user):
    try:
        return user.teacher
    except Teacher.DoesNotExist:
        return None


def is_user_already_in_contest(user, contest):
    teacher = get_user_teacher_obj(user)

    if user.participant_set.filter(contest=contest) or \
            (teacher and teacher.contestteacher_set.filter(contest=contest)):
        return True

    return False


class UserAddResult(Enum):
    Added = 1
    UserIsAlreadyAdded = 2
    UserIsNotATeacher = 3


def add_user_to_contest_as(user, contest, member_type) -> UserAddResult:
    if is_user_already_in_contest(user, contest):
        return UserAddResult.UserIsAlreadyAdded

    created = False
    if member_type == 'pupil':
        _p, created = Participant.objects.get_or_create(
            contest=contest, user=user
        )
    elif member_type == 'teacher':
        if teacher := get_user_teacher_obj(user):
            _ct, created = ContestTeacher.objects.get_or_create(
                contest=contest, teacher=teacher
            )
        else:
            return UserAddResult.UserIsNotATeacher

    if created:
        return UserAddResult.Added
    else:
        return UserAddResult.UserIsAlreadyAdded
