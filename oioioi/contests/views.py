from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.http import HttpResponseRedirect
from django import forms
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.contrib import messages
from oioioi.base.menu import menu_registry
from oioioi.base.permissions import not_anonymous
from oioioi.problems.models import ProblemStatement, ProblemAttachment
from oioioi.contests.models import ProblemInstance, Submission, \
        SubmissionReport, ContestAttachment
from oioioi.contests.controllers import ContestController
from oioioi.contests.utils import visible_contests, can_enter_contest, is_contest_admin
from oioioi.filetracker.utils import stream_file
from oioioi.base.permissions import enforce_condition
import sys
from operator import itemgetter

def has_any_submittable_problem(request):
    controller = request.contest.controller
    for pi in ProblemInstance.objects.filter(contest=request.contest) \
            .select_related():
        if controller.can_submit(request, pi):
            return True
    return False

def visible_problem_instances(request):
    controller = request.contest.controller
    queryset = ProblemInstance.objects.filter(contest=request.contest) \
            .select_related('problem')
    return [pi for pi in queryset if controller.can_see_problem(request, pi)]

def submitable_problem_instances(request):
    controller = request.contest.controller
    queryset = ProblemInstance.objects.filter(contest=request.contest) \
            .select_related('problem')
    return [pi for pi in queryset if controller.can_submit(request, pi)]


menu_registry.register('problems_list', _("Problems"),
        lambda request: reverse('problems_list', kwargs={'contest_id':
            request.contest.id}), order=100)

menu_registry.register('contest_files', _("Files"),
        lambda request: reverse('contest_files', kwargs={'contest_id':
            request.contest.id}), condition=not_anonymous,
        order=200)

menu_registry.register('submit', _("Submit"),
        lambda request: reverse('submit', kwargs={'contest_id':
            request.contest.id}), condition=has_any_submittable_problem,
        order=300)

menu_registry.register('my_submissions', _("My submissions"),
        lambda request: reverse('my_submissions', kwargs={'contest_id':
            request.contest.id}), condition=not_anonymous,
        order=400)

def select_contest_view(request):
    contests = visible_contests(request)
    return TemplateResponse(request, 'contests/select_contest.html',
            {'contests': contests})

@enforce_condition(can_enter_contest)
def default_contest_view(request, contest_id):
    url = request.contest.controller.default_view(request)
    return HttpResponseRedirect(url)

@enforce_condition(can_enter_contest)
def problems_list_view(request, contest_id):
    problem_instances = visible_problem_instances(request)
    show_rounds = len(frozenset(pi.round_id for pi in problem_instances)) > 1
    return TemplateResponse(request, 'contests/problems_list.html',
                {'problem_instances': problem_instances,
                 'show_rounds': show_rounds})

@enforce_condition(can_enter_contest)
def problem_statement_view(request, contest_id, problem_instance):
    controller = request.contest.controller
    pi = get_object_or_404(ProblemInstance, round__contest=request.contest,
            short_name=problem_instance)

    if not controller.can_see_problem(request, pi):
        raise PermissionDenied

    statements = ProblemStatement.objects.filter(problem=pi.problem)
    if not statements:
        return TemplateResponse(request, 'contests/no_problem_statement.html',
                    {'problem_instance': pi})

    lang_prefs = [translation.get_language()] + ['', None] + \
            [l[0] for l in settings.LANGUAGES]
    ext_prefs = ['.pdf', '.ps', '.html', '.txt']

    def sort_key(statement):
        try:
            lang_pref = lang_prefs.index(statement.language)
        except ValueError:
            lang_pref = sys.maxint
        try:
            ext_pref = (ext_prefs.index(statement.extension), '')
        except ValueError:
            ext_pref = (sys.maxint, statement.extension)
        return lang_pref, ext_pref

    statement = sorted(statements, key=sort_key)[0]
    return stream_file(statement.content)

class SubmissionForm(forms.Form):
    problem_instance_id = forms.ChoiceField(label=_("Problem"))

    def __init__(self, request, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)

        self.request = request

        pis = submitable_problem_instances(request)
        pi_choices = [(pi.id, unicode(pi)) for pi in pis]
        self.fields['problem_instance_id'].choices = pi_choices

        request.contest.controller.adjust_submission_form(request, self)

    def clean(self):
        cleaned_data = forms.Form.clean(self)

        if 'problem_instance_id' not in cleaned_data:
            return cleaned_data

        try:
            pi = ProblemInstance.objects.filter(contest=self.request.contest) \
                    .get(id=cleaned_data['problem_instance_id'])
            cleaned_data['problem_instance'] = pi
        except ProblemInstance.DoesNotExist:
            self._errors['problem_instance_id'] = self.error_class([
                _("Invalid problem")])
            del cleaned_data['problem_instance_id']
            return cleaned_data

        submissions_number = Submission.objects \
            .filter(user=self.request.user, problem_instance__id=pi.id) \
            .count()
        submissions_limit = \
            self.request.contest.controller.get_submissions_limit()
        if submissions_limit and submissions_number >= submissions_limit:
            raise forms.ValidationError(_("Submission limit for the problem \
                '%s' exceeded." % (pi.problem.name,)))

        decision = self.request.contest.controller.can_submit(self.request, pi)
        if not decision:
            raise forms.ValidationError(str(decision.exc))

        return self.request.contest.controller.validate_submission_form(
                self.request, pi, self, cleaned_data)

