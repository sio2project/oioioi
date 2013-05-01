import os
import shutil
import re
import itertools
import subprocess
from collections import defaultdict
from tempfile import mkdtemp, mkstemp
from operator import attrgetter

from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile, File
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from oioioi.base.permissions import enforce_condition
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.filetracker.utils import stream_file
from oioioi.contests.models import ProblemInstance, Round, \
        UserResultForProblem
from oioioi.contests.utils import is_contest_admin, contest_exists
from oioioi.programs.models import CompilationReport, GroupReport, \
        TestReport, Test
from oioioi.oi.models import Region

CONTEST_REPORT_KEY = 'all'

# FIXME conditions for views expressing oi dependence?

def _rounds(request):
    rounds = [(CONTEST_REPORT_KEY, _("Contest"))]
    for round in request.contest.round_set.all():
        rounds.append((str(round.id), round.name))
    if len(rounds) == 1:
        # No rounds have visible results
        return []
    if len(rounds) == 2:
        # Only a single round => call this "contest report".
        return rounds[:1]
    return rounds

def _regions(request):
    res = [(CONTEST_REPORT_KEY, _("All"))]
    regions = Region.objects.filter(contest=request.contest)
    for r in regions:
        res.append((r.short_name, r.name))
    return res

def _problem_instances(request, round):
    pis = ProblemInstance.objects.filter(round=round)
    return pis

def _testgroups(request):
    testgroups = []
    for round in request.contest.round_set.all():
        pis = list(ProblemInstance.objects.filter(round=round))
        res = {
            'id': str(round.id),
            'name': round.name,
            'tasks': []
        }
        for pi in pis:
            task = {
                'name': pi.problem.name,
                'short_name': pi.short_name,
                'testgroups': []
            }
            for test in list(Test.objects.filter(problem=pi.problem)):
                if test.group not in task['testgroups']:
                    task['testgroups'].append(test.group)
            res['tasks'].append(task)
        testgroups.append(res)
    return testgroups

def _users_in_contest(request, region=None):
    queryset = User.objects.filter(participant__contest=request.contest,
        participant__status='ACTIVE')
    if region is not None:
        queryset = queryset.filter(
                participant__oi_oionsiteregistration__region_id=region)
    return queryset

def _testgroups_from_POST(request):
    testgroups = defaultdict(list)
    regex = re.compile(r'testgroup\[(.*)\]\[(.*)\]$')
    for key in request.POST:
        match = regex.match(key)
        if match:
            problem_instance = ProblemInstance.objects.get(
                    short_name=match.group(1), round__contest=request.contest)
            testgroups[problem_instance].append(match.group(2))
    return testgroups


@contest_admin_menu_registry.register_decorator(_("Printing reports"),
    lambda request: reverse('report_options',
        kwargs={'contest_id': request.contest.id}),
    order=440)
@enforce_condition(contest_exists & is_contest_admin)
def report_options_view(request, contest_id):
    rounds = _rounds(request)
    regions = _regions(request)
    testgroups = _testgroups(request)
    if not rounds:
        return TemplateResponse(request, 'oireports/no_reports.html')
    return TemplateResponse(request, 'oireports/report_options.html',
        {
            'rounds': rounds,
            'regions': regions,
            'testgroups': testgroups,
            'CONTEST_REPORT_KEY': CONTEST_REPORT_KEY,
        })

def _render_report(request, template_name, title, users,
        problem_instances, test_groups):
    rows = _serialize_reports(users, problem_instances, test_groups)
    return render_to_string(template_name,
            context_instance=RequestContext(request, {
                'rows': rows,
                'title': title,
            }))

def _render_pdf_report(request, title, users, problem_instances,
        test_groups):
    return _render_report(request, 'oireports/pdfreport.tex', title,
            users, problem_instances, test_groups)

