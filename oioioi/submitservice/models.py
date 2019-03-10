from django.contrib.auth.models import User
from django.db import models


class SubmitServiceToken(models.Model):
    token = models.CharField(max_length=32, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
