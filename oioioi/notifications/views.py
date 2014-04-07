from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from oioioi.base.utils import jsonify
from oioioi.notifications.models import NotificationsSession


@csrf_exempt
@require_POST
@jsonify
def notifications_authenticate_view(request):
    not_session = NotificationsSession.objects.filter(uid=request.POST['nsid'])
    if not_session.exists():
        user_id = not_session[0].session.get_decoded().get('_auth_user_id')
        return {'user': user_id, 'status': 'OK'}
    else:
        return {'status': 'UNAUTHORIZED'}
