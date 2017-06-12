from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from oioioi.base import admin
from oioioi.base.utils import make_html_link
from oioioi.contests.admin import ContestAdmin
from oioioi.contestlogo.models import ContestLogo, ContestIcon


class ContestLogoInline(admin.TabularInline):
    model = ContestLogo
    readonly_fields = ['logo_link']
    exclude = ['updated_at']

    def logo_link(self, instance):
        if instance.id is not None:
            href = reverse('oioioi.contestlogo.views.logo_image_view',
                    kwargs={'contest_id': str(instance.contest.id)})
            return make_html_link(href, instance.filename)
        return None
    logo_link.short_description = _("Filename")


class ContestLogoAdminMixin(object):
    """Adds :class:`~oioioi.contestlogo.models.ContestLogo` to an admin panel.
    """

    def __init__(self, *args, **kwargs):
        super(ContestLogoAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = self.inlines + [ContestLogoInline]
ContestAdmin.mix_in(ContestLogoAdminMixin)


class ContestIconInline(admin.TabularInline):
    model = ContestIcon
    extra = 0
    readonly_fields = ['icon_link']
    exclude = ['updated_at']

    def icon_link(self, instance):
        if instance.id is not None:
            href = reverse('oioioi.contestlogo.views.icon_image_view',
                    kwargs={'icon_id': str(instance.id),
                            'contest_id': str(instance.contest.id)})
            return make_html_link(href, instance.filename)
        return None
    icon_link.short_description = _("Filename")


class ContestIconAdminMixin(object):
    """Adds :class:`~oioioi.contestlogo.models.ContestIcon` to an admin panel.
    """

    def __init__(self, *args, **kwargs):
        super(ContestIconAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = self.inlines + [ContestIconInline]
ContestAdmin.mix_in(ContestIconAdminMixin)
