from django.contrib.sessions.models import Session
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def notifications_authenticate_view(request):
    try:
        session = Session.objects.get(notificationssession__uid=request.POST["nsid"])
        user_id = session.get_decoded().get("_auth_user_id")
        return JsonResponse({"user": user_id})
    except KeyError:
        return HttpResponseBadRequest()
    except Session.DoesNotExist:
        return HttpResponse("Unauthorized", status=401)
