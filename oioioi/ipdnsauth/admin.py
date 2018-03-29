from oioioi.base import admin
from oioioi.ipdnsauth.models import DnsToUser, IpToUser


class IpToUserAdmin(admin.ModelAdmin):
    list_display = ('ip_addr', 'user')

admin.site.register(IpToUser, IpToUserAdmin)


class DnsToUserAdmin(admin.ModelAdmin):
    list_display = ('dns_name', 'user')

admin.site.register(DnsToUser, DnsToUserAdmin)
