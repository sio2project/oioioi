import logging

import registration.backends.default.urls
import registration.views
from django.conf import settings
from django.conf.urls import url
from django.contrib.auth.models import User
from django.contrib.auth.views import password_reset
from django.contrib.sites.requests import RequestSite
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from registration import signals
from registration.backends.default.views import (
    RegistrationView as DefaultRegistrationView,
)
from registration.models import RegistrationProfile

from oioioi.base.forms import OioioiPasswordResetForm, RegistrationFormWithNames
from oioioi.base.models import PreferencesSaved
from oioioi.base.preferences import PreferencesFactory

auditLogger = logging.getLogger(__name__ + '.audit')


class RegistrationView(DefaultRegistrationView):
    def form_class(self, instance=None, *args, **kwargs):
        return PreferencesFactory().create_form(
            RegistrationFormWithNames, instance, *args, **kwargs
        )

    def register(self, form):
        data = form.cleaned_data
        request = self.request

        user = User.objects.create_user(
            data['username'], data['email'], data['password1']
        )
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.is_active = not settings.SEND_USER_ACTIVATION_EMAIL
        user.save()

        auditLogger.info(
            "User %d (%s) created account from IP %s UA: %s",
            user.id,
            user.username,
            request.META.get('REMOTE_ADDR', '?'),
            request.META.get('HTTP_USER_AGENT', '?'),
        )

        registration_profile = RegistrationProfile.objects.create_profile(user)
        signals.user_registered.send(sender=self.__class__, user=user, request=request)
        PreferencesSaved.send(form, user=user)
        if settings.SEND_USER_ACTIVATION_EMAIL:
            registration_profile.send_activation_email(RequestSite(request))
        else:
            signals.user_activated.send(
                sender=self.__class__, user=user, request=request
            )
        return user


urlpatterns = [
    url(r'^register/$', RegistrationView.as_view(), name='registration_register'),
]

if not settings.SEND_USER_ACTIVATION_EMAIL:
    urlpatterns += [
        url(
            r'^register/complete/$',
            TemplateView.as_view(
                template_name='registration/'
                'registration_and_activation_complete.html'
            ),
            name='registration_complete',
        )
    ]

urlpatterns += [
    url(
        r'^password/reset/$',
        password_reset,
        {
            'password_reset_form': OioioiPasswordResetForm,
            'post_reset_redirect': reverse_lazy('auth_password_reset_done'),
        },
        name="auth_password_reset",
    )
]

urlpatterns += registration.backends.default.urls.urlpatterns
