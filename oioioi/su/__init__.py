"""The SU app is used to change the current logged in user on-the-fly.

   In order to achieve this goal, the module introduces concept of *effective*
   and *real* user privileges known from Unix-like systems. The *effective*
   user is stored in ``request.user`` field, while the *real* in
   ``request.real_user``.

   On-the-fly means that current session variables are preserved while changing
   *effective* user, which may be also a pitfall if some code stores
   there data directly connected with current user scope.
"""


SU_UID_SESSION_KEY = 'su_effective_user_id'
SU_BACKEND_SESSION_KEY = 'su_effective_backend'
SU_REAL_USER_IS_SUPERUSER = 'su_real_user_is_superuser'
SU_ORIGINAL_CONTEST = 'su_original_contest'

BLOCKED_URLS = [
    'api_token', 'api_regenerate_key',
    'submitservice_view_user_token', 'submitservice_clear_user_token',
    'edit_profile', 'delete_profile',
    'auth_password_change', 'auth_password_done',
]
BLOCKED_URL_NAMESPACES = ['two_factor', 'oioioiadmin']
