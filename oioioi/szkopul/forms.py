from django import forms

from oioioi.szkopul.models import MAPCourseRegistration


class MAPCourseRegistrationForm(forms.ModelForm):
    class Meta:
        model = MAPCourseRegistration
        exclude = ["participant"]

    def __init__(self, *args, **kwargs):
        super(MAPCourseRegistrationForm, self).__init__(*args, **kwargs)
        self.fields["not_primaryschool"].label = "Uczęszczam do szkoły średniej"

    def clean(self):
        super(MAPCourseRegistrationForm, self).clean()
