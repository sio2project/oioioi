from oioioi.base.utils import jsonify
from oioioi.status.utils import get_status


@jsonify
def get_status_view(request):
    return get_status(request)
