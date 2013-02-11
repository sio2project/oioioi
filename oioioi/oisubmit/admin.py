from django.utils.timezone import localtime
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.admin import SubmissionAdmin
from oioioi.oisubmit.models import OISubmitExtraData

class OISubmitSubmissionAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(OISubmitSubmissionAdminMixin, self).__init__(*args, **kwargs)
        self.list_display = self.list_display + ['local_time', 'sio_time',
                                                 'server_time']
        self.list_filter = self.list_filter +['oisubmitextradata__is_suspected']

    def _time(self, instance, kind):
        html = '<span class="subm_admin subm_status %s">%s</span>'
        is_suspected = getattr(instance.oisubmitextradata,'is_suspected', False)
        time = getattr(instance.oisubmitextradata, kind, None)
        if time is not None:
            timestr = localtime(time).strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestr = ''
        return html % ('subm_suspected' if is_suspected else '', timestr)

    def local_time(self, instance):
        return self._time(instance, 'localtime')
    local_time.allow_tags = True
    local_time.short_description = _("user localtime")

    def sio_time(self, instance):
        return self._time(instance, 'siotime')
    sio_time.allow_tags = True
    sio_time.short_description = _("user siotime")

    def server_time(self, instance):
        return self._time(instance, 'servertime')
    server_time.allow_tags = True
    server_time.short_description = _("server time")

    def get_list_select_related(self):
        return super(OISubmitSubmissionAdminMixin, self) \
                .get_list_select_related() + ['oisubmitextradata']

SubmissionAdmin.mix_in(OISubmitSubmissionAdminMixin)
