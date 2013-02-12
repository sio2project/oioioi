=========================
Split-Priority Evaluation
=========================

This module allows splitting the evaluation for programming tasks into two
phases: the high priority compilation + initial testing, and low priority
final testing. This way, users can get the initial report faster.

As Celery does not support priorities, another method must have been developed.
To accommodate this, the judging must be configured as follows:

1. Two separate evaluation manager Celery daemons must be run on the server,
   serving 'evalmgr' and 'evalmgr-lowprio' queues, appropriately. This can be
   easily done by setting ``SPLITEVAL_EVALMGR`` to ``True`` in ``settings.py``.

2. Some judging machines should be dedicated to serving only high-priority tasks
   by running the default sio-celery-worker process.

3. Some other judging machines should serve both high- and low-priority tasks
   by running sio-celeryworker with the '-Q sioworkers,sioworkers-lowprio'
   commandline option.

To enable split-priority evaluation, the ContestController attached to the
contest must have :class:`oioioi.spliteval.controllers.SplitEvalContestControllerMixin`
mixed in.
