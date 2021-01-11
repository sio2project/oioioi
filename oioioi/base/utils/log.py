import logging


class OmitSentryFilter(logging.Filter):
    """
    A logging filter that checks for existence of omit_sentry field in the
    record-to-be-logged to decide whether to log a record.
    """

    def filter(self, record):
        if hasattr(record, 'omit_sentry') and record.omit_sentry:
            return 0
        return 1
