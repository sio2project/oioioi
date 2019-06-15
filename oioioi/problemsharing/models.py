from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


class Friendship(models.Model):
    """Represents a friendship between task creators

    Friends can access user uploaded problems. Friendship is one-sided.
    """
    # "creator" created the friendship (want's their problems to be shared)
    creator = models.ForeignKey(User, on_delete=models.CASCADE,
                                verbose_name=_("creator"),
                                related_name='friendships_created')
    # "receiver" gets access to problems of "creator"
    receiver = models.ForeignKey(User, on_delete=models.CASCADE,
                                 verbose_name=_("receiver"),
                                 related_name='friendships_received')
