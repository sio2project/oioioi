from oioioi.base import admin
from oioioi.problemsharing.models import Friendship


class FriendshipAdmin(admin.ModelAdmin):
    list_display = ['creator', 'receiver']

admin.site.register(Friendship, FriendshipAdmin)
