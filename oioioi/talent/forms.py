from oioioi.participants.forms import OpenRegistrationForm
from oioioi.talent.models import TalentRegistration

class TalentRegistrationForm(OpenRegistrationForm):
    class Meta(object):
        model = TalentRegistration
        exclude = ['participant']
