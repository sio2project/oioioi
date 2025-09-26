from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from oioioi.contests.models import Contest

if "oioioi.usercontests.auth.UserContestAuthBackend" not in settings.AUTHENTICATION_BACKENDS:
    raise ImproperlyConfigured("When using the 'usercontests' module you have to activate UserContestAuthBackend")


class UserContest(models.Model):
    """This class stores information about who created which UserContest.
    It is used to determine who is its rightful admin.
    """

    contest = models.OneToOneField(Contest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
