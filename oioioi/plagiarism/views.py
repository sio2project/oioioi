from django.shortcuts import redirect
from django.template.response import TemplateResponse

from oioioi.base.permissions import enforce_condition
from oioioi.contests.utils import contest_exists, is_contest_admin
from oioioi.exportszu.utils import SubmissionsWithUserDataCollector
from oioioi.plagiarism.forms import MossSubmitForm
from oioioi.plagiarism.utils import MossClient, MossException, submit_and_get_url


def _make_moss_form(request, *args, **kwargs):
    form = MossSubmitForm(request.contest.probleminstance_set, *args, **kwargs)
    return form


@enforce_condition(contest_exists & is_contest_admin)
def moss_submit(request):
    if request.method == 'POST':
        form = _make_moss_form(request, request.POST)
        if form.is_valid():
            problem_instance = form.cleaned_data['problem_instance']
            language = form.cleaned_data['language']
            only_final = form.cleaned_data['only_final']
            userid = form.cleaned_data['userid']
            collector = SubmissionsWithUserDataCollector(
                request.contest,
                problem_instance=problem_instance,
                language=language,
                only_final=only_final,
            )
            client = MossClient(userid, language)
            try:
                url = submit_and_get_url(client, collector)
            except MossException as e:
                return TemplateResponse(
                    request,
                    'plagiarism/moss_submit.html',
                    {'form': form, 'moss_error': e.message},
                )
            return redirect(url)
    else:
        form = _make_moss_form(request)
    return TemplateResponse(request, 'plagiarism/moss_submit.html', {'form': form})
