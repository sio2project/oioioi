from django.conf import settings

from oioioi.evalmgr import add_before_placeholder


class SplitEvalContestControllerMixin(object):
    def use_spliteval(self, submission):
        return super(SplitEvalContestControllerMixin, self) \
                .use_spliteval(submission) and settings.ENABLE_SPLITEVAL

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        super(SplitEvalContestControllerMixin,
                self).fill_evaluation_environ(environ, submission, **kwargs)
        if not self.use_spliteval(submission):
            return

        environ.setdefault('sioworkers_extra_args', {}) \
            .setdefault('NORMAL', {})['queue'] = 'sioworkers-lowprio'
        try:
            add_before_placeholder(environ, 'before_final_tests',
                    ('postpone_final',
                        'oioioi.evalmgr.handlers.postpone',
                        dict(queue='evalmgr-lowprio')))
        except IndexError:
            # This may happen if some controller modifies the evaluation
            # environment so that the after_initial_tests label is no more.
            # This happens for OI's test run functionality, among others.
            pass
