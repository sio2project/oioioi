# ~*~ encoding: utf-8 ~*~
import csv
import os
import shutil
import tarfile
import tempfile
from optparse import make_option

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils.encoding import force_unicode

from oioioi.contests.models import Contest, Round
from oioioi.filetracker.client import get_client
from oioioi.filetracker.utils import django_to_filetracker_path
from oioioi.participants.models import Participant
from oioioi.programs.models import ProgramSubmission


class Command(BaseCommand):
    args = "contest archive_file"
    help = "Prepare archive containing similar submissions' sources."

    option_list = BaseCommand.option_list + (
        make_option('-r', '--round',
                    action='store',
                    type='int',
                    dest='round_id',
                    help="Export only from this round"),
        make_option('-f', '--finished-rounds',
                    action='store_true',
                    dest='finished',
                    help="Export only from finished rounds"),
        make_option('-a', '--all',
                    action='store_false',
                    dest='only_final',
                    help="Export all scored submissions, not only final."),
        )

    def collect_submissions(self, contest_id, round_id=None,
            only_final=True, **kwargs):
        contest = Contest.objects.get(id=contest_id)
        ccontroller = contest.controller
        q_expressions = Q(user__isnull=False, score__isnull=False)

        if round_id:
            round = Round.objects.get(id=round_id)
            if round.contest != contest:
                raise CommandError(
                        "Round %(round)s is not from contest %(contest)s" %
                            dict(round=round.name, contest=contest.name))
            self.stdout.write("Exporting from %s: %s" %
                    (contest.name, round.name))
            q_expressions = q_expressions & Q(problem_instance__round=round)
        else:
            self.stdout.write("Exporting from %s" % contest.name)
            q_expressions = q_expressions & Q(
                    problem_instance__contest=contest)

        if only_final:
            q_expressions = q_expressions & Q(
                    submissionreport__userresultforproblem__isnull=False)

        submissions_list = []
        psubmissions = ProgramSubmission.objects.filter(q_expressions) \
                .select_related()
        for s in psubmissions:
            row = [s.id, s.user_id, s.user.username, s.user.first_name,
                   s.user.last_name]
            try:
                registration = Participant.objects.select_related().\
                    get(contest_id=contest.id, user=s.user).registration_model

                try:
                    row.append(registration.city)
                except AttributeError:
                    row.append('NULL')

                try:
                    row.extend([registration.school.name,
                                registration.school.city])
                except AttributeError:
                    row.extend(['NULL', 'NULL'])
            except (Participant.DoesNotExist, ObjectDoesNotExist):
                row.extend(['NULL', 'NULL', 'NULL'])

            row.extend([s.problem_instance.short_name, s.score])
            filename = '%s:%s:%s.%s' % (
                    s.id, s.user.username, s.problem_instance.short_name,
                    ccontroller._get_language(s.source_file))

            submissions_list.append({
                'submission': s,
                'index_entry': map(force_unicode, row),
                'filename': filename
            })

        return submissions_list

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("Exactly two arguments are required.")

        contest_id = args[0]
        out_file = args[1]

        submissions_list = self.collect_submissions(contest_id, **options)

        tmpdir = tempfile.mkdtemp()
        try:
            files_dir = os.path.join(tmpdir, contest_id)
            os.mkdir(files_dir, 0700)
            with open(os.path.join(files_dir, 'INDEX'), 'w') as f:
                index_csv = csv.writer(f)

                for submission in submissions_list:
                    index_csv.writerow([c.encode('utf8')
                                        for c in submission['index_entry']])

            ft = get_client()
            for s in submissions_list:
                ft_file = django_to_filetracker_path(
                        s['submission'].source_file)
                ft.get_file(ft_file, os.path.join(files_dir, s['filename']),
                        add_to_cache=False)

            with tarfile.open(out_file, 'w:gz') as tar:
                tar.add(files_dir, arcname=contest_id)
        finally:
            shutil.rmtree(tmpdir)
