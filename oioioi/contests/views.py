from operator import itemgetter  # pylint: disable=E0611

import six

import django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy
from django.views.decorators.http import require_POST
from oioioi.base.main_page import register_main_page_view
from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.utils.redirect import safe_redirect
from oioioi.base.utils.user_selection import get_user_hints_view
from oioioi.contests.attachment_registration import attachment_registry
from oioioi.contests.controllers import submission_template_context
from oioioi.contests.forms import (
    GetUserInfoForm,
    SubmissionForm,
    FilesMessageForm,
    SubmissionsMessageForm,
    SubmitMessageForm,
    SubmissionMessageForm,
)
from oioioi.contests.models import (
    Contest,
    ContestAttachment,
    ProblemInstance,
    Submission,
    SubmissionReport,
    UserResultForProblem,
)
from oioioi.contests.processors import recent_contests
from oioioi.contests.utils import (
    can_admin_contest,
    can_enter_contest,
    can_see_personal_data,
    contest_exists,
    get_submission_or_error,
    has_any_submittable_problem,
    is_contest_archived,
    is_contest_admin,
    is_contest_basicadmin,
    is_contest_observer,
    visible_contests,
    visible_contests_queryset, 
    visible_problem_instances,
    visible_rounds,
    get_files_message,
    get_submissions_message,
    get_submit_message,
    get_number_of_rounds,
    get_contest_dates,
    get_problems_sumbmission_limit,
    get_results_visibility,
    are_rules_visible,
    get_scoring_desription,
    get_submission_message,
)
from oioioi.filetracker.utils import stream_file
from oioioi.problems.models import ProblemAttachment, ProblemStatement
from oioioi.problems.utils import (
    can_admin_problem_instance,
    copy_problem_instance,
    filter_my_all_visible_submissions,
    get_new_problem_instance,
    query_statement,
    query_zip,
    update_tests_from_main_pi,
)
from oioioi.status.registry import status_registry


@register_main_page_view(order=900)
def main_page_view(request):
    if not Contest.objects.exists():
        return TemplateResponse(request, 'contests/index-no-contests.html')
    return redirect('select_contest')


def select_contest_view(request):
    contests = visible_contests(request)
    contests = sorted(contests, key=lambda x: x.creation_date, reverse=True)
    context = {
        'contests': contests,
        'contests_on_page': getattr(settings, "CONTESTS_ON_PAGE", 20)
    }
    return TemplateResponse(
        request, 'contests/select_contest.html', context
    )


@enforce_condition(contest_exists & can_enter_contest)
def default_contest_view(request):
    url = request.contest.controller.default_view(request)
    return HttpResponseRedirect(url)


@status_registry.register
def get_contest_permissions(request, response):
    response['is_contest_admin'] = is_contest_admin(request)
    response['is_contest_basicadmin'] = is_contest_basicadmin(request)
    return response


@menu_registry.register_decorator(
    _("Rules"), lambda request: reverse('contest_rules'), order=90
)
@enforce_condition(contest_exists & can_enter_contest & are_rules_visible)
def contest_rules_view(request):
    no_of_rounds = get_number_of_rounds(request)
    scoring_description = get_scoring_desription(request)
    results_visibility = get_results_visibility(request)
    contest_dates = get_contest_dates(request)
    submission_limit = get_problems_sumbmission_limit(request)

    return TemplateResponse(
        request,
        'contests/contest_rules.html',
        {
            'no_of_rounds' : no_of_rounds,
            'contest_start_date' : contest_dates[0],
            'contest_end_date' : contest_dates[1],
            'submission_limit' : submission_limit,
            'results_visibility' : results_visibility,
            'scoring_type' : scoring_description,
        },
    )


