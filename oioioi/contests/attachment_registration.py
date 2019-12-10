import sys

from oioioi.base.menu import OrderedRegistry


class AttachmentRegistry(object):
    """Maintains a collection of functions that
       return attachments for 'Files' view.
    """

    def __init__(self):
        self._registry = OrderedRegistry()

    def register(self, attachment_generator=None, order=sys.maxsize):
        """Register function generating attachments.

            :Parameters:
              `attachment_generator` : `function`
                Function that takes `request` as an argument and
                returns dictionary containing following keys: `category`,
                `name`, `description`, `link`, `pub_date`.
        """
        if attachment_generator is not None:
            self._registry.register(attachment_generator, order)

    def to_list(self, request):
        attachments = []
        for idx, gen in enumerate(self._registry):
            attachments.extend(gen(request))
        return attachments


# The default attachment registry
attachment_registry = AttachmentRegistry()
