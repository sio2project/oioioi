import datetime

from oioioi.oi.forms import OIRegistrationForm
from oioioi.szkopul.models import MAPCourseRegistration


class MAPCourseRegistrationForm(OIRegistrationForm):
    class Meta(object):
        model = MAPCourseRegistration
        exclude = ['participant']

    def __init__(self, *args, **kwargs):
        super(MAPCourseRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['parent_consent'].required = False

    def _is_underage(self):
        birthday = self.cleaned_data.get('birthday')
        print(birthday)
        if not birthday:
            return True

        if birthday.month == 2 and birthday.day == 29:
            # born on leap year, there is no 29th Feb on 18th birthday,
            # so use 1st March as the threshold
            birthday = birthday + datetime.timedelta(1)

        return datetime.datetime.now() < datetime.datetime(
            birthday.year + 18, birthday.month, birthday.day, 0, 0, 0, 0
        )

    def clean(self):
        cleaned_data = super(MAPCourseRegistrationForm, self).clean()
        parent_consent = cleaned_data['parent_consent']
        if self._is_underage():
            if parent_consent is None:
                self.add_error(
                    "parent_consent",
                    "Zgoda rodzica jest wymagana aby móc uczestniczyć w konkursie.",
                )