def _render_xml_report(request, title, users, problem_instances,
        test_groups):
    return _render_report(request, 'oireports/xmlreport.xml', title,
            users, problem_instances, test_groups)

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
            submission_report__isnull=False)
    for r in results:
        problem_instance = r.problem_instance
        submission_report = r.submission_report
        submission = submission_report.submission
        source_file = submission.programsubmission.source_file
        groups = list(test_groups[problem_instance])

        try:
            compilation_report = CompilationReport.objects \
                    .get(submission_report=submission_report)
        except CompilationReport.DoesNotExist:
            compilation_report = None

        try:
            test_reports = TestReport.objects \
                    .filter(submission_report__submission=submission) \
                    .filter(submission_report__status='ACTIVE') \
                    .filter(submission_report__kind__in=['INITIAL', 'NORMAL']) \
                    .filter(test_group__in=groups) \
                    .order_by('test__kind', 'test__order', 'test_name')
        except TestReport.DoesNotExist:
            test_reports = []

        group_reports = GroupReport.objects \
                .filter(submission_report__submission=submission) \
                .filter(submission_report__status='ACTIVE') \
                .filter(submission_report__kind__in=['INITIAL', 'NORMAL']) \
                .filter(group__in=groups)
        group_reports = dict((g.group, g) for g in group_reports)
        groups = []
        for group_name, tests in itertools.groupby(test_reports,
                attrgetter('test_group')):
            groups.append({'tests': list(tests),
                'report': group_reports[group_name]})

        max_problem_score = 0
        problem_score = None
        for group in groups:
            max_test_scores = frozenset(test_report.test_max_score
                    for test_report in group['tests'])
            # We assume that all tests in group have equal max_score
            # and we need only one.
            assert len(max_test_scores) == 1
            max_group_score = list(max_test_scores)[0]
            group['max_score'] = max_group_score
            max_problem_score += max_group_score
            group_score = group['report'].score
            if problem_score is None:
                problem_score = group_score
            elif group_score is not None:
                problem_score += group_score

        resultsets.append(dict(
            result=r,
            score=problem_score,
            max_score=max_problem_score,
            compilation_report=compilation_report,
            groups=groups,
            code=source_file.read(),
            codefile=source_file.file.name
        ))
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
        user_data = _serialize_report(user, problem_instances,
                test_groups)
        if user_data['resultsets']:
            data.append(user_data)
    return data

def _report_text(request, render_fn):
    round_key = request.POST.get('round_key', CONTEST_REPORT_KEY)
    if round_key == CONTEST_REPORT_KEY:
        round = None
    else:
        round = Round.objects.get(contest=request.contest, id=round_key)

    title = request.contest.name
    if round:
        title += ' -- ' + round.name

    # Region object
    region_key = request.POST.get('region_key', CONTEST_REPORT_KEY)
    if region_key == CONTEST_REPORT_KEY:
        region = None
    else:
        region = Region.objects.get(short_name=region_key,
                contest=request.contest)

    # Generate report
    testgroups = _testgroups_from_POST(request)
    return render_fn(
        request, title,
        _users_in_contest(request, region),
        testgroups.keys(),
        testgroups
    )

@enforce_condition(contest_exists & is_contest_admin)
def pdfreport_view(request, contest_id):
    report = _report_text(request, _render_pdf_report)
    # Create temporary file and folder
    tmp_folder = mkdtemp()
    try:
        tex_file, tex_filename = mkstemp(dir=tmp_folder)

        # Pass the TeX template through Django templating engine
        # and into the temp file
        os.write(tex_file, report.encode('utf-8'))
        os.close(tex_file)

        # Compile the TeX file with PDFLaTeX
        # \write18 is disabled by default, so no LaTeX injection should happen
        for i in xrange(3):
            p = subprocess.Popen([
                    'pdflatex',
                    '-output-directory=' + tmp_folder,
                    tex_filename
                ],
                stdin=open('/dev/null'),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            stdout, stderr = p.communicate()
            if p.returncode:
                raise RuntimeError('pdflatex failed: ' + stdout)

        # Get PDF file contents
        pdf_file = open(tex_filename + '.pdf', 'r')
        filename = '%s-%s-%s.pdf' % (request.contest.id,
            request.POST.get('round_key', ''),
            request.POST.get('region_key', 'all'))
        return stream_file(File(pdf_file), filename)
    finally:
        shutil.rmtree(tmp_folder)

@enforce_condition(contest_exists & is_contest_admin)
def xmlreport_view(request, contest_id):
    report = _report_text(request, _render_xml_report)
    filename = '%s-%s-%s.xml' % (request.contest.id,
        request.POST.get('round_key', ''),
        request.POST.get('region_key', 'all'))
    return stream_file(ContentFile(report.encode('utf-8')), filename)
