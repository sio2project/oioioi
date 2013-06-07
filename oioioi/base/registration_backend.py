from django.conf.urls import patterns, url
from django.contrib.sites.models import RequestSite
from django.contrib.auth.models import User
from registration import signals
from registration.models import RegistrationProfile
from registration.backends.default.views import \
    RegistrationView as DefaultRegistrationView
from oioioi.base.forms import RegistrationFormWithNames
import registration.backends.default.urls
import registration.views


class RegistrationView(DefaultRegistrationView):
    form_class = RegistrationFormWithNames

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

urlpatterns = patterns('',
    url(r'^register/$',
        RegistrationView.as_view(),
        name='registration_register'),
)
urlpatterns += registration.backends.default.urls.urlpatterns
