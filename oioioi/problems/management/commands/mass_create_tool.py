import random
import string
import sys

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from oioioi.problems.models import (
    Problem,
    AlgorithmTag,
    DifficultyTag,
    AlgorithmTagThrough,
    DifficultyTagThrough,
    AlgorithmTagProposal,
    DifficultyTagProposal,
)

User = get_user_model()

def get_unique_candidate(candidate_fn, uniqueness_fn, max_attempts=10):
    """
    Repeatedly calls candidate_fn() until uniqueness_fn(candidate) is True,
    or max_attempts is reached. Raises CommandError if no unique candidate is found.
    """
    for attempt in range(max_attempts):
        candidate = candidate_fn()
        if uniqueness_fn(candidate):
            return candidate
    raise CommandError(
        f"Failed to generate a unique candidate after {max_attempts} attempts"
    )

class Command(BaseCommand):
    help = (
        "Allows the creation of mock data for testing purposes. "
        "Creates Problems, Users, Algorithm Tags, Difficulty Tags, Algorithm Tag Proposals, and "
        "Algorithm Tag Through and Difficulty Tag Through records to assign tags to problems. Use with caution in production environments. "
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--problems', '-p',
            type=int,
            default=0,
            metavar='N',
            help='Number of problems to create (default: 0)'
        )
        parser.add_argument(
            '--users', '-u',
            type=int,
            default=0,
            metavar='N',
            help='Number of users to create (default: 0)'
        )
        parser.add_argument(
            '--algotags', '-at',
            type=int,
            default=0,
            metavar='N',
            help='Number of algorithm tags to create (default: 0)'
        )
        parser.add_argument(
            '--difftags', '-dt',
            type=int,
            default=0,
            metavar='N',
            help='Number of difficulty tags to create (default: 0)'
        )
        parser.add_argument(
            '--algothrough', '-att',
            type=int,
            default=0,
            metavar='N',
            help='Number of algorithm tag through records (assigning algorithm tags to problems) to create (default: 0)'
        )
        parser.add_argument(
            '--diffthrough', '-dtt',
            type=int,
            default=0,
            metavar='N',
            help='Number of difficulty tag through records (assigning difficulty tags to problems) to create (default: 0)'
        )
        parser.add_argument(
            '--algoproposals', '-ap',
            type=int,
            default=0,
            metavar='N',
            help='Number of algorithm tag proposals to create (default: 0)'
        )
        parser.add_argument(
            '--diffproposals', '-dp',
            type=int,
            default=0,
            metavar='N',
            help='Number of difficulty tag proposals to create (default: 0)'
        )
        parser.add_argument(
            '--seed', '-s',
            type=int,
            default=None,
            metavar='SEED',
            help='Random seed for reproducibility'
        )

    def create_unique_objects(self, count, candidate_prefix, random_length, uniqueness_fn, create_instance_fn, verbose_name, verbosity):
        """
        Creates a list of objects using get_unique_candidate.
        - count: number of objects to create.
        - candidate_prefix: A prefix string (e.g. 'prob_').
        - random_length: Number of random characters to append.
        - uniqueness_fn: Function taking candidate -> bool (should return True if candidate is unique).
        - create_instance_fn: Function taking candidate -> instance (which should be saved later).
        - verbose_name: A description used in output.
        - verbosity: The current verbosity level.
        Returns a list of created objects.
        """
        candidate_prefix = self.auto_prefix + candidate_prefix

        objs = []
        for i in range(count):
            candidate_fn = lambda: candidate_prefix + ''.join(random.choices(string.ascii_lowercase, k=random_length))
            try:
                unique_candidate = get_unique_candidate(candidate_fn, uniqueness_fn)
            except CommandError as e:
                self.errors_found = True
                self.stderr.write(self.style.ERROR(
                    f"Failed to create {verbose_name} candidate: {e}. Stopping further creation for {verbose_name}."
                ))
                break
            instance = create_instance_fn(unique_candidate)
            instance.save()
            objs.append(instance)
            if verbosity >= 3:
                self.stdout.write(self.style.SUCCESS(
                    f"Created {verbose_name}: {unique_candidate} (ID: {getattr(instance, 'id', 'N/A')})"
                ))
            elif verbosity == 2:
                sys.stdout.write(f"Created {i+1} of {count} {verbose_name}s\r")
                sys.stdout.flush()
        if verbosity == 2 and objs:
            sys.stdout.write("\n")
        return objs

    def create_through_records(self, count, problems, tags, through_model, verbose_name, verbosity):
        """
        Creates a specified number of through-records connecting a problem and a tag.
        For DifficultyTagThrough ensures that each problem is assigned to at most one difficulty tag.
        For AlgorithmTagThrough ensures that each (problem, tag) pair is unique.
        - count: number of through records to create.
        - problems: list of existing problems.
        - tags: list of existing tags.
        - through_model: the through model class to use.
        - verbose_name: description used in output.
        - verbosity: the current verbosity level.
        Returns a list of created through-records.
        """
        objs = []
        for i in range(count):
            candidate_fn = lambda: (random.choice(problems), random.choice(tags))
            if through_model == DifficultyTagThrough:
                uniqueness_fn = lambda candidate: not (
                    through_model.objects.filter(problem=candidate[0]).exists() or
                    any(r.problem == candidate[0] for r in objs)
                )
            else:
                uniqueness_fn = lambda candidate: not (
                    through_model.objects.filter(problem=candidate[0], tag=candidate[1]).exists() or
                    any(r.problem == candidate[0] and r.tag == candidate[1] for r in objs)
                )
            try:
                candidate = get_unique_candidate(candidate_fn, uniqueness_fn)
            except CommandError as e:
                self.errors_found = True
                self.stderr.write(self.style.ERROR(
                    f"Failed to create {verbose_name} candidate: {e}. Stopping further creation for {verbose_name}."
                ))
                break
            record = through_model(problem=candidate[0], tag=candidate[1])
            record.save()
            objs.append(record)
            if verbosity >= 3:
                self.stdout.write(self.style.SUCCESS(
                    f"Created {verbose_name}: Problem ID {candidate[0].id} - Tag {candidate[1].name}"
                ))
            elif verbosity == 2:
                sys.stdout.write(f"Created {i+1} of {count} {verbose_name}s\r")
                sys.stdout.flush()
        if verbosity == 2 and count:
            sys.stdout.write("\n")
        return objs

    def create_proposals(self, count, problems, users, tags, proposal_model, verbose_name, verbosity):
        """
        Creates algorithm tag proposals by pairing problems, users, and algotags randomly.
        Returns a list of created AlgorithmTagProposal objects.
        """
        objs = []
        for i in range(count):
            problem = random.choice(problems)
            user = random.choice(users)
            tag = random.choice(tags)
            proposal = proposal_model(problem=problem, user=user, tag=tag)
            proposal.save()
            objs.append(proposal)
            if verbosity >= 3:
                self.stdout.write(self.style.SUCCESS(
                    f"Created Proposal: Problem ID {problem.id} - User {user.username} - Tag {tag.name}"
                ))
            elif verbosity == 2:
                sys.stdout.write(f"Created {i+1} of {count} {verbose_name}s\r")
                sys.stdout.flush()
        if verbosity == 2 and objs:
            sys.stdout.write("\n")
        return objs

    def write_summary(self, created, expected, object_name):
        if expected == 0:
            return
        if created == expected:
            msg = f"Created {expected} {object_name}."
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            msg = f"Created {created} of {expected} {object_name}."
            self.stdout.write(self.style.WARNING(msg))

    def handle(self, *args, **options):
        self.errors_found = False
        self.auto_prefix = "auto_"

        num_problems = options['problems']
        num_users = options['users']
        num_algotags = options['algotags']
        num_difftags = options['difftags']
        num_algothrough = options['algothrough']
        num_diffthrough = options['diffthrough']
        num_algoproposals = options['algoproposals']
        num_diffproposals = options['diffproposals']
        seed = options['seed']
        verbosity = int(options.get('verbosity', 1))

        if (num_problems == 0 and num_users == 0 and num_algotags == 0 and num_difftags == 0
            and num_algothrough == 0 and num_diffthrough == 0
            and num_algoproposals == 0 and num_diffproposals == 0):
            self.stdout.write(self.style.WARNING(
                "No objects specified for creation. Please set one or more counts to non-zero. "
                "See --help for usage details."
            ))
            return

        if seed is not None:
            random.seed(seed)

        if num_algothrough > 0 and (num_problems <= 0 or num_algotags <= 0):
            self.errors_found = True
            raise CommandError("Assigning algorithm tags to problems requires at least one problem and one algorithm tag to be created first.")

        if num_diffthrough > 0 and (num_problems <= 0 or num_difftags <= 0):
            self.errors_found = True
            raise CommandError("Assigning difficulty tags to problems requires at least one problem and one difficulty tag to be created first.")

        if num_algoproposals > 0 and (num_problems <= 0 or num_users <= 0 or num_algotags <= 0):
            self.errors_found = True
            raise CommandError("Creation of algorithm tag proposals requires at least one problem, one user, and one algorithm tag to be created first.")

        if num_diffproposals > 0 and (num_problems <= 0 or num_users <= 0 or num_difftags <= 0):
            self.errors_found = True
            raise CommandError("Creation of difficulty tag proposals requires at least one problem, one user, and one difficulty tag to be created first.")

        created_problems = self.create_unique_objects(
            count=num_problems,
            candidate_prefix='prob_',
            random_length=10,
            uniqueness_fn=lambda s: not Problem.objects.filter(short_name=s).exists(),
            create_instance_fn=lambda candidate: Problem(short_name=candidate),
            verbose_name="Problem",
            verbosity=verbosity,
        )

        created_users = self.create_unique_objects(
            count=num_users,
            candidate_prefix='user_',
            random_length=10,
            uniqueness_fn=lambda s: not User.objects.filter(username=s).exists(),
            create_instance_fn=lambda candidate: User.objects.create_user(username=candidate, email=f"{candidate}@example.com", password="password"),
            verbose_name="User",
            verbosity=verbosity,
        )

        created_algotags = self.create_unique_objects(
            count=num_algotags,
            candidate_prefix='algo_',
            random_length=8,
            uniqueness_fn=lambda s: not AlgorithmTag.objects.filter(name=s).exists(),
            create_instance_fn=lambda candidate: AlgorithmTag(name=candidate),
            verbose_name="Algorithm Tag",
            verbosity=verbosity,
        )

        created_difftags = self.create_unique_objects(
            count=num_difftags,
            candidate_prefix='diff_',
            random_length=8,
            uniqueness_fn=lambda s: not DifficultyTag.objects.filter(name=s).exists(),
            create_instance_fn=lambda candidate: DifficultyTag(name=candidate),
            verbose_name="Difficulty Tag",
            verbosity=verbosity,
        )

        created_algothrough = []
        if created_problems and created_algotags and num_algothrough > 0:
            created_algothrough = self.create_through_records(
                count=num_algothrough,
                problems=created_problems,
                tags=created_algotags,
                through_model=AlgorithmTagThrough,
                verbose_name="Algorithm Tag Through",
                verbosity=verbosity,
            )
        elif num_algothrough > 0:
            self.errors_found = True
            self.stderr.write(self.style.ERROR(
                "Not all prerequisites were created: skipping Algorithm Tag Through records."
            ))

        created_diffthrough = []
        if created_problems and created_difftags and num_diffthrough > 0:
            created_diffthrough = self.create_through_records(
                count=num_diffthrough,
                problems=created_problems,
                tags=created_difftags,
                through_model=DifficultyTagThrough,
                verbose_name="Difficulty Tag Through",
                verbosity=verbosity,
            )
        elif num_diffthrough > 0:
            self.errors_found = True
            self.stderr.write(self.style.ERROR(
                "Not all prerequisites were created: skipping Difficulty Tag Through records."
            ))

        created_algoproposals = []
        if created_problems and created_users and created_algotags:
            created_algoproposals = self.create_proposals(
                count=num_algoproposals,
                problems=created_problems,
                users=created_users,
                tags=created_algotags,
                proposal_model=AlgorithmTagProposal,
                verbose_name="Algorithm Tag Proposal",
                verbosity=verbosity,
            )
        elif num_algoproposals > 0:
            self.errors_found = True
            self.stderr.write(self.style.ERROR(
                "Not all prerequisites were created: skipping Algorithm Tag Proposals."
            ))

        created_diffproposals = []
        if created_problems and created_users and created_difftags:
            created_diffproposals = self.create_proposals(
                count=num_diffproposals,
                problems=created_problems,
                users=created_users,
                tags=created_difftags,
                proposal_model=DifficultyTagProposal,
                verbose_name="Difficulty Tag Proposal",
                verbosity=verbosity,
            )
        elif num_diffproposals > 0:
            self.errors_found = True
            self.stderr.write(self.style.ERROR(
                "Not all prerequisites were created: skipping Difficulty Tag Proposals."
            ))

        overall_msg = "Mock data creation complete." if not self.errors_found else "Errors occurred during mock data creation."
        overall_status = self.style.SUCCESS if not self.errors_found else self.style.WARNING
        self.stdout.write(overall_status(overall_msg))

        if verbosity >= 1:
            self.write_summary(len(created_problems), options['problems'], "Problems")
            self.write_summary(len(created_users), options['users'], "Users")
            self.write_summary(len(created_algotags), options['algotags'], "Algorithm Tags")
            self.write_summary(len(created_difftags), options['difftags'], "Difficulty Tags")
            self.write_summary(len(created_algothrough), options['algothrough'], "Algorithm Tag Through Records")
            self.write_summary(len(created_diffthrough), options['diffthrough'], "Difficulty Tag Through Records")
            self.write_summary(len(created_algoproposals), options['algoproposals'], "Algorithm Tag Proposals")
            self.write_summary(len(created_diffproposals), options['diffproposals'], "Difficulty Tag Proposals")
