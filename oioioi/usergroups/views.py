from django.views.generic import ListView, FormView, UpdateView, DeleteView
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied, MultipleObjectsReturned
from django.shortcuts import get_object_or_404, redirect

from oioioi.base.permissions import not_anonymous, enforce_condition
from oioioi.base.utils import generate_key
from oioioi.base.utils.confirmation import confirmation_view
from oioioi.contests.utils import is_contest_admin, contest_exists
from oioioi.teachers.views import is_teacher
from oioioi.usergroups.models import UserGroup
from oioioi.usergroups.forms import AddUserGroupForm, UserGroupChangeNameForm
from oioioi.usergroups.utils import is_usergroup_owner, is_usergroup_attached, \
    add_usergroup_to_members, move_members_to_usergroup, filter_usergroup_exclusive_members


@method_decorator(enforce_condition(not_anonymous & is_teacher), name='dispatch')
class GroupsListView(ListView):
    model = UserGroup
    template_name = 'usergroups/teacher_usergroups_list.html'

    def get_queryset(self):
        queryset = UserGroup.objects.filter(owners__in=[self.request.user])

        return queryset


@method_decorator(enforce_condition(not_anonymous & is_teacher), name='dispatch')
class GroupsAddView(FormView):
    form_class = AddUserGroupForm
    template_name = 'usergroups/teacher_add_usergroup.html'
    from_contest = False

    def __init__(self, *args, **kwargs):
        super(GroupsAddView, self).__init__(*args, **kwargs)
        self.from_contest = False

    def get_success_url(self):
        if self.from_contest:
            return reverse('show_members', kwargs={'member_type': 'pupil',
                                                   'contest_id': self.request.contest.id})
        return reverse('teacher_usergroups_list')

    def form_valid(self, form):
        self.from_contest = bool(self.request.GET.get('create_from_contest', False))

        if self.from_contest and not is_contest_admin(self.request):
            raise PermissionDenied

        group = form.instance
        group.save()

        group.owners.add(self.request.user)

        if self.from_contest:
            move_members_to_usergroup(self.request.contest, group)
            group.contests.add(self.request.contest)
            messages.success(self.request,
                             _('New user group from contest members created successfully!'))
        else:
            messages.success(self.request, _('New user group created successfully!'))

        return super(GroupsAddView, self).form_valid(form)


@method_decorator(enforce_condition(not_anonymous & is_teacher), name='dispatch')
class GroupsDetailView(UpdateView):
    form_class = UserGroupChangeNameForm
    model = UserGroup
    template_name = 'usergroups/teacher_usergroup_detail.html'

    def get_context_data(self, **kwargs):
        context = super(GroupsDetailView, self).get_context_data(**kwargs)

        context['addition_link'] = self.request.build_absolute_uri(
            reverse('usergroups_user_join', kwargs={
                'key': self.object.addition_config.key,
                'contest_id': None
            }))

        context['sharing_link'] = self.request.build_absolute_uri(
            reverse('usergroups_become_owner', kwargs={
                'key': self.object.sharing_config.key,
                'contest_id': None
            }))

        return context

    def get_success_url(self):
        return reverse('teacher_usergroup_detail', kwargs={
            'usergroup_id': self.kwargs['usergroup_id']
        })

    def get_object(self, queryset=None):
        return get_object_or_404(UserGroup.objects.select_related('addition_config').
                                 select_related('sharing_config').
                                 prefetch_related('members').
                                 prefetch_related('owners'), id=self.kwargs['usergroup_id'])

    def dispatch(self, request, *args, **kwargs):
        if not is_usergroup_owner(self.request.user, self.kwargs['usergroup_id']):
            raise PermissionDenied

        return super(GroupsDetailView, self).dispatch(request, *args, **kwargs)


@method_decorator(enforce_condition(not_anonymous & is_teacher), name='dispatch')
class GroupsDeleteView(DeleteView):
    template_name = 'admin/delete_confirmation.html'

    def get_success_url(self):
        return reverse('teacher_usergroups_list')

    def get_object(self, queryset=None):
        return get_object_or_404(UserGroup, id=self.kwargs['usergroup_id'])

    def get_context_data(self, **kwargs):
        context = super(GroupsDeleteView, self).get_context_data(**kwargs)
        context['object_name'] = _('User group')

        return context

    def post(self, request, *args, **kwargs):
        group_name = self.get_object().name

        response = super(GroupsDeleteView, self).post(request, *args, **kwargs)

        messages.success(request,
                         _("Successfully deleted group %s!") % group_name)
        return response

    def dispatch(self, request, *args, **kwargs):
        if not is_usergroup_owner(self.request.user, self.kwargs['usergroup_id']):
            raise PermissionDenied

        return super(GroupsDeleteView, self).dispatch(request, *args, **kwargs)

@require_POST
@enforce_condition(not_anonymous & is_teacher)
def set_addition_view(request, usergroup_id, value):
    if not is_usergroup_owner(request.user, usergroup_id):
        raise PermissionDenied

    group = get_object_or_404(UserGroup.objects.select_related('addition_config'),
                                 id=usergroup_id)

    group.addition_config.enabled = value
    group.addition_config.save()

    return redirect('teacher_usergroup_detail', usergroup_id=usergroup_id)

@require_POST
@enforce_condition(not_anonymous & is_teacher)
def regenerate_addition_key_view(request, usergroup_id):
    if not is_usergroup_owner(request.user, usergroup_id):
        raise PermissionDenied

    group = get_object_or_404(UserGroup.objects.select_related('addition_config'),
                              id=usergroup_id)

    group.addition_config.key = generate_key()
    group.addition_config.save()

    return redirect('teacher_usergroup_detail', usergroup_id=usergroup_id)

