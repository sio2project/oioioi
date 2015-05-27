from django.db.models.signals import post_save
from django.dispatch import receiver
from oioioi.gamification.experience import PROBLEM_EXPERIENCE_SOURCE
from oioioi.gamification.models import ProblemDifficulty


@receiver(post_save, sender=ProblemDifficulty)
def recalculate_on_difficulty_update(sender, instance, created, **kwargs):
    PROBLEM_EXPERIENCE_SOURCE.force_recalculate_problem(instance.problem)
