from oioioi.contests.models import ProblemInstance
from oioioi.pa.models import PAProblemInstanceData


def save_division(env):
    problem_instance = ProblemInstance.objects.get(id=env["problem_instance_id"])
    pid, created = PAProblemInstanceData.objects.get_or_create(problem_instance=problem_instance)
    pid.division = env["division"]
    pid.save()
    return env
