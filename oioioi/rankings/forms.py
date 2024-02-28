from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.forms import PublicMessageForm
from oioioi.base.utils.user_selection import UserSelectionField
from oioioi.rankings.models import RankingMessage


class FilterUsersInRankingForm(forms.Form):
    user = UserSelectionField(label=_("Username"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(FilterUsersInRankingForm, self).__init__(*args, **kwargs)
        self.fields['user'].hints_url = reverse(
            'get_users_in_ranking', kwargs={'contest_id': request.contest.id}
        )
        self.fields['user'].widget.attrs['placeholder'] = _("Search for user...")


class RankingMessageForm(PublicMessageForm):
    class Meta(object):
        model = RankingMessage
        fields = ['content']