@menu_registry.register_decorator(
    _("Problems"), lambda request: reverse('problems_list'), order=100
)
@enforce_condition(contest_exists & can_enter_contest)
def problems_list_view(request):
    controller = request.contest.controller
    problem_instances = visible_problem_instances(request)

    # Problem statements in order
    # 1) problem instance
    # 2) statement_visible
    # 3) round end time
    # 4) user result
    # 5) number of submissions left
    # 6) submissions_limit
    # 7) can_submit
    # Sorted by (start_date, end_date, round name, problem name)
    problems_statements = sorted(
        [
            (
                pi,
                controller.can_see_statement(request, pi),
                controller.get_round_times(request, pi.round),
                # Because this view can be accessed by an anynomous user we can't
                # use `user=request.user` (it would cause TypeError). Surprisingly
                # using request.user.id is ok since for AnynomousUser id is set
                # to None.
                next(
                    (
                        r
                        for r in UserResultForProblem.objects.filter(
                            user__id=request.user.id, problem_instance=pi
                        )
                        if r
                        and r.submission_report
                        and controller.can_see_submission_score(
                            request, r.submission_report.submission
                        )
                    ),
                    None,
                ),
                pi.controller.get_submissions_left(request, pi),
                pi.controller.get_submissions_limit(request, pi),
                controller.can_submit(request, pi) and not is_contest_archived(request),
            )
            for pi in problem_instances
        ],
        key=lambda p: (p[2].get_key_for_comparison(), p[0].round.name, p[0].short_name),
    )

    show_submissions_limit = any([p[5] for p in problems_statements])
    show_submit_button = any([p[6] for p in problems_statements])
    show_rounds = len(frozenset(pi.round_id for pi in problem_instances)) > 1
    table_columns = 3 + int(show_submissions_limit) + int(show_submit_button)

    return TemplateResponse(
        request,
        'contests/problems_list.html',
        {
            'problem_instances': problems_statements,
            'show_rounds': show_rounds,
            'show_scores': request.user.is_authenticated,
            'show_submissions_limit': show_submissions_limit,
            'show_submit_button': show_submit_button,
            'table_columns': table_columns,
            'problems_on_page': getattr(settings, 'PROBLEMS_ON_PAGE', 100),
        },
    )


@enforce_condition(contest_exists & can_enter_contest)
def problem_statement_view(request, problem_instance):
    controller = request.contest.controller
    pi = get_object_or_404(
        ProblemInstance, round__contest=request.contest, short_name=problem_instance
    )

    if not controller.can_see_problem(request, pi) or not controller.can_see_statement(
        request, pi
    ):
        raise PermissionDenied

    if not pi.problem.controller.supports_problem_statement():
        # if the problem doesn't support having a problem statement,
        # redirect to submission
        return redirect('submit', problem_instance_id=pi.id)

    statement = query_statement(pi.problem)

    if not statement:
        return TemplateResponse(
            request, 'contests/no_problem_statement.html', {'problem_instance': pi}
        )

    if statement.extension == '.zip':
        return redirect(
            'problem_statement_zip_index',
            contest_id=request.contest.id,
            problem_instance=problem_instance,
            statement_id=statement.id,
        )
    return stream_file(statement.content, statement.download_name)


@enforce_condition(contest_exists & can_enter_contest)
def problem_statement_zip_index_view(request, problem_instance, statement_id):

    response = problem_statement_zip_view(
        request, problem_instance, statement_id, 'index.html'
    )

    problem_statement = get_object_or_404(ProblemStatement, id=statement_id)

    return TemplateResponse(
        request,
        'contests/html_statement.html',
        {
            'content': mark_safe(six.ensure_str(response.content)),
            'problem_name': problem_statement.problem.name,
        },
    )


@enforce_condition(contest_exists & can_enter_contest)
def problem_statement_zip_view(request, problem_instance, statement_id, path):
    controller = request.contest.controller
    pi = get_object_or_404(
        ProblemInstance, round__contest=request.contest, short_name=problem_instance
    )
    statement = get_object_or_404(
        ProblemStatement, problem__probleminstance=pi, id=statement_id
    )

    if not controller.can_see_problem(request, pi) or not controller.can_see_statement(
        request, pi
    ):
        raise PermissionDenied

    return query_zip(statement, path)


