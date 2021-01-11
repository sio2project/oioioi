from oioioi.base.admin import AdminSite
from oioioi.base.permissions import make_request_condition
from oioioi.contests.admin import ContestAdmin
from oioioi.contests.models import Contest


# This function cannot be placed in contests/utils.py because Django complains
# that at the moment of importing can_user_create_contest "Models aren't loaded yet."
@make_request_condition
def can_create_contest(request):
    return ContestAdmin(Contest, AdminSite(name='oioioiadmin')).has_add_permission(
        request
    )
