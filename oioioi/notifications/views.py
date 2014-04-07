from django.contrib.sessions.models import Session
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from oioioi.base.utils import jsonify


@csrf_exempt
@require_POST
@jsonify
def notifications_authenticate_view(request):
    try:
        session = Session.objects.get(notificationssession__uid=
                                      request.POST['nsid'])
        user_id = session.get_decoded().get('_auth_user_id')
        return {'user': user_id, 'status': 'OK'}
    except Session.DoesNotExist:
        return {'status': 'UNAUTHORIZED'}
