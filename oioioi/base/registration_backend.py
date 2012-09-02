from django.conf.urls import patterns, url
from django.contrib.sites.models import RequestSite
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django import forms

from registration import signals
from registration.forms import RegistrationForm
from registration.models import RegistrationProfile
from registration.backends.default import DefaultBackend
import registration.backends.default.urls
import registration.views

class RegistrationFormWithNames(RegistrationForm):
    def __init__(self, *args, **kwargs):
        super(RegistrationFormWithNames, self).__init__(*args, **kwargs)
        self.fields.insert(1, 'first_name',
                forms.CharField(label=_("First name")))
        self.fields.insert(2, 'last_name',
                forms.CharField(label=_("Last name")))

class Backend(DefaultBackend):
    def register(self, request, username, password1, email, first_name,
            last_name, **kwargs):
        user = User.objects.create_user(username, email, password1)
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = False
        user.save()

        registration_profile = RegistrationProfile.objects.create_profile(user)
        registration_profile.send_activation_email(RequestSite(request))

        signals.user_registered.send(sender=self.__class__, user=user,
                request=request)
        return user

    def get_form_class(self, request):
        return RegistrationFormWithNames

urlpatterns = patterns(
    url(r'^activate/(?P<activation_key>\w+)/$',
        registration.views.activate,
        {'backend': 'oioioi.base.registration_backend.Backend'},
        name='registration_activate'),
    url(r'^register/$',
        registration.views.register,
        {'backend': 'oioioi.base.registration_backend.Backend'},
        name='registration_register'),
)
urlpatterns += registration.backends.default.urls.urlpatterns