@menu_registry.register_decorator(
    _("Submit"), lambda request: reverse('submit'), order=300
)
@enforce_condition(contest_exists & can_enter_contest & ~is_contest_archived)
@enforce_condition(
    has_any_submittable_problem, template='contests/nothing_to_submit.html'
)
def submit_view(request, problem_instance_id=None):
    if request.method == 'POST':
        form = SubmissionForm(request, request.POST, request.FILES)
        if form.is_valid():
            request.contest.controller.create_submission(
                request, form.cleaned_data['problem_instance'], form.cleaned_data
            )
            return redirect('my_submissions', contest_id=request.contest.id)
    else:
        initial = {}
        if problem_instance_id is not None:
            initial = {'problem_instance_id': int(problem_instance_id)}
        form = SubmissionForm(request, initial=initial)

    pis = form.get_problem_instances()
    submissions_left = {
        pi.id: pi.controller.get_submissions_left(request, pi) for pi in pis
    }
    return TemplateResponse(
        request,
        'contests/submit.html',
        {
            'form': form,
            'submissions_left': submissions_left,
            'message': get_submit_message(request),
        },
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def edit_submit_message_view(request):
    instance = get_submit_message(request)
    if request.method == 'POST':
        form = SubmitMessageForm(request, request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect('my_submissions')
    else:
        form = SubmitMessageForm(request, instance=instance)
    return TemplateResponse(
        request,
        'public_message/edit.html',
        {'form': form, 'title': _("Edit submit message")},
    )


@menu_registry.register_decorator(
    _("My submissions"), lambda request: reverse('my_submissions'), order=400
)
@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def my_submissions_view(request):
    queryset = (
        Submission.objects.filter(problem_instance__contest=request.contest)
        .order_by('-date')
        .select_related(
            'user',
            'problem_instance',
            'problem_instance__contest',
            'problem_instance__round',
            'problem_instance__problem',
        )
    )
    controller = request.contest.controller
    queryset = controller.filter_my_visible_submissions(request, queryset)
    header = controller.render_my_submissions_header(request, queryset.all())
    submissions = [submission_template_context(request, s) for s in queryset]
    show_scores = any(s['can_see_score'] for s in submissions)

    return TemplateResponse(
        request,
        'contests/my_submissions.html',
        {
            'header': header,
            'submissions': submissions,
            'show_scores': show_scores,
            'submissions_on_page': getattr(settings, 'SUBMISSIONS_ON_PAGE', 100),
            'is_contest_archived': is_contest_archived(request),
            'message': get_submissions_message(request),
            'is_admin': is_contest_basicadmin(request),
        },
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def edit_submissions_message_view(request):
    instance = get_submissions_message(request)
    if request.method == 'POST':
        form = SubmissionsMessageForm(request, request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect('my_submissions', contest_id=request.contest.id)
    else:
        form = SubmissionsMessageForm(request, instance=instance)
    return TemplateResponse(
        request,
        'public_message/edit.html',
        {'form': form, 'title': _("Edit submissions message")},
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def edit_submission_message_view(request):
    instance = get_submission_message(request)
    if request.method == 'POST':
        form = SubmissionMessageForm(request, request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect('my_submissions', contest_id=request.contest.id)
    else:
        form = SubmissionMessageForm(request, instance=instance)
    return TemplateResponse(
        request,
        'public_message/edit.html',
        {'form': form, 'title': _("Edit submission message")},
    )


@enforce_condition(not_anonymous)
def all_submissions_view(request):
    submissions = []

    if request.user.is_authenticated:
        queryset = Submission.objects.filter(user=request.user).select_related(
            'user',
            'problem_instance',
            'problem_instance__contest',
            'problem_instance__round',
            'problem_instance__problem',
        )

        submissions_list = filter_my_all_visible_submissions(
            request, queryset
        ).order_by('-date')
        for s in submissions_list:
            request.contest = s.problem_instance.contest
            submissions.append(submission_template_context(request, s))
        request.contest = None
        show_scores = any(s['can_see_score'] for s in submissions)

    return TemplateResponse(
        request,
        'contests/my_submissions_all.html',
        {
            'submissions': submissions,
            'show_scores': show_scores,
            'submissions_on_page': getattr(settings, 'SUBMISSIONS_ON_PAGE', 100),
        },
    )


@enforce_condition(~contest_exists | can_enter_contest)
def submission_view(request, submission_id):
    submission = get_submission_or_error(request, submission_id)
    pi = submission.problem_instance
    controller = pi.controller
    can_admin = can_admin_problem_instance(request, pi)

    header = controller.render_submission(request, submission)
    footer = controller.render_submission_footer(request, submission)
    reports = []
    queryset = SubmissionReport.objects.filter(submission=submission).prefetch_related(
        'scorereport_set'
    )
    for report in controller.filter_visible_reports(
        request, submission, queryset.filter(status='ACTIVE')
    ):
        reports.append(controller.render_report(request, report))

    if can_admin:
        all_reports = controller.filter_visible_reports(request, submission, queryset)
    else:
        all_reports = []

    return TemplateResponse(
        request,
        'contests/submission.html',
        {
            'submission': submission,
            'header': header,
            'footer': footer,
            'reports': reports,
            'all_reports': all_reports,
            'can_admin': can_admin,
        },
    )


def report_view(request, submission_id, report_id):
    submission = get_submission_or_error(request, submission_id)
    pi = submission.problem_instance
    if not can_admin_problem_instance(request, pi):
        raise PermissionDenied

    queryset = SubmissionReport.objects.filter(submission=submission)
    report = get_object_or_404(queryset, id=report_id)
    return HttpResponse(pi.controller.render_report(request, report))


@require_POST
def rejudge_submission_view(request, submission_id):
    submission = get_submission_or_error(request, submission_id)
    pi = submission.problem_instance
    if not can_admin_problem_instance(request, pi):
        raise PermissionDenied

    extra_args = {}
    supported_extra_args = pi.controller.get_supported_extra_args(submission)
    for flag in request.GET:
        if flag in supported_extra_args:
            extra_args[flag] = True
        else:
            raise SuspiciousOperation

    pi.controller.judge(submission, extra_args, is_rejudge=True)
    messages.info(request, _("Rejudge request received."))
    return redirect('submission', submission_id=submission_id)


@require_POST
def change_submission_kind_view(request, submission_id, kind):
    submission = get_submission_or_error(request, submission_id)
    pi = submission.problem_instance
    if not can_admin_problem_instance(request, pi):
        raise PermissionDenied

    controller = pi.controller
    if kind in controller.valid_kinds_for_submission(submission):
        controller.change_submission_kind(submission, kind)
        messages.success(request, _("Submission kind has been changed."))
    else:
        messages.error(
            request,
            _("%(kind)s is not valid kind for submission %(submission_id)d.")
            % {'kind': kind, 'submission_id': submission.id},
        )
    return redirect('submission', submission_id=submission_id)


@menu_registry.register_decorator(
    _("Downloads"), lambda request: reverse('contest_files'), order=200
)
@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def contest_files_view(request):
    is_admin = is_contest_basicadmin(request)
    additional_files = attachment_registry.to_list(request=request)

    contest_files = ContestAttachment.objects.filter(
        contest=request.contest,
    ).filter(
        Q(round__isnull=True) | Q(round__in=visible_rounds(request))
    ).select_related('round')
    contest_files_without_admin = contest_files.filter(
        Q(pub_date__isnull=True) | Q(pub_date__lte=request.timestamp),
    )
    if is_admin:
        contest_files_without_admin = contest_files_without_admin.filter(
            Q(round__isnull=True) | Q(round__in=visible_rounds(request, no_admin=True))
        )
    else:
        contest_files = contest_files_without_admin
    contest_files_without_admin = set(contest_files_without_admin)

    problem_ids = [pi.problem_id for pi in visible_problem_instances(request)]
    if is_admin:
        problem_ids_without_admin = {
            pi.problem_id for pi in visible_problem_instances(request, no_admin=True)
        }
    else:
        problem_ids_without_admin = set(problem_ids)
    problem_files = ProblemAttachment.objects.filter(
        problem_id__in=problem_ids
    ).select_related('problem')

    round_file_exists = contest_files.filter(round__isnull=False).exists()
    add_category_field = round_file_exists or problem_files.exists()
    rows = sorted([
        {
            'category': cf.round if cf.round else '',
            'name': cf.download_name,
            'description': cf.description,
            'link': reverse(
                'contest_attachment',
                kwargs={'contest_id': request.contest.id, 'attachment_id': cf.id},
            ),
            'pub_date': cf.pub_date,
            'admin_only': cf not in contest_files_without_admin,
        }
        for cf in contest_files
    ], key=itemgetter('name'))

    rows += sorted([
        {
            'category': pf.problem,
            'name': pf.download_name,
            'description': pf.description,
            'link': reverse(
                'problem_attachment',
                kwargs={'contest_id': request.contest.id, 'attachment_id': pf.id},
            ),
            'pub_date': None,
            'admin_only': pf.problem_id not in problem_ids_without_admin,
        }
        for pf in problem_files
    ], key=itemgetter('name'))
    rows += sorted(additional_files, key=itemgetter('name'))
    return TemplateResponse(
        request,
        'contests/files.html',
        {
            'files': rows,
            'files_on_page': getattr(settings, 'FILES_ON_PAGE', 100),
            'add_category_field': add_category_field,
            'show_pub_dates': True,
            'message': get_files_message(request),
        },
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def edit_files_message_view(request):
    instance = get_files_message(request)
    if request.method == 'POST':
        form = FilesMessageForm(request, request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect('contest_files', contest_id=request.contest.id)
    else:
        form = FilesMessageForm(request, instance=instance)
    return TemplateResponse(
        request,
        'public_message/edit.html',
        {'form': form, 'title': _("Edit files message")},
    )


@enforce_condition(contest_exists & can_enter_contest)
def contest_attachment_view(request, attachment_id):
    attachment = get_object_or_404(
        ContestAttachment, contest_id=request.contest.id, id=attachment_id
    )

    if (attachment.round and attachment.round not in visible_rounds(request)) or (
        not is_contest_basicadmin(request)
        and attachment.pub_date
        and attachment.pub_date > request.timestamp
    ):
        raise PermissionDenied

    return stream_file(attachment.content, attachment.download_name)


@enforce_condition(contest_exists & can_enter_contest)
def problem_attachment_view(request, attachment_id):
    attachment = get_object_or_404(ProblemAttachment, id=attachment_id)
    problem_instances = visible_problem_instances(request)
    problem_ids = [pi.problem_id for pi in problem_instances]
    if attachment.problem_id not in problem_ids:
        raise PermissionDenied
    return stream_file(attachment.content, attachment.download_name)


@enforce_condition(
    contest_exists
    & (is_contest_basicadmin | is_contest_observer | can_see_personal_data)
)
def contest_user_hints_view(request):
    rcontroller = request.contest.controller.registration_controller()
    queryset = rcontroller.filter_participants(User.objects.all())
    return get_user_hints_view(request, 'substr', queryset)


@enforce_condition(contest_exists & (is_contest_basicadmin | can_see_personal_data))
def user_info_view(request, user_id):
    controller = request.contest.controller
    rcontroller = controller.registration_controller()
    user = get_object_or_404(User, id=user_id)

    if not request.user.is_superuser and (
        user
        not in rcontroller.filter_users_with_accessible_personal_data(
            User.objects.all()
        )
        or user.is_superuser
    ):
        raise PermissionDenied

    infolist = sorted(
        controller.get_contest_participant_info_list(request, user)
        + rcontroller.get_contest_participant_info_list(request, user),
        reverse=True,
    )
    info = "".join(html for (_p, html) in infolist)
    return TemplateResponse(
        request,
        'contests/user_info.html',
        {
            'target_user_name': controller.get_user_public_name(request, user),
            'info': info,
        },
    )


@enforce_condition(contest_exists & (is_contest_basicadmin | can_see_personal_data))
@require_POST
def user_info_redirect_view(request):
    form = GetUserInfoForm(request, request.POST)
    if not form.is_valid():
        return TemplateResponse(
            request,
            'simple-centered-form.html',
            {
                'form': form,
                'action': reverse(
                    'user_info_redirect', kwargs={'contest_id': request.contest.id}
                ),
                'title': _("See user info page"),
            },
        )

    user = form.cleaned_data['user']

    return safe_redirect(
        request,
        reverse(
            'user_info', kwargs={'contest_id': request.contest.id, 'user_id': user.id}
        ),
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def rejudge_all_submissions_for_problem_view(request, problem_instance_id):
    problem_instance = get_object_or_404(ProblemInstance, id=problem_instance_id)
    count = problem_instance.submission_set.count()
    if request.POST:
        for submission in problem_instance.submission_set.all():
            problem_instance.controller.judge(
                submission, request.GET.dict(), is_rejudge=True
            )
        messages.info(
            request,
            ngettext_lazy(
                "%(count)d rejudge request received.",
                "%(count)d rejudge requests received.",
                count,
            )
            % {'count': count},
        )
        problem_instance.needs_rejudge = False
        problem_instance.save(update_fields=["needs_rejudge"])
        return safe_redirect(
            request, reverse('oioioiadmin:contests_probleminstance_changelist')
        )

    return TemplateResponse(request, 'contests/confirm_rejudge.html', {'count': count})


@enforce_condition(contest_exists & is_contest_basicadmin)
def rejudge_not_needed_view(request, problem_instance_id):
    problem_instance = get_object_or_404(ProblemInstance, id=problem_instance_id)

    if request.POST:
        problem_instance.needs_rejudge = False
        problem_instance.save(update_fields=["needs_rejudge"])
        messages.success(request, _("Needs rejudge flag turned off."))

        return safe_redirect(
            request,
            reverse('oioioiadmin:contests_probleminstance_changelist'),
        )

    return TemplateResponse(request, 'contests/confirm_rejudge_not_needed.html')


@enforce_condition(contest_exists & is_contest_basicadmin)
def reset_tests_limits_for_probleminstance_view(request, problem_instance_id):
    problem_instance = get_object_or_404(ProblemInstance, id=problem_instance_id)
    if request.POST:
        update_tests_from_main_pi(problem_instance)
        messages.success(request, _("Tests limits reset successfully"))
        return safe_redirect(
            request, reverse('oioioiadmin:contests_probleminstance_changelist')
        )

    return TemplateResponse(
        request,
        'contests/confirm_resetting_limits.html',
        {'probleminstance': problem_instance},
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def reattach_problem_contest_list_view(request, full_list=False):
    problem_ids = request.GET.get('ids')
    if problem_ids:
        problem_ids = [int(i) for i in problem_ids.split(',') if i.isdigit()]

    if not problem_ids:
        raise SuspiciousOperation("Invalid problem ids")

    problem_instances = ProblemInstance.objects.filter(id__in=problem_ids)

    if full_list:
        contests = Contest.objects.all()
    else:
        contests = recent_contests(request) or Contest.objects.all()

    contests = [c for c in contests if can_admin_contest(request.user, c)]
    return TemplateResponse(
        request,
        'contests/reattach_problem_contest_list.html',
        {
            'problem_instances': problem_instances,
            'contest_list': contests,
            'full_list': full_list,
            'problem_ids': '%2C'.join(str(i) for i in problem_ids), # Separate the problem ids with a comma (%2C)
        },
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def reattach_problem_confirm_view(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)
    if not can_admin_contest(request.user, contest):
        raise PermissionDenied
    
    problem_ids = request.GET.get('ids')
    if problem_ids:
        problem_ids = [int(i) for i in problem_ids.split(',')]

    if not problem_ids:
        raise SuspiciousOperation("Invalid problem ids")

    problem_instances = ProblemInstance.objects.filter(id__in=problem_ids)

    if request.method == 'POST':
        copied_instances = (
            [copy_problem_instance(problem_instance, contest) 
             for problem_instance in problem_instances]
            if request.POST.get('copy-limits', '') == 'on'
            else [get_new_problem_instance(problem_instance.problem, contest) 
                  for problem_instance in problem_instances]
        )
        messages.success(request, _(u"Problems {} added successfully.".format(', '.join(map(str, copied_instances)))))
        return safe_redirect(
            request,
            reverse(
                'oioioiadmin:contests_probleminstance_changelist',
                kwargs={'contest_id': contest.id},
            ),
        )
    return TemplateResponse(
        request,
        'contests/reattach_problem_confirm.html',
        {
            'problem_instances': problem_instances,
            'contest': contest
        },
    )


@enforce_condition(contest_exists & is_contest_basicadmin)
def confirm_archive_contest(request):
    if request.method == 'POST':
        contest = request.contest
        contest.is_archived = True
        contest.save()
        return redirect('default_contest_view', contest_id=contest.id)
    return TemplateResponse(request, 'contests/confirm_archive_contest.html')


@enforce_condition(contest_exists & is_contest_basicadmin)
def unarchive_contest(request):
    contest = request.contest
    contest.is_archived = False
    contest.save()
    return redirect('default_contest_view', contest_id=contest.id)

def filter_contests_view(request, filter_value=""):
    contests = visible_contests_queryset(request, filter_value)
    contests = sorted(contests, key=lambda x: x.creation_date, reverse=True)
    
    context = {
        'contests' : contests,
        'contests_on_page' : getattr(settings, 'CONTESTS_ON_PAGE', 20),
    }  
    return TemplateResponse(
        request, 'contests/select_contest.html', context
    )