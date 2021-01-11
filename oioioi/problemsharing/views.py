from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView

from oioioi.base.menu import account_menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.utils.user_selection import get_user_hints_view
from oioioi.problemsharing.forms import AddFriendshipForm
from oioioi.problemsharing.models import Friendship
from oioioi.teachers.views import is_teacher

account_menu_registry.register(
    name='friends',
    text=_("Friends"),
    url_generator=lambda request: reverse('problemsharing_friends'),
    condition=is_teacher,
    order=170,
)


@method_decorator(enforce_condition(not_anonymous & is_teacher), name='dispatch')
class FriendshipsView(TemplateView):
    template_name = 'problemsharing/friendship.html'

    def get_context_data(self, **kwargs):
        ctx = super(FriendshipsView, self).get_context_data(**kwargs)
        ctx['form'] = AddFriendshipForm()
        ctx['friends'] = User.objects.filter(
            friendships_received__creator=self.request.user
        )
        return ctx

    def post(self, request):
        ctx = self.get_context_data()
        if 'befriend' in request.POST:
            # if we would always pass POST data to AddFriendshipForm,
            # an "field empty" error message would appear on "unfriending"
            ctx['form'] = AddFriendshipForm(self.request.POST)
            if ctx['form'].is_valid():
                receiver = ctx['form'].cleaned_data['user']

                if Friendship.objects.filter(
                    creator=request.user, receiver=receiver
                ).exists():
                    messages.warning(request, _("This user is already your friend"))
                    return render(request, self.template_name, ctx)
                if receiver == request.user:
                    messages.error(request, _("You can't befriend yourself"))
                    return render(request, self.template_name, ctx)

                friendship = Friendship(creator=request.user, receiver=receiver)
                friendship.save()
                ctx['form'] = AddFriendshipForm()  # Clean form input
                messages.info(request, _("Friend added"))
        elif 'unfriend' in request.POST:
            try:
                friendship = Friendship.objects.get(
                    creator=request.user, receiver_id=request.POST.get('id')
                )
                friendship.delete()
                ctx['friends'].exclude(id=request.POST.get('id'))
            except Friendship.DoesNotExist:
                messages.error(
                    request, _("Invalid request (this user is not your friend)")
                )
        else:
            raise SuspiciousOperation
        return render(request, self.template_name, ctx)


@enforce_condition(is_teacher)
def friend_hints_view(request):
    queryset = (
        User.objects.filter(teacher__isnull=False)
        .exclude(friendships_received__creator=request.user)
        .exclude(id=request.user.id)
    )
    return get_user_hints_view(request, 'substr', queryset)