@enforce_condition(can_enter_contest)
def submit_view(request, contest_id):
    if request.method == 'POST':
        form = SubmissionForm(request, request.POST, request.FILES)
        if form.is_valid():
            request.contest.controller.create_submission(request,
                    form.cleaned_data['problem_instance'], form.cleaned_data)
            return redirect('my_submissions', contest_id=contest_id)
    else:
        form = SubmissionForm(request)
        if not form.fields['problem_instance_id'].choices:
            return TemplateResponse(request, 'contests/nothing_to_submit.html')
    return TemplateResponse(request, 'contests/submit.html', {'form': form})

def submission_template_context(request, submission):
    controller = submission.problem_instance.contest.controller
    can_see_status = controller.can_see_submission_status(request, submission)
    can_see_score = controller.can_see_submission_score(request, submission)
    can_see_comment = controller.can_see_submission_comment(request,
            submission)
    return {'submission': submission,
            'can_see_status': can_see_status,
            'can_see_score': can_see_score,
            'can_see_comment': can_see_comment}

@enforce_condition(can_enter_contest)
def my_submissions_view(request, contest_id):
    queryset = Submission.objects \
            .filter(problem_instance__contest=request.contest) \
            .order_by('-date') \
            .select_related()
    controller = request.contest.controller
    queryset = controller.filter_visible_submissions(request, queryset)
    show_scores = bool(queryset.filter(score__isnull=False))
    return TemplateResponse(request, 'contests/my_submissions.html',
                {'submissions': [submission_template_context(request, s)
                    for s in queryset], 'show_scores': show_scores})

def check_submission_access(request, submission):
    if submission.problem_instance.contest != request.contest:
        raise PermissionDenied
    if request.user.has_perm('contests.contest_admin', request.contest):
        return
    controller = request.contest.controller
    queryset = Submission.objects.filter(id=submission.id)
    if not controller.filter_visible_submissions(request, queryset):
        raise PermissionDenied

@enforce_condition(can_enter_contest)
def submission_view(request, contest_id, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    check_submission_access(request, submission)

    controller = request.contest.controller
    header = controller.render_submission(request, submission)
    reports = []
    queryset = SubmissionReport.objects.filter(submission=submission,
            status='ACTIVE')
    for report in controller.filter_visible_reports(request, submission,
            queryset):
        reports.append(controller.render_report(request, report))

    return TemplateResponse(request, 'contests/submission.html',
                {'submission': submission, 'header': header,
                    'reports': reports})

@enforce_condition(is_contest_admin)
def rejudge_submission_view(request, contest_id, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    controller = request.contest.controller
    controller.judge(submission, request.GET.dict())
    messages.info(request, _("Rejudge request received."))
    return redirect('submission', contest_id=contest_id,
            submission_id=submission_id)

@enforce_condition(can_enter_contest)
def files_view(request, contest_id):
    contest_files = ContestAttachment.objects.filter(contest=request.contest)
    problem_instances = visible_problem_instances(request)
    problem_ids = [pi.problem_id for pi in problem_instances]
    problem_files = \
            ProblemAttachment.objects.filter(problem_id__in=problem_ids)
    rows = [{
        'name': cf.filename,
        'description': cf.description,
        'link': reverse('contest_attachment', kwargs={'contest_id': contest_id,
            'attachment_id': cf.id}),
        } for cf in contest_files]
    rows += [{
        'name': pf.filename,
        'description': u'%s: %s' % (pf.problem, pf.description),
        'link': reverse('problem_attachment', kwargs={'contest_id': contest_id,
            'attachment_id': pf.id}),
        } for pf in problem_files]
    rows.sort(key=itemgetter('name'))
    return TemplateResponse(request, 'contests/files.html', {'files': rows})

@enforce_condition(can_enter_contest)
def contest_attachment_view(request, contest_id, attachment_id):
    attachment = get_object_or_404(ContestAttachment, contest_id=contest_id,
        id=attachment_id)
    return stream_file(attachment.content)

@enforce_condition(can_enter_contest)
def problem_attachment_view(request, contest_id, attachment_id):
    attachment = get_object_or_404(ProblemAttachment, id=attachment_id)
    problem_instances = visible_problem_instances(request)
    problem_ids = [pi.problem_id for pi in problem_instances]
    if attachment.problem_id not in problem_ids:
        raise PermissionDenied
    return stream_file(attachment.content)
