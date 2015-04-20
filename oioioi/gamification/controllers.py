from oioioi.base.utils import ObjectWithMixins
from oioioi.base.permissions import make_condition


class CodeSharingController(ObjectWithMixins):
    """When viewing a programming problem, we want to compare our code with our
       friends. This class provides api for actually getting access permissions
       and a list of visible codes for us. If in the future we want to have
       different permissions for accessing code than just friends,
       this controller can be extended with mixins.
       Actually implementing friends-based permissions are done in other class
       - this is because we might not want to use friends at all and skip that.
    """

    def can_see_code(self, task, user_requester, user_sharing):
        """This functions returns a bool indicating whether the requester can
           see code of sharer for the task
        """
        pass

    def shared_with_me(self, task, user):
        """This functions returns a list of all the possible codes the user can
           see for the provided task
        """
        pass


class TaskSuggestionController(ObjectWithMixins):
    """Since we're collecting some data about the user we can somehow suggest a
       task for him to complete on theirs learning level, this controller is
       the API. To provide your implementation you should mix-in with this
       class and override suggest_task which should return a suggested problem
       for the user. You might want to also call super and do something with
       the task you got from a mixed-in object higher in hierarchy, but it's
       not required

       Warning though, this controller might return None if no task is
       suggested eg. no tasks in the database
    """

    def suggest_task(self, user):
        """Returns a problem object as a suggestion for the user or None if no
           suggestion can be returned
        """
        return None
