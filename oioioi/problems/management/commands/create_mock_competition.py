import random
import re
import string

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import get_language

from oioioi.contests.models import ScoreReport, Submission, SubmissionReport, UserResultForProblem
from oioioi.contests.scores import IntegerScore
from oioioi.problems.models import (
    OriginInfoCategory,
    OriginInfoValue,
    OriginInfoValueLocalization,
    OriginTag,
    OriginTagLocalization,
    Problem,
    ProblemName,
    ProblemSite,
)

# List of 300 random words of length at most 6
# Used for creating problems with "believable" names
WORDS = [
    "Whole",
    "Crime",
    "Eight",
    "Member",
    "Join",
    "Man",
    "Thing",
    "Box",
    "Friend",
    "Piece",
    "Good",
    "Eat",
    "Only",
    "Save",
    "About",
    "Six",
    "Cup",
    "Yeah",
    "Reveal",
    "Whose",
    "Remain",
    "Speak",
    "Card",
    "Entire",
    "Key",
    "When",
    "Sense",
    "Drive",
    "Where",
    "Little",
    "Need",
    "Can",
    "Bit",
    "Never",
    "Coach",
    "Push",
    "Where",
    "Small",
    "Remain",
    "Future",
    "Which",
    "Around",
    "Score",
    "Born",
    "Score",
    "Remain",
    "Thing",
    "Tend",
    "Bit",
    "Tree",
    "Type",
    "Say",
    "Two",
    "Kind",
    "Half",
    "Truth",
    "Occur",
    "Wish",
    "Big",
    "Glass",
    "Just",
    "Hear",
    "Lose",
    "His",
    "Entire",
    "List",
    "Year",
    "Type",
    "Cost",
    "Bank",
    "Hair",
    "Try",
    "Color",
    "Choice",
    "Former",
    "Enough",
    "Task",
    "Fast",
    "Little",
    "Smile",
    "Floor",
    "Only",
    "Fly",
    "Never",
    "Energy",
    "Rise",
    "Or",
    "Recent",
    "Place",
    "Share",
    "Book",
    "Soon",
    "Poor",
    "Tend",
    "Learn",
    "Guess",
    "Eat",
    "Eye",
    "Those",
    "Full",
    "Sing",
    "Data",
    "Me",
    "Charge",
    "Never",
    "Grow",
    "Job",
    "These",
    "Rock",
    "Itself",
    "Until",
    "Seek",
    "Yes",
    "Soon",
    "Break",
    "Follow",
    "Stuff",
    "Good",
    "Side",
    "Sign",
    "Either",
    "Itself",
    "Per",
    "Spring",
    "Ahead",
    "Region",
    "Power",
    "Real",
    "Wife",
    "Radio",
    "Walk",
    "Doctor",
    "Event",
    "Sort",
    "Film",
    "Form",
    "Under",
    "Fast",
    "Range",
    "Mrs",
    "Bring",
    "Ago",
    "Matter",
    "Oil",
    "Change",
    "A",
    "Help",
    "Baby",
    "Whom",
    "Own",
    "Loss",
    "Debate",
    "Seek",
    "Sport",
    "Wife",
    "Read",
    "Court",
    "Land",
    "Reason",
    "Wrong",
    "Report",
    "Garden",
    "Use",
    "Film",
    "Avoid",
    "Worker",
    "Civil",
    "Assume",
    "Our",
    "First",
    "Color",
    "Girl",
    "Second",
    "Year",
    "Window",
    "Past",
    "Kind",
    "Change",
    "She",
    "Within",
    "Page",
    "Action",
    "Road",
    "Leader",
    "Late",
    "Really",
    "Here",
    "Far",
    "Minute",
    "Sense",
    "Coach",
    "Play",
    "Return",
    "Quite",
    "Author",
    "Fill",
    "Attack",
    "Thing",
    "Option",
    "Choose",
    "This",
    "Bit",
    "Should",
    "Result",
    "Rate",
    "Dog",
    "Push",
    "Early",
    "Upon",
    "Data",
    "For",
    "Mother",
    "Poor",
    "Nor",
    "Reason",
    "Pretty",
    "Take",
    "Room",
    "Live",
    "Design",
    "See",
    "Center",
    "Better",
    "Unit",
    "Thus",
    "Town",
    "Space",
    "End",
    "Act",
    "Today",
    "Weight",
    "They",
    "Young",
    "Mr",
    "Reason",
    "Easy",
    "Affect",
    "Soon",
    "Thing",
    "Maybe",
    "Learn",
    "Often",
    "Agree",
    "Become",
    "Lose",
    "There",
    "Rock",
    "Heavy",
    "Though",
    "Space",
    "Total",
    "Base",
    "Glass",
    "Visit",
    "Form",
    "Team",
    "Choice",
    "Much",
    "Behind",
    "Room",
    "Data",
    "Family",
    "Hour",
    "North",
    "Fly",
    "Right",
    "Remain",
    "White",
    "They",
    "Report",
    "There",
    "Song",
    "Focus",
    "Cover",
    "Within",
    "Then",
    "Board",
    "Her",
    "Yeah",
    "Last",
    "By",
    "Change",
    "Push",
    "That",
    "Will",
    "About",
    "Until",
    "Fire",
    "Apply",
    "Big",
    "Fish",
    "Have",
    "Choice",
    "Fund",
    "Radio",
    "Upon",
    "Around",
    "There",
    "Have",
    "Apply",
]


