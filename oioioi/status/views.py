from oioioi.status.utils import get_status
from oioioi.base.utils import jsonify


@jsonify
def get_status_view(request, contest_id=None):
    return get_status(request)
