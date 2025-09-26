from django.db.models.signals import post_migrate
from django.dispatch import receiver

from oioioi.portals.models import Node
from oioioi.portals.widgets import REGISTERED_WIDGETS
from oioioi.problems.models import Problem


def parse_node_for_problems(node):
    """Parses node's content in search for links to problems
    and returns a queryset of problems accessible from the node.
    """
    widgets_with_links = filter(lambda w: hasattr(w, "get_problem_ids"), REGISTERED_WIDGETS)

    ids = []
    for widget in widgets_with_links:
        regex = widget.compiled_tag_regex
        for node_version in node.language_versions.all():
            for m in regex.finditer(node_version.panel_code):
                ids += widget.get_problem_ids(m)

    return Problem.objects.filter(id__in=ids).distinct()


def update_task_information_cache(node):
    node.problems_in_content.set(parse_node_for_problems(node))


@receiver(post_migrate)
def rebuild_handler(sender, **kwargs):
    # post_migrate is called after each app's migrations
    if sender.name == "oioioi.portals":
        Node.objects.rebuild()
