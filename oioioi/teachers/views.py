from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.core.mail import EmailMessage
from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_POST

from oioioi.base.menu import account_menu_registry
from oioioi.base.utils.confirmation import confirmation_view
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import Contest
from oioioi.participants.models import Participant
from oioioi.teachers.models import RegistrationConfig, ContestTeacher, Teacher
from oioioi.teachers.controllers import TeacherContestController
from oioioi.teachers.forms import AddTeacherForm
from oioioi.base.permissions import enforce_condition, not_anonymous, \
    is_superuser, make_request_condition
from oioioi.contests.utils import is_contest_admin, contest_exists

@make_request_condition
def is_teachers_contest(request):
    return isinstance(request.contest.controller, TeacherContestController)

@make_request_condition
def is_not_teacher(request):
    return not_anonymous(request) and \
           not request.user.has_perm('teachers.teacher')


def send_request_email(request, teacher, message):
    context = {
        'teacher': teacher,
        'accept_link': request.build_absolute_uri(reverse(accept_teacher_view,
            kwargs={'user_id': teacher.user_id})),
        'message': message.strip(),
    }
    subject = render_to_string('teachers/request_email_subject.txt', context)
    subject = ' '.join(subject.strip().splitlines())
    body = render_to_string('teachers/request_email.txt', context)
    message = EmailMessage(subject, body, settings.SERVER_EMAIL,
            [m[1] for m in settings.MANAGERS],
            headers={'Reply-To': teacher.user.email})
    message.send()

def send_acceptance_email(request, teacher):
    context = {
        'teacher': teacher,
        'new_contest_link': request.build_absolute_uri(
            reverse('oioioiadmin:contests_contest_add')),
    }
    subject = render_to_string('teachers/acceptance_email_subject.txt',
            context)
    subject = ' '.join(subject.strip().splitlines())
    body = render_to_string('teachers/acceptance_email.txt', context)
    teacher.user.email_user(subject, body)

@account_menu_registry.register_decorator(_("Request teacher account"),
    lambda request: reverse(add_teacher_view),
    order=100)
@enforce_condition(not_anonymous & is_not_teacher)
def add_teacher_view(request):
    try:
        instance = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        instance = None
    if request.method == 'POST':
        form = AddTeacherForm(request.POST, instance=instance)
        if form.is_valid():
            new_instance = form.save(commit=False)
            if not instance:
                new_instance.user = request.user
            new_instance.save()
            send_request_email(request, new_instance,
                    form.cleaned_data['message'])
            return TemplateResponse(request, 'teachers/request_sent.html')
    else:
        form = AddTeacherForm(instance=instance)
    return TemplateResponse(request, 'teachers/request.html', {'form': form})

@enforce_condition(is_superuser)
def accept_teacher_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    teacher, created = Teacher.objects.get_or_create(user=user)
    if teacher.is_active:
        messages.info(request, _("User already accepted."))
    else:
        choice = confirmation_view(request, 'teachers/confirm_add_teacher.html',
                {'teacher': teacher})
        if not isinstance(choice, bool):
            return choice
        if choice:
            teacher.is_active = True
            teacher.save()
            send_acceptance_email(request, teacher)
            messages.success(request, _("Successfully accepted and emailed the "
                "new teacher."))
    return redirect('oioioiadmin:teachers_teacher_changelist')

@contest_admin_menu_registry.register_decorator(_("Pupils"), lambda request:
        reverse(pupils_view, kwargs={'contest_id': request.contest.id}),
    order=30)
@enforce_condition(contest_exists & is_teachers_contest & is_contest_admin)
def pupils_view(request, contest_id):
    teachers = User.objects \
            .filter(teacher__contestteacher__contest=request.contest)
    pupils = User.objects.filter(participant__contest=request.contest)
    registration_config, created = RegistrationConfig.objects.get_or_create(
            contest=request.contest)
    registration_link = request.build_absolute_uri(
            reverse(activate_pupil_view, kwargs=
                {'contest_id': contest_id, 'key': registration_config.key}))
    other_contests = Contest.objects \
            .filter(contestteacher__teacher__user=request.user) \
            .exclude(id=request.contest.id)
    return TemplateResponse(request, 'teachers/pupils.html', {
                'teachers': teachers,
                'pupils': pupils,
                'registration_config': registration_config,
                'registration_link': registration_link,
                'other_contests': other_contests,
            })

@enforce_condition(not_anonymous & is_teachers_contest)
def activate_pupil_view(request, contest_id, key):
    registration_config = get_object_or_404(RegistrationConfig,
            contest=request.contest)
    key_ok = registration_config.key == key
    if key_ok and registration_config.is_active:
        is_teacher = request.user.has_perm('teachers.teacher')
        if not request.method == 'POST' or 'register_as' not in request.POST:
            return TemplateResponse(request, 'teachers/confirm_join.html',
                {'key': key, 'is_teacher': is_teacher})
        else:
            register_as = request.POST['register_as']
            if register_as == 'pupil':
                Participant.objects.get_or_create(contest=request.contest,
                        user=request.user)
            elif is_teacher and register_as == 'teacher':
                teacher_obj = get_object_or_404(Teacher, user=request.user)
                ContestTeacher.objects.get_or_create(contest=request.contest,
                        teacher=teacher_obj)
            else:
                raise SuspiciousOperation
            messages.info(request, _("Activation successful."))
            return redirect('default_contest_view', contest_id=contest_id)
    return TemplateResponse(request, 'teachers/activation_error.html', {
                'key_ok': key_ok,
                'registration_active': registration_config.is_active,
            })

def redirect_to_pupils(request):
    return redirect(reverse(pupils_view, kwargs={'contest_id':
        request.contest.id}))

@require_POST
@enforce_condition(contest_exists & is_teachers_contest & is_contest_admin)
def set_registration_view(request, contest_id, value):
    registration_config = get_object_or_404(RegistrationConfig,
            contest=request.contest)
    registration_config.is_active = value
    registration_config.save()
    return redirect_to_pupils(request)

@require_POST
@enforce_condition(contest_exists & is_teachers_contest & is_contest_admin)
def regenerate_key_view(request, contest_id):
    registration_config = get_object_or_404(RegistrationConfig,
            contest=request.contest)
    registration_config.generate_key()
    registration_config.save()
    return redirect_to_pupils(request)

@require_POST
@enforce_condition(contest_exists & is_teachers_contest & is_contest_admin)
def delete_pupils_view(request, contest_id):
    ContestTeacher.objects.filter(contest=request.contest,
            teacher__user_id__in=request.POST.getlist('teacher')).delete()
    Participant.objects.filter(contest=request.contest,
            user_id__in=request.POST.getlist('pupil')).delete()
    return redirect_to_pupils(request)

@require_POST
@enforce_condition(contest_exists & is_teachers_contest & is_contest_admin)
def bulk_add_pupils_view(request, contest_id, other_contest_id):
    other_contest = get_object_or_404(Contest, id=other_contest_id)
    if not request.user.has_perm('contests.contest_admin', other_contest):
        raise PermissionDenied
    for p in Participant.objects.filter(contest=other_contest):
        Participant.objects.get_or_create(contest=request.contest,
                user=p.user)
    for ct in ContestTeacher.objects.filter(contest=other_contest):
        ContestTeacher.objects.get_or_create(contest=request.contest,
                teacher=ct.teacher)
    return redirect_to_pupils(request)
