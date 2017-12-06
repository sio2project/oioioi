from django.conf.urls import url
from django.conf import settings
from django.contrib.auth.views import password_reset
from django.contrib.sites.requests import RequestSite
from django.core.urlresolvers import reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth.models import User
from registration import signals
from registration.models import RegistrationProfile
from registration.backends.default.views import \
    RegistrationView as DefaultRegistrationView
from oioioi.base.forms import RegistrationFormWithNames, \
    OioioiPasswordResetForm
import registration.backends.default.urls
import registration.views


class RegistrationView(DefaultRegistrationView):
    form_class = RegistrationFormWithNames

    def register(self, form):
        data = form.cleaned_data
        request = self.request

        user = User.objects.create_user(data['username'],
                                        data['email'], data['password1'])
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.is_active = not settings.SEND_USER_ACTIVATION_EMAIL
        user.save()

        registration_profile = RegistrationProfile.objects.create_profile(user)
        signals.user_registered.send(sender=self.__class__, user=user,
                                     request=request)
        if settings.SEND_USER_ACTIVATION_EMAIL:
            registration_profile.send_activation_email(RequestSite(request))
        else:
            signals.user_activated.send(sender=self.__class__, user=user,
                                        request=request)
        return user

urlpatterns = [
    url(r'^register/$',
        RegistrationView.as_view(), name='registration_register'),
]

if not settings.SEND_USER_ACTIVATION_EMAIL:
    urlpatterns += [url(
        r'^register/complete/$',
        TemplateView.as_view(
            template_name='registration/'
                'registration_and_activation_complete.html'
        ),
        name='registration_complete'
    )]

urlpatterns += [
    url(r'^password/reset/$',
        password_reset,
        {
            'password_reset_form': OioioiPasswordResetForm,
            'post_reset_redirect': reverse_lazy('auth_password_reset_done'),
        },
        name="auth_password_reset")
]

urlpatterns += registration.backends.default.urls.urlpatterns
