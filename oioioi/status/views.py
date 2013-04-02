import json

from django.http import HttpResponse

from oioioi.status.utils import get_status


def get_status_view(request, contest_id=None):
    response = get_status(request)
    return HttpResponse(json.dumps(response), content_type='application/json')
