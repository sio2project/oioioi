from oioioi.evalmgr import add_after_placeholder

class SplitEvalContestControllerMixin(object):
    def fill_evaluation_environ(self, environ, submission, **kwargs):
        super(SplitEvalContestControllerMixin,
                self).fill_evaluation_environ(environ, submission, **kwargs)
        environ.setdefault('sioworkers_extra_args', {}) \
            .setdefault('NORMAL', {})['queue'] = 'sioworkers-lowprio'
        try:
            add_after_placeholder(environ, 'after_initial_tests',
                    ('postpone_final',
                        'oioioi.evalmgr.handlers.postpone',
                        dict(queue='evalmgr-lowprio')))
        except IndexError:
            # This may happen if some controller modifies the evaluation
            # environment so that the after_initial_tests label is no more.
            # This happens for OI's test run functionality, among others.
            pass
