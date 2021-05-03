import six
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _

from oioioi.contests.models import ProblemInstance
from oioioi.exportszu.utils import SubmissionsWithUserDataCollector
from oioioi.plagiarism.utils import MossClient, MossException, submit_and_get_url


class Command(BaseCommand):
    help = _("Submits submissions to the MOSS (code similarity detection tool).")

    def add_arguments(self, parser):
        parser.add_argument(
            '-a',
            '--all',
            action='store_true',
            dest='all',
            help="Submit all scored submissions, not only final.",
        )
        parser.add_argument(
            '-l',
            '--language',
            choices=list(getattr(settings, 'SUBMITTABLE_EXTENSIONS', {}).keys()),
            dest='lang',
            required=True,
            help="Programming language of the exported submissions.",
        )
        parser.add_argument(
            '-i',
            '--user-id',
            type=int,
            required=True,
            dest='userid',
            help="MOSS user ID",
        )
        parser.add_argument('probleminstance_id', type=str, help="Problem instance")

    def handle(self, *args, **options):
        problem_instance = ProblemInstance.objects.get(id=options['probleminstance_id'])
        contest = problem_instance.contest
        language = options['lang']
        collector = SubmissionsWithUserDataCollector(
            contest,
            problem_instance=problem_instance,
            language=language,
            only_final=not options.get('all'),
        )
        client = MossClient(options['userid'], language)
        try:
            url = submit_and_get_url(client, collector)
        except MossException as e:
            raise CommandError(
                _('There was an error with the submission: %s') % e.message
            )
        else:
            print(
                self.style.SUCCESS(
                    _('Successfully submitted the source codes. URL to the results: %s')
                    % url
                )
            )