@enforce_condition(not_anonymous)
def join_usergroup_view(request, key):
    try:
        group = get_object_or_404(UserGroup.objects.select_related('addition_config'),
                                  addition_config__key=key)
    except MultipleObjectsReturned:
        messages.error(request, _('Provided key is not unique!'
                                  ' Ask your teacher to regenerate it.'))
        return redirect('index')

    if UserGroup.objects.filter(id=group.id).filter(members__in=[request.user]).exists():
        messages.info(request, _('You are already member of this group.'))
    else:
        if group.addition_config.enabled:
            confirmation = confirmation_view(request, 'usergroups/confirm_addition.html', {
                'group_name': group.name
            })

            if not isinstance(confirmation, bool):
                return confirmation

            if confirmation:
                group.members.add(request.user)
                messages.success(request, _('You have been successfully'
                                            ' added to group %s!') % group.name)
        else:
            messages.error(request, _('You cannot join this group.'
                                      ' This option is currently disabled.'))

    return redirect('index')

@require_POST
@enforce_condition(not_anonymous & is_teacher)
def delete_members_view(request, usergroup_id):
    if not is_usergroup_owner(request.user, usergroup_id):
        raise PermissionDenied

    group = get_object_or_404(UserGroup, id=usergroup_id)

    selected_members = User.objects.filter(id__in=request.POST.getlist('member'))
    group.members.remove(*list(selected_members))

    messages.success(request, _("Deletion of selected members successful!"))

    return redirect('teacher_usergroup_detail', usergroup_id=usergroup_id)

@enforce_condition(not_anonymous & is_teacher)
def become_owner_view(request, key):
    try:
        group = get_object_or_404(UserGroup.objects.select_related('sharing_config'),
                                  sharing_config__key=key)
    except MultipleObjectsReturned:
        messages.error(request, _('Provided key is not unique!'
                                  ' Ask group\'s owner to regenerate it.'))
        return redirect('teacher_usergroups_list')

    if UserGroup.objects.filter(id=group.id).filter(owners__in=[request.user]).exists():
        messages.info(request, _('You are already owner of this group.'))
    else:
        if group.sharing_config.enabled:
            group.owners.add(request.user)
            messages.success(request, _('You became owner of group %s.') % group.name)
        else:
            messages.error(request, _('You cannot become owner of this group.'
                                      ' This option is currently disabled.'))

    return redirect('teacher_usergroups_list')

@require_POST
@enforce_condition(not_anonymous & is_teacher)
def set_sharing_view(request, usergroup_id, value):
    if not is_usergroup_owner(request.user, usergroup_id):
        raise PermissionDenied

    group = get_object_or_404(UserGroup.objects.select_related('sharing_config'),
                                 id=usergroup_id)

    group.sharing_config.enabled = value
    group.sharing_config.save()

    return redirect('teacher_usergroup_detail', usergroup_id=usergroup_id)

@require_POST
@enforce_condition(not_anonymous & is_teacher)
def regenerate_sharing_key_view(request, usergroup_id):
    if not is_usergroup_owner(request.user, usergroup_id):
        raise PermissionDenied

    group = get_object_or_404(UserGroup.objects.select_related('sharing_config'),
                              id=usergroup_id)

    group.sharing_config.key = generate_key()
    group.sharing_config.save()

    return redirect('teacher_usergroup_detail', usergroup_id=usergroup_id)

@require_POST
@enforce_condition(not_anonymous & is_teacher)
def delete_owners_view(request, usergroup_id):
    if not is_usergroup_owner(request.user, usergroup_id):
        raise PermissionDenied

    group = get_object_or_404(UserGroup, id=usergroup_id)
    selected_owners = User.objects.filter(id__in=request.POST.getlist('owner'))

    if selected_owners.filter(id=request.user.id).exists():
        messages.error(request, _("You cannot renounce ownership. "
                                  "Consider deleting group instead."))
    else:
        group.owners.remove(*list(selected_owners))
        messages.success(request, _("Deletion of selected owners successful!"))

    return redirect('teacher_usergroup_detail', usergroup_id=usergroup_id)


@require_POST
@enforce_condition(not_anonymous & is_teacher & contest_exists & is_contest_admin)
def attach_to_contest_view(request):
    usergroup_id = request.POST.get('usergroup_id')
    if not is_usergroup_owner(request.user, usergroup_id):
        raise PermissionDenied
    usergroup = UserGroup.objects.get(id=usergroup_id)
    if is_usergroup_attached(request.contest, usergroup):
        messages.info(request, _("The group is already attached to the contest."))
    else:
        usergroup.contests.add(request.contest)
        messages.info(request, _("The group was successfully attached to the contest!"))

    return redirect('show_members', contest_id=request.contest.id,
                    member_type='pupil')


@enforce_condition(not_anonymous & is_teacher & contest_exists & is_contest_admin)
def detach_from_contest_view(request, usergroup_id):
    convert_to_members = request.POST.get('convert_to_members', False)
    usergroup = UserGroup.objects.get(id=usergroup_id)

    if not is_usergroup_attached(request.contest, usergroup):
        return redirect('show_members', contest_id=request.contest.id,
                        member_type='pupil')

    removed_users = filter_usergroup_exclusive_members(request.contest, usergroup)

    confirmation = confirmation_view(request,
                                     'usergroups/confirm_detaching.html', {
                                         'contest_id': request.contest.id,
                                         'group_name': usergroup.name,
                                         'removed_users': removed_users,
                                     })

    if not isinstance(confirmation, bool):
        return confirmation

    if confirmation:
        if convert_to_members:
            add_usergroup_to_members(request.contest, usergroup)
        usergroup.contests.remove(request.contest)

        messages.info(request, _("The group was successfully detached from the contest!"))

    return redirect('show_members', contest_id=request.contest.id,
                    member_type='pupil')