# Helper command, which finds the smallest natural number n, such that
# no object from the model model_class has a field equal to [base_value]n.
# This function is to be used for finding anyname that isn't
# used in the database yet.
def get_unique_field_value(model_class, field_name, base_value):
    filter_kwargs = {f"{field_name}__startswith": base_value}

    existing_vals = model_class.objects.filter(**filter_kwargs).values_list(field_name, flat=True)

    unused = 0
    regex_pattern = base_value + r"(\d+)"
    for value in existing_vals:
        # Try to convert to number
        try:
            # Find the integer after base_value in the field
            num = int(re.search(regex_pattern, value).group(1))
            # Make sure unused is different than num
            unused = max(unused, num + 1)
        except ValueError:
            pass

    return base_value + str(unused)


def create_origin_tag(competition_name):
    """Create an OriginTag for the competition_name with the name it is given or
    a unique name starting with 'mock'
    """
    if competition_name is not None:
        # Disallow duplicate origin tags, and raise an exception
        if OriginTag.objects.filter(name=competition_name).exists():
            raise Exception(f"An origin_tag with competition name '{competition_name}' already exists, choose a non-duplicate name for the competition.")
    else:
        # Find a unique name of the form 'mock%d'
        competition_name = get_unique_field_value(OriginTag, "name", "mock")

    # Create top-level origin tag for the competition.
    origin_tag = OriginTag(name=competition_name)
    origin_tag.save()

    # Assign the name ot_name for the competiton for the default language.
    OriginTagLocalization(origin_tag=origin_tag, language=get_language(), short_name=competition_name, full_name=competition_name).save()

    return origin_tag


def create_origin_info_categories(origin_tag, levels):
    """Create an OriginInfoCategory for each level described by levels"""
    categories = []
    for level in range(len(levels)):
        category = OriginInfoCategory(parent_tag=origin_tag, name=f"level{level}", order=level)
        category.save()
        categories.append(category)

    return categories


RESULT_KINDS = ["pass", "partial", "fail"]


def choose_results(problems, group_count):
    """Choose the problems that get a result and the kind of each result.

    The problems are split into group_count groups of equal size. There is at
    least one result of each kind, results in at least two groups, and at
    least one problem without a result.
    """
    # One result of each kind, plus a random number of random ones, but
    # never as many as there are problems.
    results_count = random.randint(len(RESULT_KINDS), len(problems) - 1)
    kinds = RESULT_KINDS + [random.choice(RESULT_KINDS) for _ in range(results_count - len(RESULT_KINDS))]
    random.shuffle(kinds)

    # recurse() returns the problems depth-first, so the groups of each level
    # are contiguous slices. Take one problem from each of two random groups.
    group_size = len(problems) // group_count
    groups = [problems[i : i + group_size] for i in range(0, len(problems), group_size)]
    chosen = [random.choice(group) for group in random.sample(groups, 2)]

    # Distribute the rest of the results randomly.
    chosen += random.sample([p for p in problems if p not in chosen], results_count - len(chosen))

    return list(zip(chosen, kinds, strict=True))


def create_mock_problem(with_instances):
    """Create a problem with a random name and an empty problem site."""
    words = [random.choice(WORDS), random.choice(WORDS)]
    problem_name = "Problem {} {} {}".format(words[0], words[1], "".join(random.choices(string.digits, k=6)))
    # The short name will be the first word in lower case
    short_name = words[0].lower()
    if with_instances:
        p = Problem.create(short_name=short_name, controller_name="oioioi.problems.controllers.ProblemController")
    else:
        p = Problem(short_name=short_name)

    name = ProblemName(problem=p, language=get_language(), name=problem_name)

    p.save()
    name.save()

    # Assign an empty fake problem site for a problem.
    # Use a random ID large enough, that the Birthday Paradox won't be a problem
    ProblemSite(problem=p, url_key=str(random.randrange(2**40))).save()

    return p


def get_results_user(options):
    """Validate "--results-for" and return its user, or None if it was not given."""
    if options["user"] is None:
        return None
    if not options["with_instances"]:
        raise CommandError('You must run with "--with-instances" when using "--results-for".')
    if options["branches"] < 1 or (options["branches"] < 2 and options["levels"] < 2):
        raise CommandError('"--results-for" needs at least 2 branches or 2 levels, so that the results are in several groups.')
    try:
        return User.objects.get(username=options["user"])
    except User.DoesNotExist:
        raise CommandError(f"User '{options['user']}' does not exist.")


