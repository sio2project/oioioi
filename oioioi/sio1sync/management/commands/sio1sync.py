# pylint: disable=W0601
# Global variable '%s' undefined at the module level
import logging
import logging.config
import time
import MySQLdb
import ConfigParser

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import LocalTimezone
from django.utils.dateparse import parse_datetime

from oioioi.contests.models import Contest, Round, ProblemInstance
from oioioi.problems.models import Problem
from oioioi.programs.models import ProgramSubmission

from optparse import make_option
from registration.models import RegistrationProfile


def get_sio1_user(sio1_user_id):
    """Returns dict with user's (sio1_user_id) data in SIO 1"""

    sql = 'SELECT login, first_name, last_name, e_mail, pass \
            FROM users WHERE id = %s'

    sync_env['sioCursor'].execute(sql, (sio1_user_id,))
    result = sync_env['sioCursor'].fetchone()

    return {'username': result[0], 'first_name': result[1].decode('latin2'),
            'last_name': result[2].decode('latin2'), 'email': result[3],
            'password': result[4]}


def sync_user(sio1_user):
    """Sync user (sio1_user) to SIO2 unless such user already exists.
       Returns corresponding SIO2 User object.
    """

    try:
        sio2_user = User.objects.get(username=sio1_user['username'])
        if sio1_user['first_name'] != sio2_user.first_name or \
           sio1_user['last_name'] != sio2_user.last_name:
            logger.warning("User already exists, but names differ."
                           " SIO1: (%(login1)s, %(fname1)s %(lname1)s),"
                           " SIO2: (%(login2)s, %(fname2)s %(lname2)s)",
                           {'login1': sio1_user['username'],
                            'fname1': sio1_user['first_name'],
                            'lname1': sio1_user['last_name'],
                            'login2': sio2_user.username,
                            'fname2': sio2_user.first_name,
                            'lname2': sio2_user.last_name})
        else:
            logger.debug("User (%(login)s, %(fname)s %(lname)s) exists.",
                         {'login': sio2_user.username,
                          'fname': sio2_user.first_name,
                          'lname': sio2_user.last_name})

    except User.DoesNotExist:
        sio2_user = User.objects.create_user(sio1_user['username'],
                                             sio1_user['email'], '')
        sio2_user.first_name = sio1_user['first_name']
        sio2_user.last_name = sio1_user['last_name']
        sio2_user.password = sio1_user['password']
        sio2_user.is_active = True
        sio2_user.save()

        reg_profile = RegistrationProfile.objects.create_profile(sio2_user)
        reg_profile.activation_key = RegistrationProfile.ACTIVATED
        reg_profile.save()

        logger.info("User (%(login)s, %(fname)s %(lname)s) synced.",
                    {'login': sio2_user.username,
                     'fname': sio2_user.first_name,
                     'lname': sio2_user.last_name})

    return sio2_user


def get_sio1_users_ids():
    """Returns list of id's of all non-blocked users in sio1."""

    sql = 'SELECT id FROM users WHERE pass is not NULL AND (user_type = 0 \
            OR user_type = 1 OR user_type = 1000)'
    sync_env['sioCursor'].execute(sql)
    return [x[0] for x in sync_env['sioCursor'].fetchall()]


def get_sio1_participants_ids():
    """Returns list of id's of all participants (in sio1_contest)."""

    sql = 'SELECT user FROM participants WHERE contest = %s'
    sync_env['sioCursor'].execute(sql, (sync_env['sio1_contest'], ))
    return [x[0] for x in sync_env['sioCursor'].fetchall()]


def sync_users(sio1_users_ids):
    """Sync all users on sio1_users_ids list."""

    for uid in sio1_users_ids:
        sio1_user = get_sio1_user(uid)
        sync_user(sio1_user)


def get_sio1_submissions_ids(sio1_submission_type=1):
    """Returns list of id's of all non-synced submissions in sio1, that
       respond to one of sync_env['problems']
    """

    if not sync_env['problems']:
        return []

    sql = 'SELECT id FROM submits WHERE in_sio2 = 0 AND task' \
          ' IN (' + ', '.join(y for (x, y) in sync_env['problems']) + ')' \
          ' AND type = %s'

    sync_env['sioCursor'].execute(sql, (sio1_submission_type))
    return [x[0] for x in sync_env['sioCursor'].fetchall()]


