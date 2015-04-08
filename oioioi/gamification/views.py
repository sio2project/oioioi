from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.menu import account_menu_registry
from oioioi.gamification.experience import Experience
from oioioi.gamification.profile import profile_registry


@account_menu_registry.register_decorator(_("Profile"),
    lambda request: reverse('view_current_profile'), order=50)
@login_required
def profile_view(request, username=None):
    shown_user = None

    if username is None:
        shown_user = request.user
    else:
        shown_user = get_object_or_404(User.objects, username=username)

    exp = Experience(shown_user)
    sections = [func(request, shown_user) for func in profile_registry.items]

    return TemplateResponse(request, 'gamification/profile.html', {
        'shown_user': shown_user,
        'exp': exp,
        'sections': sections,
        'exp_percentage': int(100 * exp.current_experience /
                              exp.required_experience_to_lvlup)
    })
