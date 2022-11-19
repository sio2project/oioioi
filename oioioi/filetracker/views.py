import mimetypes
from wsgiref.util import FileWrapper

from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.http import Http404, StreamingHttpResponse


def raw_file_view(request, filename):
    if not filename or filename.startswith('/'):
        raise Http404
    if not request.user.is_superuser:
        raise PermissionDenied
    if not default_storage.exists(filename):
        raise Http404

    file = default_storage.open(filename, 'rb')
    content_type = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
    response = StreamingHttpResponse(FileWrapper(file), content_type=content_type)
    try:
        response['Content-Length'] = default_storage.size(filename)
    except NotImplementedError:
        pass

    return response
