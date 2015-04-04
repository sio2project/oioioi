from oioioi.base.utils import ObjectWithMixins
from oioioi.base.permissions import make_condition

class CodeSharingController(ObjectWithMixins):
    """
    When viewing a programming problem, we want to compare our code with our
    friends. This class provides api for actually getting access permissions
    and a list of visible codes for us. If in the future we want to have
    different permissions for accessing code than just friends,
    this controller can be extended with mixins.
    Actually implementing friends-based permissions are done in other class -
    this is because we might not want to use friends at all and skip that.
    """

    def can_see_code(self, task, user_requester, user_sharing):
        """
        This functions returns a bool indicating whether the requester can
        see code of sharer for the task
        """
        pass

    def shared_with_me(self, task, user):
        """
        This functions returns a list of all the possible codes the user can
        see for the provided task
        """
        pass