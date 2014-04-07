from django.db import models
from django.contrib.sessions.models import Session


class NotificationsSession(models.Model):
    uid = models.CharField(max_length=32, unique=True)
    session = models.OneToOneField(Session)