def sync_submission(sio1_submission_id):
    """Sync submission (sio1_submission_id) to SIO2."""

    sql = 'SELECT s.task, s.user, s.date, s.data, b.body FROM submits as s,' \
          ' submits_bodies as b WHERE s.id = b.id AND b.id = %s'

    sync_env['sioCursor'].execute(sql, (sio1_submission_id,))

    sio1_problem_id, sio1_user_id, sio1_date, sio1_filename, sio1_source \
        = sync_env['sioCursor'].fetchone()

    problem_id = sync_env['reversed_problems'][str(sio1_problem_id)]
    problem = Problem.objects.get(id=problem_id)
    c = Contest.objects.get(id=sync_env['sio2_contest'])
    r = Round.objects.get(name=sync_env['sio2_round'])

    pi = ProblemInstance.objects.get(problem=problem, contest=c, round=r)

    sio1_user = get_sio1_user(sio1_user_id)
    sio2_user = sync_user(sio1_user)

    submission_file = ContentFile(sio1_source, name=sio1_filename)
    sio1_date = parse_datetime(str(sio1_date)).replace(tzinfo=LocalTimezone())

    submission = ProgramSubmission(user=sio2_user, problem_instance=pi)
    submission.source_file.save(sio1_filename, submission_file)
    submission.date = sio1_date
    submission.save()
    c.controller.judge(submission)

    sql = 'UPDATE submits SET in_sio2 = %s WHERE id = %s'
    sync_env['sioCursor'].execute(sql, (submission.id, sio1_submission_id))

    logger.info("Submission (id: %(id1)s, u: %(login)s, p: %(pshortname)s)"
                " synced to SIO2 (id: %(id2)s).",
                {'id1': sio1_submission_id, 'login': sio1_user['username'],
                 'pshortname': pi.short_name, 'id2': submission.id})


def sync_submissions():
    """Every wait_time seconds try to sync new submissions."""

    while True:
        new_submits = get_sio1_submissions_ids()
        new_submits.sort()
        logger.info(new_submits)
        for s in new_submits:
            sync_submission(s)

        time.sleep(int(sync_env['wait_time']))


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--participants',
                    action='store_true',
                    dest='participants',
                    default=False,
                    help='Sync all participants'),
        make_option('--all-users',
                    action='store_true',
                    dest='users',
                    default=False,
                    help='Sync all users'),
        make_option('--no-submissions',
                    action='store_true',
                    dest='no-submissions',
                    default=False,
                    help='Do not sync submissions')
    )

    args = 'config_file.conf'
    help = "Utility to synchronize users accounts and submissions to SIO2.\n" \
           "Requires a configuration file that contains problems mapping\n" \
           "and ids of contests and rounds in both systems. See example:\n\n" \
           " oioioi/sio1sync/sio1sync.conf.example\n\n" \
           "Works with SIO1 with in_sio2 column in submits table (v031)."

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Missing argument (configuration file)")

        global logger
        logging.config.fileConfig(args[0])
        logger = logging.getLogger('sio1sync')

        cfg = ConfigParser.ConfigParser()
        cfg.read(args[0])

        sio1_dbconf = dict((k, v) for k, v in cfg.items('sio1db'))

        sio1_db = MySQLdb.connect(host=sio1_dbconf['host'],
                                  user=sio1_dbconf['user'],
                                  passwd=sio1_dbconf['pass'],
                                  db=sio1_dbconf['name'],
                                  use_unicode=False)

        sio1_db.autocommit(True)
        sioCursor = sio1_db.cursor()
        sioCursor.execute('SET NAMES latin1')

        problems = cfg.items('problems')
        reversed_problems = dict((s1_id, s2_id) for s2_id, s1_id in problems)

        global sync_env
        sync_env = dict(cfg.items('sync'))
        sync_env.update({'sioCursor': sioCursor, 'problems': problems,
                         'reversed_problems': reversed_problems})

        if options['users']:
            sync_users(get_sio1_users_ids())

        if options['participants']:
            sync_users(get_sio1_participants_ids())

        if not options['no-submissions']:
            sync_submissions()
