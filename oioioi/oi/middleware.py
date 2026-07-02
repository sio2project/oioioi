from django.shortcuts import redirect
from django.urls import reverse

from oioioi.base.utils import is_ajax
from oioioi.oi.utils import get_participant_requiring_data_confirmation


class OIDataConfirmationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self._process_request(request)
        if response is None:
            return self.get_response(request)
        return response

    def _process_request(self, request):
        if not getattr(request, "contest", None):
            return None

        # Only redirect real page navigations, not background AJAX.
        if is_ajax(request):
            return None

        if get_participant_requiring_data_confirmation(request) is None:
            return None

        confirm_url = reverse("oi_confirm_data", kwargs={"contest_id": request.contest.id})
        if request.path == confirm_url:
            return None

        return redirect(confirm_url)
