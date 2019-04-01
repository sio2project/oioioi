from django.db.models import Q

from oioioi.teachers.controllers import TeacherRegistrationController


class UserGroupsParticipantsControllerMixin(object):
    def filter_participants(self, queryset):
        base_qs = super(UserGroupsParticipantsControllerMixin, self)\
            .filter_participants(queryset)
        groups_qs = queryset.filter(usergroups__contests__id=self.contest.id)
        return base_qs | groups_qs

    def user_contests_query(self, request):
        base_query = super(UserGroupsParticipantsControllerMixin, self).user_contests_query(request)
        if not request.user.is_authenticated:
            return base_query
        return base_query | Q(usergroups__members__id=request.user.id)


TeacherRegistrationController.mix_in(UserGroupsParticipantsControllerMixin)
