from django.core.signing import BadSignature, Signer

from oioioi.problems.models import Problem
from oioioi.zeus.models import ZeusProblemData


def is_zeus_problem(problem):
    try:
        return bool(problem.zeusproblemdata)
    except ZeusProblemData.DoesNotExist:
        return False


def filter_zeus_problem_instances(problem_instances):
    # Not returning new query_set because `instances` may have some cache in it
    problems = frozenset(
        Problem.objects.filter(
            pk__in=[p.problem.pk for p in problem_instances]
        ).exclude(zeusproblemdata=None)
    )
    return [pi for pi in problem_instances if pi.problem in problems]


# Note:
# "Unlike your SECRET_KEY, your salt argument does not need to stay secret."
# https://docs.djangoproject.com/en/1.9/topics/signing/#using-the-salt-argument
ZEUS_URL_SALT = 'zeus_url_salt'


def zeus_url_signature(submission_id):
    signer = Signer(salt=ZEUS_URL_SALT)
    return signer.sign(submission_id)


def verify_zeus_url_signature(submission_id, signature):
    signer = Signer(salt=ZEUS_URL_SALT)
    try:
        return signer.unsign(signature) == submission_id
    except BadSignature:
        return False
