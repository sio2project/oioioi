import random
import string
import sys

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from oioioi.problems.models import (
    Problem,
    AlgorithmTag,
    DifficultyTag,
    AlgorithmTagThrough,
    DifficultyTagThrough,
    AlgorithmTagProposal,
    DifficultyTagProposal,
    ProblemSite,
)

User = get_user_model()

def unsigned_int(value):
    ivalue = int(value)
    if ivalue < 0:
        raise ValueError(f"{value} is not a non-negative integer")
    return ivalue

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
        "!!! THIS TOOL IS INTENDED FOR BENCHMARKING AND TESTING PURPOSES ONLY -- DO NOT USE IN PRODUCTION !!! "
        "Allows the creation of mock data for testing purposes. "
        "Creates Problems, Users, Algorithm Tags, Difficulty Tags, Algorithm Tag Proposals, and "
        "Algorithm Tag Through and Difficulty Tag Through records to assign tags to problems. Use with caution in production environments. "
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--wipe', '-w',
            action='store_true',
            help='Remove all previously generated mock data before creating new data'
        )
        parser.add_argument(
            '--problems', '-p',
            type=unsigned_int,
            default=0,
            metavar='N',
            help='Number of problems to create (default: 0)'
        )
        parser.add_argument(
            '--users', '-u',
            type=unsigned_int,
            default=0,
            metavar='N',
            help='Number of users to create (default: 0)'
        )
        parser.add_argument(
            '--algotags', '-at',
            type=unsigned_int,
            default=0,
            metavar='N',
            help='Number of algorithm tags to create (default: 0)'
        )
        parser.add_argument(
            '--difftags', '-dt',
            type=unsigned_int,
            default=0,
            metavar='N',
            help='Number of difficulty tags to create (default: 0)'
        )
        parser.add_argument(
            '--algothrough', '-att',
            type=unsigned_int,
            default=0,
            metavar='N',
            help='Number of algorithm tag through records (assigning algorithm tags to problems) to create (default: 0)'
        )
        parser.add_argument(
            '--diffthrough', '-dtt',
            type=unsigned_int,
            default=0,
            metavar='N',
            help='Number of difficulty tag through records (assigning difficulty tags to problems) to create (default: 0)'
        )
        parser.add_argument(
            '--algoproposals', '-ap',
            type=unsigned_int,
            default=0,
            metavar='N',
            help='Number of algorithm tag proposals to create (default: 0)'
        )
        parser.add_argument(
            '--diffproposals', '-dp',
            type=unsigned_int,
            default=0,
            metavar='N',
            help='Number of difficulty tag proposals to create (default: 0)'
        )
        parser.add_argument(
            '--seed', '-s',
            type=unsigned_int,
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

    def create_problems(self, count, verbosity):
        """
        Creates a list of Problems using create_unique_objects,
        then creates associated ProblemSite objects.
        - count: number of objects to create.
        - candidate_prefix: A prefix string (e.g. 'prob_').
        - random_length: Number of random characters to append.
        - verbose_name: A description used in output.
        - verbosity: The current verbosity level.
        Returns a list of created objects.
        """
        created_problems = self.create_unique_objects(
            count=count,
            candidate_prefix='prob_',
            random_length=10,
            uniqueness_fn=lambda s: not Problem.objects.filter(short_name=s).exists(),
            create_instance_fn=lambda candidate: Problem.create(short_name=candidate),
            verbose_name="Problem",
            verbosity=verbosity,
        )
        for problem in created_problems:
            site = ProblemSite.objects.create(
                problem=problem,
                url_key=f"{problem.short_name}_site",
            )
            site.save()
        return created_problems

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

    def create_through_records(self, count, problems, tags, through_model, verbose_name, verbosity):
        """
        Creates exactly `count` distinct through-records connecting problems and tags.
        - For DifficultyTagThrough: at most one per problem.
        - For AlgorithmTagThrough: any unique (problem, tag) pair.
        """
        if through_model == DifficultyTagThrough:
            if count > len(problems):
                raise CommandError(
                    f"Cannot create {count} difficulty-through records; "
                    f"only {len(problems)} problems available"
                )
            chosen_problems = random.sample(problems, count)
            pairs = list(zip(chosen_problems, random.choices(tags, k=count)))
        else:
            all_pairs = [(p, t) for p in problems for t in tags]
            if count > len(all_pairs):
                raise CommandError(
                    f"Cannot create {count} algorithm-through records; "
                    f"only {len(all_pairs)} unique pairs available"
                )
            random.shuffle(all_pairs)
            pairs = all_pairs[:count]

        objs = []
        for idx, (problem, tag) in enumerate(pairs, start=1):
            record = through_model(problem=problem, tag=tag)
            record.save()
            objs.append(record)

            if verbosity >= 3:
                self.stdout.write(self.style.SUCCESS(
                    f"Created {verbose_name}: Problem ID {problem.id} - Tag {tag.name}"
                ))
            elif verbosity == 2:
                sys.stdout.write(f"Created {idx} of {count} {verbose_name}s\r")
                sys.stdout.flush()

        if verbosity == 2 and objs:
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

    def remove_all_generated_data(self):
        """
        Removes all mass-generated mock data created using this tool.
        """

        prob_qs = Problem.objects.filter(short_name__startswith=self.auto_prefix)
        prob_count = prob_qs.count()
        prob_qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {prob_count} Problems"))

        user_qs = User.objects.filter(username__startswith=self.auto_prefix)
        user_count = user_qs.count()
        user_qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {user_count} Users"))

        algo_tag_qs = AlgorithmTag.objects.filter(name__startswith=self.auto_prefix)
        algo_tag_count = algo_tag_qs.count()
        algo_tag_qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {algo_tag_count} Algorithm Tags"))

        diff_tag_qs = DifficultyTag.objects.filter(name__startswith=self.auto_prefix)
        diff_tag_count = diff_tag_qs.count()
        diff_tag_qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {diff_tag_count} Difficulty Tags"))

        self.stdout.write(self.style.SUCCESS("Through, Proposal and AggregatedProposal records are deleted on cascade, along with ProblemSites."))
        self.stdout.write(self.style.SUCCESS("Mock data removal complete"))

    def handle(self, *args, **options):
        self.errors_found = False
        self.auto_prefix = "_auto_"

        wipe = options['wipe']
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

        total_objects_to_create = (
            num_problems + num_users + num_algotags +
            num_difftags + num_algothrough + num_diffthrough +
            num_algoproposals + num_diffproposals
        )
        max_algothrough = num_problems * num_algotags
        max_diffthrough = num_problems

        if not settings.DEBUG:
            self.errors_found = True
            raise CommandError("This command should only be run in DEBUG mode. Please set DEBUG=True in your settings.")

        if num_algothrough > max_algothrough:
            self.errors_found = True
            raise CommandError(f"For {num_problems} problems and {num_algotags} algorithm tags can create at most {max_algothrough} algorithm tag through records.")

        if num_diffthrough > max_diffthrough:
            self.errors_found = True
            raise CommandError(f"For {num_problems} problems can create at most {max_diffthrough} difficulty tag through records.")

        if num_algoproposals > 0 and (num_problems <= 0 or num_users <= 0 or num_algotags <= 0):
            self.errors_found = True
            raise CommandError("Creation of algorithm tag proposals requires at least one problem, one user, and one algorithm tag to be created first.")

        if num_diffproposals > 0 and (num_problems <= 0 or num_users <= 0 or num_difftags <= 0):
            self.errors_found = True
            raise CommandError("Creation of difficulty tag proposals requires at least one problem, one user, and one difficulty tag to be created first.")

        if wipe:
            self.stdout.write(self.style.WARNING(
                "Wiping all previously generated mock data."
            ))
            self.remove_all_generated_data()

            if total_objects_to_create == 0:
                return
            else:
                self.stdout.write(self.style.SUCCESS(
                    "Wipe complete. Proceeding to create new mock data."
                ))

        if total_objects_to_create == 0:
            self.stdout.write(self.style.WARNING(
                "No objects specified for creation. Please set one or more counts to non-zero. "
                "See --help for usage details."
            ))
            return

        if seed is not None:
            random.seed(seed)

        created_problems = self.create_problems(
            count=num_problems,
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
