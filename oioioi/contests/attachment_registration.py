import sys

from oioioi.base.menu import OrderedRegistry


class AttachmentRegistry(object):
    """Maintains a collection of functions that
    return attachments for 'Downloads' view.
    """

    def __init__(self):
        self._registry = OrderedRegistry()

    def register(self, attachment_generator=None, order=sys.maxsize):
        """Register function generating attachments.

        :Parameters:
            Function that takes elements from `**kwargs` as arguments and
            returns dictionary containing following keys: `category`,
            `name`, `description`, `link`, `pub_date`, `admin_only`.
        """
        if attachment_generator is not None:
            self._registry.register(attachment_generator, order)

    def to_list(self, **kwargs):
        attachments = []
        for idx, gen in enumerate(self._registry):
            attachments.extend(gen(**kwargs))
        return attachments


# The default attachment registry
attachment_registry = AttachmentRegistry()
attachment_registry_problemset = AttachmentRegistry()
