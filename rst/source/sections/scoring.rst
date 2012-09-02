===================
Representing scores
===================

Scores may be very different things, based on the rules of the competition.
They may be simple numbers, like in
:class:`~oioioi.contests.scores.IntegerScore` or substantially more complex
things, like these used for ACM competitions --
:class:`~oioioi.acm.scores.ACMScore`.

Storing scores in models
------------------------

To store a score in a model field, use
:class:`oioioi.contests.fields.ScoreField`, for example::

    from django.db import models
    from oioioi.contests.fields import ScoreField
    from oioioi.contests.models import SubmissionReport

    class ScoreReport(models.Model):
        submission_report = models.ForeignKey(SubmissionReport)
        score = ScoreField()

You cannot then assign primitive types, like ``int`` directly, but you can use
score types::

    from oioioi.contests.scores import IntegerScore

    report = ScoreReport(...)
    report.score = IntegerScore(2)

    # It's also ok to directly assign a serialized value, if you really know
    # what you're doing:
    serialized_score = IntegerScore(2).serialize()
    ...
    report.score = serialized_score

All score types support at least comparison, addition and human-readable
conversion to :py:class:`unicode` type.

In database they are represented by ``VARCHAR`` columns built from the actual
class :attr:`~oioioi.contests.scores.ScoreValue.symbol` and serialized data
returned by :meth:`~oioioi.contests.scores.ScoreValue.to_repr`.

Reference
---------

.. autoclass:: oioioi.contests.scores.ScoreValue
    :members: symbol, serialize, deserialize, _to_repr, _from_repr,
              __add__, __cmp__, __unicode__

.. autoclass:: oioioi.contests.scores.IntegerScore
    :members:

.. rem autoclass:: oioioi.contests.fields.ACMScore
    :members:
