from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.core.servers.basehttp import FileWrapper
import mimetypes

def raw_file_view(request, filename):
    if not filename or filename.startswith('/'):
        raise Http404
    if not request.user.is_superuser:
        raise PermissionDenied
    if not default_storage.exists(filename):
        raise Http404

    file = default_storage.open(filename, 'rb')
    content_type = mimetypes.guess_type(filename)[0] or \
        'application/octet-stream'
    response = HttpResponse(FileWrapper(file), content_type=content_type)
    response['Content-Length'] = default_storage.size(filename)
    return response
