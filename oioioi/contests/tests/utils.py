from oioioi.contests.models import ContestPermission

def make_user_contest_admin(user, contest):
    cp = ContestPermission()
    cp.user = user
    cp.permission = 'contests.contest_admin'
    cp.contest = contest
    cp.save()

    contest.refresh_from_db()
