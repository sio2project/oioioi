from django.template.loader import render_to_string

from oioioi.contests.controllers import ContestController
from oioioi.questions.views import messages_template_context, visible_messages


class QuestionsContestControllerMixin(object):
    """ContestController mixin that adds participants' questions to his info.
    """

    def get_contest_participant_info_list(self, request, user):
        messages = messages_template_context(request, visible_messages(request,
                author=user))

        prev = super(QuestionsContestControllerMixin, self) \
                .get_contest_participant_info_list(request, user)
        if messages:
            prev.append((30, render_to_string('questions/user_list_table.html',
                    {'contest': request.contest,
                     'hide_author': True,
                     'records': messages,
                     'user': request.user})))
        return prev

ContestController.mix_in(QuestionsContestControllerMixin)
