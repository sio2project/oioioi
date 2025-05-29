from oioioi.oi.models import School


def get_schools(request):
    contest = request.contest
    if contest and hasattr(contest.controller, 'get_filtered_schools'):
        return contest.controller.get_filtered_schools(request)
    return School.objects.filter(is_active=True)
