from django.template.loader import render_to_string
from oioioi.gamification.utils import node_progress
from oioioi.portals.widgets import register_widget
import re


class NodeProgressBarWidget(object):
    name = "gamification_nodeprogressbar"
    compiled_tag_regex = re.compile(
        r'\[\[NodeProgressBar\]\]'
    )

    def render(self, request, m):
        completed, all = node_progress(request.current_node, request.user)
        progress_text = str(completed) + ' / ' + str(all)
        progress = (float(completed) / float(all)) if all > 0 else 0.0

        return render_to_string(
                'gamification/widgets/node-progress.html',
                {'percentage': progress * 100.0,
                 'text': progress_text}
            )

register_widget(NodeProgressBarWidget())
