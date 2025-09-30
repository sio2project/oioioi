import csv
import os
import shutil
import tarfile
import tempfile

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.encoding import force_str

from oioioi.filetracker.client import get_client
from oioioi.filetracker.utils import django_to_filetracker_path
from oioioi.participants.models import Participant
from oioioi.programs.models import ProgramSubmission
from oioioi.programs.utils import get_extension


class SubmissionData:
    submission_id = None
    user_id = None
    username = None
    first_name = None
    last_name = None
    city = None
    school = None
    school_city = None
    problem_short_name = None
    score = None
    solution_language = None
    source_file = None


class SubmissionsWithUserDataCollector:
    """
    Collects submissions with some associated data in specific contest with
    some filtering.

    We want the user of collector objects to know nothing (or very little)
    about the database, controller logic etc. It is responsibility of
    the collector to provide access to fully prepared data.
    """

    def __init__(self, contest, round=None, problem_instance=None, language=None, only_final=True):
        self.contest = contest
        self.round = round
        self.problem_instance = problem_instance

        if language:
            exts = getattr(settings, "SUBMITTABLE_EXTENSIONS", {})
            if language not in exts:
                raise ValueError("Invalid programming language")
            self.lang_exts = exts[language]
        else:
            self.lang_exts = None

        self.only_final = only_final
        self.filetracker = get_client()

    def get_contest_id(self):
        return self.contest.id

    def collect_list(self):
        q_expressions = Q(user__isnull=False)

        if self.round:
            q_expressions &= Q(problem_instance__round=self.round)
        else:
            q_expressions &= Q(problem_instance__contest=self.contest)

        if self.problem_instance:
            q_expressions &= Q(problem_instance=self.problem_instance)

        if self.lang_exts:
            q_expr_langs = Q()
            for ext in self.lang_exts:
                q_expr_langs |= Q(source_file__contains=f".{ext}@")
            q_expressions &= q_expr_langs

        if self.only_final:
            q_expressions &= Q(submissionreport__userresultforproblem__isnull=False)

        submissions_list = []
        psubmissions = ProgramSubmission.objects.filter(q_expressions).select_related()

        for s in psubmissions:
            data = SubmissionData()
            data.submission_id = s.id
            data.user_id = s.user_id
            data.username = s.user.username
            data.first_name = s.user.first_name
            data.last_name = s.user.last_name
            data.problem_short_name = s.problem_instance.short_name
            data.score = s.score
            data.solution_language = get_extension(s.source_file.name)
            data.source_file = s.source_file

            # here we try to get some optional data, it just may not be there
            # and it's ok
            try:
                registration = Participant.objects.select_related().get(contest_id=self.contest.id, user=s.user).registration_model
                try:
                    data.city = registration.city
                except AttributeError:
                    pass
                try:
                    data.school = registration.school.name
                    data.school_city = registration.school.city
                except AttributeError:
                    pass
            except (Participant.DoesNotExist, ObjectDoesNotExist):
                pass

            submissions_list.append(data)
        return submissions_list

    def get_submission_source(self, out_file_path, source):
        ft_file = django_to_filetracker_path(source)
        self.filetracker.get_file(ft_file, out_file_path, add_to_cache=False)


def build_submissions_archive(out_file, submission_collector):
    """
    Builds submissions archive, in szubrawcy format, in out_file from data
    provided by submission_collector. Argument out_file should be a file-like
    object.
    """
    submission_list = submission_collector.collect_list()
    tmpdir = tempfile.mkdtemp()
    try:
        contest_id = submission_collector.get_contest_id()
        files_dir = os.path.join(tmpdir, contest_id)
        os.mkdir(files_dir, 0o700)
        with open(os.path.join(files_dir, "INDEX"), "w") as f:
            index_csv = csv.writer(f)
            header = [
                "submission_id",
                "user_id",
                "username",
                "first_name",
                "last_name",
                "city",
                "school",
                "school_city",
                "problem_short_name",
                "score",
            ]
            index_csv.writerow(header)
            for s in submission_list:
                index_entry = [
                    s.submission_id,
                    s.user_id,
                    s.username,
                    s.first_name,
                    s.last_name,
                    s.city,
                    s.school,
                    s.school_city,
                    s.problem_short_name,
                    s.score,
                ]

                def encode(obj):
                    if obj is None:
                        return "NULL"
                    else:
                        return force_str(obj, errors="ignore")

                index_csv.writerow([encode(col) for col in index_entry])

        for s in submission_list:
            filename = f"{s.submission_id}:{s.username}:{s.problem_short_name}.{s.solution_language}"
            dest = os.path.join(files_dir, filename)
            submission_collector.get_submission_source(dest, s.source_file)

        with tarfile.open(fileobj=out_file, mode="w:gz") as tar:
            tar.add(files_dir, arcname=contest_id)
    finally:
        shutil.rmtree(tmpdir)
