from django import forms
from django.contrib.auth.models import User

from oioioi.base.utils.user_selection import UserSelectionField
from oioioi.contests.current_contest import reverse


class AddFriendshipForm(forms.Form):
    user = UserSelectionField(queryset=User.objects.filter(teacher__isnull=False))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].hints_url = reverse("problemsharing_friend_hints")
