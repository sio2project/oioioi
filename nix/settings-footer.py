if DEBUG:
    TEMPLATES[0]['OPTIONS']['loaders'] = UNCACHED_TEMPLATE_LOADERS
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    }
else:
    # Cache compiled templates in production environment.
    TEMPLATES[0]['OPTIONS']['loaders'] = CACHED_TEMPLATE_LOADERS

MIDDLEWARE += (
    "oioioi.supervision.middleware.supervision_middleware", # needed for supervision
    "oioioi.contests.middleware.CurrentContestMiddleware", # mandatory
)

INSTALLED_APPS = (
    "oioioi.participants",
    "oioioi.testrun",
    "oioioi.scoresreveal",
    "oioioi.confirmations",
    "oioioi.ctimes",
    "oioioi.suspendjudge",
    "oioioi.submitservice",
    "oioioi.timeline",
    "oioioi.statistics",
    "oioioi.notifications",
    "oioioi.globalmessage",
    "oioioi.phase",
    "oioioi.supervision",
    "oioioi.talent",
) + INSTALLED_APPS

TEMPLATES[0]['APP_DIRS'] = False
TEMPLATES[0]['OPTIONS']['context_processors'] += (
    'oioioi.supervision.processors.supervision_processor',
    'oioioi.notifications.processors.notification_processor',
    'oioioi.globalmessage.processors.global_message_processor'
)

SUBMITTABLE_LANGUAGES.pop('Java')
SUBMITTABLE_LANGUAGES.pop('Python')
SUBMITTABLE_EXTENSIONS.pop('Java')
SUBMITTABLE_EXTENSIONS.pop('Python')

from basic_settings import *
