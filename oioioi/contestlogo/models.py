from django.db import models
from oioioi.contests.models import Contest

class ContestLogo(models.Model):
    contest = models.OneToOneField(Contest, primary_key=True)
    logo_url = models.CharField(max_length=255)
