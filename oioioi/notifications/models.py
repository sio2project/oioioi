from django.contrib.sessions.models import Session
from django.db import models


class NotificationsSession(models.Model):
    uid = models.CharField(max_length=32, unique=True)
    session = models.OneToOneField(Session, on_delete=models.CASCADE)
