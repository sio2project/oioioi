from oioioi.problems.models import Problem
from oioioi.sharingcli.models import RemoteProblemURL


def save_url(env):
    problem = Problem.objects.get(id=env['problem_id'])
    purl, _created = RemoteProblemURL.objects.get_or_create(
            problem=problem)
    purl.url = env['url']
    purl.save()
    return env
