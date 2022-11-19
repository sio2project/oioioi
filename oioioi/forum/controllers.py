from oioioi.contests.controllers import ContestController
from oioioi.forum.models import Forum


class ContestControllerWithForum(object):
    """Contest controller defines whether this particular contests needs
    forum application. Set True in a contest controller, if you want
    to let the participants use your forum. Do not change it here!
    This requires adding 'oioioi.forum' in Installed_apps in your settings.py
    """

    create_forum = True

    def adjust_contest(self):
        super(ContestControllerWithForum, self).adjust_contest()
        Forum.objects.get_or_create(contest=self.contest)


ContestController.mix_in(ContestControllerWithForum)
