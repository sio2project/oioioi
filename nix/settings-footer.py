if DEBUG:
    TEMPLATES[0]['OPTIONS']['loaders'] = UNCACHED_TEMPLATE_LOADERS
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    }
else:
    # Cache compiled templates in production environment.
    TEMPLATES[0]['OPTIONS']['loaders'] = CACHED_TEMPLATE_LOADERS

TEMPLATES[0]['APP_DIRS'] = False
TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'oioioi.supervision.processors.supervision_processor',
    'oioioi.notifications.processors.notification_processor',
    'oioioi.globalmessage.processors.global_message_processor'
]

from basic_settings import *
