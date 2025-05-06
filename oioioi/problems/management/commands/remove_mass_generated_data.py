import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from oioioi.problems.models import (
    Problem,
    AlgorithmTag,
    DifficultyTag,
)

User = get_user_model()

class Command(BaseCommand):
    help = (
        "Removes all mass-generated mock data created by the mass create tool. "
        "For models which are removed on cascade, a message is output to verify the cascade deletion."
    )

    def handle(self, *args, **options):
        auto_prefix = "auto_"

        # Delete Problems
        prob_qs = Problem.objects.filter(short_name__startswith=auto_prefix)
        prob_count = prob_qs.count()
        prob_qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {prob_count} Problems"))

        # Delete Users
        user_qs = User.objects.filter(username__startswith=auto_prefix)
        user_count = user_qs.count()
        user_qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {user_count} Users"))

        # Delete Algorithm Tags
        algo_tag_qs = AlgorithmTag.objects.filter(name__startswith=auto_prefix)
        algo_tag_count = algo_tag_qs.count()
        algo_tag_qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {algo_tag_count} Algorithm Tags"))

        # Delete Difficulty Tags
        diff_tag_qs = DifficultyTag.objects.filter(name__startswith=auto_prefix)
        diff_tag_count = diff_tag_qs.count()
        diff_tag_qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {diff_tag_count} Difficulty Tags"))

        self.stdout.write(self.style.SUCCESS("Through, Proposal and AggregatedProposal records are deleted on cascade."))
        self.stdout.write(self.style.SUCCESS("Mock data removal complete"))
