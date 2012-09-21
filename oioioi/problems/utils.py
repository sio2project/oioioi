def can_add_problems(request):
    return request.user.has_perm('problems.problems_db_admin') \
            or request.user.has_perm('contests.contest_admin',
                    request.contest)
