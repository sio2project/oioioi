from django.contrib.auth.mixins import UserPassesTestMixin
from oauth2_provider.views import (
    ApplicationRegistration,
    ApplicationUpdate,
    ApplicationDelete,
    ApplicationList,
    ApplicationDetail,
)
from oauth2_provider.models import Application

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

class AdminApplicationList(AdminRequiredMixin, ApplicationList):
    def get_queryset(self):
        return Application.objects.all()

class AdminApplicationRegistration(AdminRequiredMixin, ApplicationRegistration):
    pass

class AdminApplicationUpdate(AdminRequiredMixin, ApplicationUpdate):
    pass

class AdminApplicationDelete(AdminRequiredMixin, ApplicationDelete):
    pass

class AdminApplicationDetail(AdminRequiredMixin, ApplicationDetail):
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        return obj