def populate_mock_results(problems, levels, user):
    """Create results for user on some of the problems, spread over the groups of the first level that branches."""
    group_count = next(n for n in levels if n > 1)
    for problem, kind in choose_results(problems, group_count):
        populate_results(problem.main_problem_instance, user, kind)


def populate_results(problem_instance, user, kind):
    if kind == "pass":
        score = 100
    elif kind == "partial":
        score = random.randint(1, 99)
    else:
        score = 0
    status = "OK" if score == 100 else "WA"

    sub = Submission(
        problem_instance=problem_instance,
        user=user,
        score=IntegerScore(score),
        max_score=IntegerScore(100),
        status=status,
    )
    sub.save()

    sub_report = SubmissionReport(submission=sub, kind="FINAL", status="ACTIVE")
    sub_report.save()

    ScoreReport(
        submission_report=sub_report,
        status=status,
        score=IntegerScore(score),
        max_score=IntegerScore(100),
    ).save()

    UserResultForProblem(user=user, problem_instance=problem_instance, score=IntegerScore(score), status=status, submission_report=sub_report).save()


def create_origin_info_values(origin_tag, levels, categories):
    """Create levels[level] values for each category"""
    info_values = [[] for i in range(len(levels))]
    for level in range(len(levels)):
        for i in range(levels[level]):
            # Create an OriginInfoValue for each branch in the current level
            info_value = OriginInfoValue(
                value=f"{level}_{i}",
                parent_tag=origin_tag,
                category=categories[level],
            )
            info_value.save()
            info_values[level].append(info_value)

            # Name the OriginInfoValue in the default language
            localization = OriginInfoValueLocalization(origin_info_value=info_value, language=get_language(), full_value=f"Level {level} - {i}")
            localization.save()

    return info_values


class Command(BaseCommand):
    help = (
        "Create a mock competition with empty problems. "
        "Useful for replicating the size of the production databse in the local environment. "
        "This can be used for finding performance bottlenecks, "
        "where the number of queries grows with the number of problems in the database. "
        "WARNING: this operation will fill your database with a lot of rubbish data. "
        "Only use it if you're sure that's not a problem, or use 'python manage.py dumpdata' "
        "and 'python manage.py loaddata'."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-b",
            "--branches",
            type=int,
            action="store",
            dest="branches",
            required=True,
            default=10,
            help="Number of top-level branches of the competition tree. Conceptually, this is the number of stages of the competition.",
        )

        parser.add_argument(
            "-n",
            "--name",
            type=str,
            action="store",
            dest="competition_name",
            help="Name of the mock competition which will be created. If a competition with this name already exists, an error will be thrown. "
            "If not specified, the name will be 'mock{N}', where N is the smallest number, "
            "such that no competition of with this name already exists.",
        )

        parser.add_argument("-l", "--levels", type=int, action="store", dest="levels", default=2, help="Number of levels of nesting of the competition.")

        parser.add_argument("-s", "--seed", type=int, action="store", dest="seed", help="Random seed to use for problem name randomization.")

        parser.add_argument(
            "--with-instances",
            action="store_true",
            dest="with_instances",
            help="Give each problem a controller and a main problem instance, so that its problem page can be opened.",
        )

        parser.add_argument(
            "--results-for",
            type=str,
            action="store",
            dest="user",
            metavar="USERNAME",
            help="Create random results for a subset of the problems for the given user: at least one full, partial and zero score, "
            "in at least two groups, and at least one problem without a result. "
            "Requires --with-instances and at least 2 branches or 2 levels.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["seed"] is not None:
            random.seed(options["seed"])

        # Array of branching factors for each level of the tree of problems.
        levels = [1]
        levels.append(options["branches"])
        levels += [3] * (options["levels"] - 1)

        with_instances = options["with_instances"]
        results_user = get_results_user(options)

        PROBLEMS_PER_LEAF = 3

        origin_tag = create_origin_tag(options["competition_name"])
        categories = create_origin_info_categories(origin_tag, levels)
        info_values = create_origin_info_values(origin_tag, levels, categories)

        # Recursive function for creating problem. It traverses the tree of
        # problems depth-first and returns all the problems in its subtree.
        def recurse(level, name):
            problems = []

            if level == len(levels):
                # Reached bottom level - create problems
                for _i in range(PROBLEMS_PER_LEAF):
                    p = create_mock_problem(with_instances)
                    problems.append(p)

                    # Add the problem to the competition origin tag.
                    origin_tag.problems.add(p)
                return problems
            else:
                for i in range(levels[level]):
                    subname = f"{name}_{i}"
                    # Recurse for each of levels[level] branches
                    subproblems = recurse(level + 1, subname)

                    problems += subproblems

                    # Assign each of the subproblems in the current branch to the
                    # corresponding info_value
                    info_value = info_values[level][i]
                    for p in subproblems:
                        info_value.problems.add(p)

            return problems

        problems = recurse(0, "")

        if results_user is not None:
            populate_mock_results(problems, levels, results_user)
