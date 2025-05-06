import random
import string
import sys

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from oioioi.problems.models import Problem, AlgorithmTag, AlgorithmTagProposal

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
        "Creates mock problems, users, algorithm tags, and algorithm tag proposals for benchmarking. "
        "Defaults for all counts are 0. If you specify a positive number of proposals, "
        "you must also have >0 problems, users, and algorithm tags. "
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
            '--algorithmtags', '-at',
            type=int,
            default=0,
            metavar='N',
            help='Number of algorithm tags to create (default: 0)'
        )
        parser.add_argument(
            '--proposals', '-ap',
            type=int,
            default=0,
            metavar='N',
            help='Number of algorithm tag proposals to create (default: 0)'
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
        - candidate_prefix: A prefix string (e.g. 'auto_prob_').
        - random_length: Number of random characters to append.
        - uniqueness_fn: Function taking candidate -> bool (should return True if candidate is unique).
        - create_instance_fn: Function taking candidate -> instance (which should be saved later).
        - verbose_name: A description used in output.
        - verbosity: The current verbosity level.
        Returns a list of created objects.
        """
        objs = []
        for i in range(count):
            candidate_fn = lambda: candidate_prefix + ''.join(random.choices(string.ascii_lowercase, k=random_length))
            try:
                unique_candidate = get_unique_candidate(candidate_fn, uniqueness_fn)
            except CommandError as e:
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

    def handle(self, *args, **options):
        num_problems = options['problems']
        num_users = options['users']
        num_tags = options['algorithmtags']
        num_proposals = options['proposals']
        seed = options['seed']
        verbosity = int(options.get('verbosity', 1))

        if seed is not None:
            random.seed(seed)

        # Validate proposals prerequisites
        if num_proposals > 0:
            if num_problems <= 0:
                raise CommandError("Cannot create proposals when number of problems is 0")
            if num_users <= 0:
                raise CommandError("Cannot create proposals when number of users is 0")
            if num_tags <= 0:
                raise CommandError("Cannot create proposals when number of algorithm tags is 0")

        created_problems = []
        created_users = []
        created_tags = []

        # Create Problems with unique short_name (now with 10 random characters)
        for i in range(num_problems):
            candidate_fn = lambda: 'auto_prob_' + ''.join(random.choices(string.ascii_lowercase, k=10))
            try:
                unique_short_name = get_unique_candidate(
                    candidate_fn,
                    lambda s: not Problem.objects.filter(short_name=s).exists()
                )
            except CommandError as e:
                self.stderr.write(self.style.ERROR(
                    f"Failed to create Problem short_name: {e}. Stopping further creation for Problems."
                ))
                break  # stop further problem creation
            p = Problem(short_name=unique_short_name)
            p.save()
            created_problems.append(p)
            if verbosity >= 3:
                self.stdout.write(self.style.SUCCESS(
                    f"Created Problem (ID: {p.id}, short_name: {unique_short_name})"
                ))
            elif verbosity == 2:
                sys.stdout.write(f"Created {i+1} of {num_problems} Problems\r")
                sys.stdout.flush()
        if verbosity == 2 and created_problems:
            sys.stdout.write("\n")

        # Create Users with unique username (using 10 random characters)
        for i in range(num_users):
            candidate_fn = lambda: 'auto_user_' + ''.join(random.choices(string.ascii_lowercase, k=10))
            try:
                unique_username = get_unique_candidate(
                    candidate_fn,
                    lambda s: not User.objects.filter(username=s).exists()
                )
            except CommandError as e:
                self.stderr.write(self.style.ERROR(
                    f"Failed to create User username: {e}. Stopping further creation for Users."
                ))
                break  # stop further user creation
            email = f"{unique_username}@example.com"
            password = "password"
            u = User.objects.create_user(username=unique_username, email=email, password=password)
            created_users.append(u)
            if verbosity >= 3:
                self.stdout.write(self.style.SUCCESS(f"Created User: {unique_username}"))
            elif verbosity == 2:
                sys.stdout.write(f"Created {i+1} of {num_users} Users\r")
                sys.stdout.flush()
        if verbosity == 2 and created_users:
            sys.stdout.write("\n")

        # Create Algorithm Tags with unique name (using 8 random characters)
        for i in range(num_tags):
            candidate_fn = lambda: 'auto_tag_' + ''.join(random.choices(string.ascii_lowercase, k=8))
            try:
                unique_tag_name = get_unique_candidate(
                    candidate_fn,
                    lambda s: not AlgorithmTag.objects.filter(name=s).exists()
                )
            except CommandError as e:
                self.stderr.write(self.style.ERROR(
                    f"Failed to create Algorithm Tag: {e}. Stopping further creation for Algorithm Tags."
                ))
                break  # stop further tag creation
            at = AlgorithmTag(name=unique_tag_name)
            at.save()
            created_tags.append(at)
            if verbosity >= 3:
                self.stdout.write(self.style.SUCCESS(f"Created Algorithm Tag: {unique_tag_name}"))
            elif verbosity == 2:
                sys.stdout.write(f"Created {i+1} of {num_tags} Algorithm Tags\r")
                sys.stdout.flush()
        if verbosity == 2 and created_tags:
            sys.stdout.write("\n")

        # Create Algorithm Tag Proposals by random combination
        # Only proceed if there is data available for these relations
        proposals_created = 0
        if created_problems and created_users and created_tags:
            for i in range(num_proposals):
                problem = random.choice(created_problems)
                user = random.choice(created_users)
                tag = random.choice(created_tags)
                proposal = AlgorithmTagProposal(problem=problem, user=user, tag=tag)
                proposal.save()
                proposals_created += 1
                if verbosity >= 3:
                    self.stdout.write(self.style.SUCCESS(
                        f"Created Proposal: Problem ID {problem.id} - User {user.username} - Tag {tag.name}"
                    ))
                elif verbosity == 2:
                    sys.stdout.write(f"Created {i+1} of {num_proposals} Algorithm Tag Proposals\r")
                    sys.stdout.flush()
            if verbosity == 2 and num_proposals:
                sys.stdout.write("\n")
        else:
            self.stderr.write(self.style.ERROR(
                "Not all prerequisites were created: skipping Algorithm Tag Proposals."
            ))
        
        errors_found = False
        if len(created_problems) != options['problems']:
            errors_found = True
        if len(created_users) != options['users']:
            errors_found = True
        if len(created_tags) != options['algorithmtags']:
            errors_found = True
        if options['proposals'] > 0:
            # Either proposals were skipped or the count didn't match.
            if not (created_problems and created_users and created_tags) or proposals_created != options['proposals']:
                errors_found = True

        def write_summary(created, expected, object_name):
            """
            Prints a summary line for an object type.
            Skips output if expected is 0.
            If created equals expected, it prints a green "Created all ..." message.
            Otherwise, it prints a yellow "Created X of Y ..." message.
            """
            if expected == 0:
                return
            if created == expected:
                msg = f"Created {expected} {object_name}."
                self.stdout.write(self.style.SUCCESS(msg))
            else:
                msg = f"Created {created} of {expected} {object_name}."
                self.stdout.write(self.style.WARNING(msg))

        overall_msg = (
            "Mock data creation complete" if not errors_found
            else "Errors occurred during mock data creation"
        )
        overall_status = self.style.SUCCESS if not errors_found else self.style.ERROR
        self.stdout.write(overall_status(overall_msg))

        if verbosity >= 1:
            write_summary(len(created_problems), options['problems'], "Problems")
            write_summary(len(created_users), options['users'], "Users")
            write_summary(len(created_tags), options['algorithmtags'], "Algorithm Tags")
            if options['proposals'] and (created_problems and created_users and created_tags):
                write_summary(proposals_created, options['proposals'], "Algorithm Tag Proposals")
