from oioioi.teachers.controllers import TeacherRegistrationController


class UserGroupsParticipantsControllerMixin(object):
    def filter_participants(self, queryset):
        base_qs = super(UserGroupsParticipantsControllerMixin, self)\
            .filter_participants(queryset)
        groups_qs = queryset.filter(usergroups__contests__id=self.contest.id)
        return base_qs | groups_qs

    @classmethod
    def filter_user_contests(cls, request, contest_queryset):
        base_qs = super(UserGroupsParticipantsControllerMixin, cls)\
            .filter_user_contests(request, contest_queryset)
        if not request.user.is_authenticated:
            return base_qs
        groups_qs = contest_queryset.filter(usergroups__members__id=request.user.id)
        return base_qs | groups_qs


TeacherRegistrationController.mix_in(UserGroupsParticipantsControllerMixin)
