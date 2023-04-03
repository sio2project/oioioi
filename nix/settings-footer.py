if DEBUG:
    TEMPLATES[0]['OPTIONS']['loaders'] = UNCACHED_TEMPLATE_LOADERS
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    }
else:
    # Cache compiled templates in production environment.
    TEMPLATES[0]['OPTIONS']['loaders'] = CACHED_TEMPLATE_LOADERS
    INSTALLED_APPS.remove('debug_toolbar')
    MIDDLEWARE.remove('debug_toolbar.middleware.DebugToolbarMiddleware')

TEMPLATES[0]['APP_DIRS'] = False
TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'oioioi.supervision.processors.supervision_processor',
    'oioioi.notifications.processors.notification_processor',
    'oioioi.globalmessage.processors.global_message_processor'
]
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

from basic_settings import *
