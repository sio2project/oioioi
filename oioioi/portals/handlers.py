from django.db.models.signals import post_migrate
from django.dispatch import receiver

from oioioi.portals.models import Node
from oioioi.portals.widgets import collect_problems
from oioioi.problems.models import Problem


def update_task_information_cache(node):
    problems = []
    for node_version in node.language_versions.all():
        problems += collect_problems(node_version.panel_code)
    node.problems_in_content.set(Problem.objects.filter(id__in=problems).distinct())


@receiver(post_migrate)
def rebuild_handler(sender, **kwargs):
    # post_migrate is called after each app's migrations
    if sender.name == "oioioi.portals":
        Node.objects.rebuild()
