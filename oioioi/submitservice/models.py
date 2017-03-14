from django.db import models
from django.contrib.auth.models import User


class SubmitServiceToken(models.Model):
    token = models.CharField(max_length=32, unique=True)
    user = models.OneToOneField(User)
