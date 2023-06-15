from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.base.utils import make_html_link
from oioioi.contestlogo.models import ContestIcon, ContestLogo
from oioioi.contests.admin import ContestAdmin


class ContestLogoInline(admin.TabularInline):
    model = ContestLogo
    readonly_fields = ['logo_link']
    exclude = ['updated_at']
    category = _("Advanced")

    def logo_link(self, instance):
        if instance.id is not None:
            href = reverse(
                'logo_image_view', kwargs={'contest_id': str(instance.contest.id)}
            )
            return make_html_link(href, instance.filename)
        return None

    logo_link.short_description = _("Filename")


class ContestLogoAdminMixin(object):
    """Adds :class:`~oioioi.contestlogo.models.ContestLogo` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(ContestLogoAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (ContestLogoInline,)


ContestAdmin.mix_in(ContestLogoAdminMixin)


class ContestIconInline(admin.TabularInline):
    model = ContestIcon
    extra = 0
    readonly_fields = ['icon_link']
    exclude = ['updated_at']
    category = _("Advanced")

    def icon_link(self, instance):
        if instance.id is not None:
            href = reverse(
                'icon_image_view',
                kwargs={
                    'icon_id': str(instance.id),
                    'contest_id': str(instance.contest_id),
                },
            )
            return make_html_link(href, instance.filename)
        return None

    icon_link.short_description = _("Filename")


class ContestIconAdminMixin(object):
    """Adds :class:`~oioioi.contestlogo.models.ContestIcon` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(ContestIconAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (ContestIconInline,)


ContestAdmin.mix_in(ContestIconAdminMixin)
