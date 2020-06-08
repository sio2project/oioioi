import itertools
from operator import attrgetter  # pylint: disable=E0611

import six
from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.permissions import enforce_condition
from oioioi.base.utils.pdf import generate_pdf
from oioioi.base.utils.user_selection import get_user_hints_view
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import Round, Submission, UserResultForProblem
from oioioi.contests.utils import contest_exists, has_any_rounds, is_contest_admin
from oioioi.filetracker.utils import stream_file
from oioioi.oireports.forms import CONTEST_REPORT_KEY, OIReportForm
from oioioi.participants.models import Region
from oioioi.programs.models import CompilationReport, GroupReport, TestReport

# FIXME conditions for views expressing oi dependence?


def _users_in_contest(request, region=None):
    queryset = User.objects.filter(
        participant__contest=request.contest, participant__status='ACTIVE'
    )
    if region is not None:
        queryset = queryset.filter(
            participant__participants_onsiteregistration__region_id=region
        )
    return queryset


@contest_admin_menu_registry.register_decorator(
    _("Printing reports"),
    lambda request: reverse('oireports', kwargs={'contest_id': request.contest.id}),
    order=440,
)
@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(has_any_rounds, 'oireports/no-reports.html')
def oireports_view(request):
    if request.method == 'POST':
        form = OIReportForm(request, request.POST)

        if form.is_valid():
            form_type = form.cleaned_data['form_type']

            if form_type == 'pdf_report':
                return generate_pdfreport(request, form)
            elif form_type == 'xml_report':
                return generate_xmlreport(request, form)
            else:
                raise SuspiciousOperation
    else:
        form = OIReportForm(request)
    return TemplateResponse(
        request,
        'oireports/report-options.html',
        {'form': form, 'CONTEST_REPORT_KEY': CONTEST_REPORT_KEY},
    )


def _render_report(
    request, template_name, title, users, problem_instances, test_groups
):
    rows = _serialize_reports(users, problem_instances, test_groups)
    return render_to_string(
        template_name,
        request=request,
        context={
            'rows': rows,
            'title': title,
        },
    )


def _serialize_report(user, problem_instances, test_groups):
    """Generates a dictionary representing a single report.


    :param request: Django request
    :type user: :cls:`django.contrib.auth.User`
    :param user: user to generate the report for
    :type problem_instances: list of
                              :cls:`oioioi.contests.ProblemInstance`
    :param problem_instances: problem instances to include in the report
    :type test_groups: dict(:cls:`oioioi.contests.ProblemInstance`
                        -> list of str)
    :param test_groups: dictionary mapping problem instances into lists
                        of names of test groups to include
    """

    resultsets = []
    total_score = None

    results = UserResultForProblem.objects.filter(
        user=user,
        problem_instance__in=list(problem_instances),
        submission_report__isnull=False,
    )
    for r in results:
        problem_instance = r.problem_instance
        submission_report = r.submission_report
        submission = submission_report.submission
        source_file = submission.programsubmission.source_file
        groups = list(test_groups[problem_instance])

        try:
            compilation_report = CompilationReport.objects.get(
                submission_report=submission_report
            )
        except CompilationReport.DoesNotExist:
            compilation_report = None

        try:
            test_reports = (
                TestReport.objects.filter(submission_report__submission=submission)
                .filter(submission_report__status='ACTIVE')
                .filter(submission_report__kind__in=['INITIAL', 'NORMAL'])
                .filter(test_group__in=groups)
                .order_by('test__kind', 'test__order', 'test_name')
            )
        except TestReport.DoesNotExist:
            test_reports = []

        group_reports = (
            GroupReport.objects.filter(submission_report__submission=submission)
            .filter(submission_report__status='ACTIVE')
            .filter(submission_report__kind__in=['INITIAL', 'NORMAL'])
            .filter(group__in=groups)
        )
        group_reports = dict((g.group, g) for g in group_reports)
        groups = []
        for group_name, tests in itertools.groupby(
            test_reports, attrgetter('test_group')
        ):
            groups.append({'tests': list(tests), 'report': group_reports[group_name]})

        problem_score = None
        max_problem_score = None
        for group in groups:
            group_score = group['report'].score
            group_max_score = group['report'].max_score

            if problem_score is None:
                problem_score = group_score
            elif group_score is not None:
                problem_score += group_score

            if max_problem_score is None:
                max_problem_score = group_max_score
            elif group_max_score is not None:
                max_problem_score += group_max_score

        resultsets.append(
            dict(
                result=r,
                score=problem_score,
                max_score=max_problem_score,
                compilation_report=compilation_report,
                groups=groups,
                code=six.ensure_text(source_file.read(), errors="replace"),
                codefile=source_file.file.name,
            )
        )
        if total_score is None:
            total_score = problem_score
        elif problem_score is not None:
            total_score += problem_score
    return {
        'user': user,
        'resultsets': resultsets,
        'sum': total_score,
    }


def _serialize_reports(users, problem_instances, test_groups):
    """Runs :meth:`serialize_report` for a number of users.

    Returns a list of objects produced by serialize_report, sorted
    by user's last name and first name.
    """
    data = []
    for user in users.order_by('last_name', 'first_name', 'username'):
        user_data = _serialize_report(user, problem_instances, test_groups)
        if user_data['resultsets']:
            data.append(user_data)
    return data


def _report_text(request, template_file, report_form):
    round_key = report_form.cleaned_data['report_round']
    if round_key == CONTEST_REPORT_KEY:
        round = None
    else:
        round = Round.objects.get(contest=request.contest, id=round_key)

    title = request.contest.name
    if round:
        title += ' -- ' + round.name

    # Region object
    region_key = report_form.cleaned_data['report_region']
    if region_key == CONTEST_REPORT_KEY:
        region = None
    else:
        region = Region.objects.get(short_name=region_key, contest=request.contest)

    if report_form.cleaned_data['is_single_report']:
        users = User.objects.filter(
            username=report_form.cleaned_data['single_report_user']
        )
    else:
        users = _users_in_contest(request, region)

    # Generate report
    testgroups = report_form.get_testgroups(request)
    return _render_report(
        request, template_file, title, users, list(testgroups.keys()), testgroups
    )


def generate_pdfreport(request, report_form):
    report = _report_text(request, 'oireports/pdfreport.tex', report_form)
    filename = '%s-%s-%s.pdf' % (
        request.contest.id,
        report_form.cleaned_data['report_round'],
        report_form.cleaned_data['report_region'],
    )

    return generate_pdf(report, filename)


def generate_xmlreport(request, report_form):
    report = _report_text(request, 'oireports/xmlreport.xml', report_form)
    filename = '%s-%s-%s.xml' % (
        request.contest.id,
        report_form.cleaned_data['report_round'],
        report_form.cleaned_data['report_region'],
    )
    return stream_file(ContentFile(report.encode('utf-8')), filename)


@enforce_condition(contest_exists & is_contest_admin)
def get_report_users_view(request):
    queryset = Submission.objects.filter(problem_instance__contest=request.contest)
    return get_user_hints_view(request, 'substr', queryset, 'user')
