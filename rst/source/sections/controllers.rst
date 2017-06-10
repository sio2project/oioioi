===========
Controllers
===========

The main purpose of controllers is implementing various rules. Below are
described the three main types of controllers used for contests and problems.
Every contest and problem use its own controller. If you want to implement
your own controller, you should derive from base problem or contest
controller class: :class:`~oioioi.problems.controllers.ProblemController` and
:class:`~oioioi.contests.controllers.ContestController`. For a short overview,
please read their summaries described below. Moreover, you can use already
defined :doc:`mixins </sections/mixins>`. Also, please pay attention to
a special controller:
:class:`~oioioi.contests.problem_instance_controller.ProblemInstanceController`.

An :ref:`example` of custom controller can be found below.

More types of controllers usually live in ``controllers.py`` file in the root
directory of some :doc:`OIOIOI Modules </sections/modules>`.


Problem controller
------------------

.. autoclass:: oioioi.problems.controllers.ProblemController
    :members:


Contest controller
------------------

.. autoclass:: oioioi.contests.controllers.ContestController
    :members:


Problem instance controller
---------------------------

.. autoclass:: oioioi.contests.problem_instance_controller.ProblemInstanceController
    :members:

.. _example:

Example
-------

Let's say there are too many ``e`` characters in English language, so we
dislike them. We want a problem controller which will check if the submitted
source code contains no more than ``MAX_E_COUNT`` ``e`` characters::

    class MaxEProblemController(ProblemController):
        """Checks if a source code is cool."""

        def validate_source_code_coolness(self, problem_instance, source_code):
            if source_code.count('e') >= MAX_E_COUNT:
                raise ValidationError(
                    "Too much letters 'e' found in source code!")
            return source_code

Now, we have a cool problem controller. We want to use it in some contest!
But wait... We love undervalued ``z`` letters. Let's create a contest
controller which checks if the source code contains at least ``MIN_Z_COUNT``
``z`` letters::

    class MinZContestController(ContestController):
        """Checks if a source code is even cooler."""

        def validate_source_code_coolness(self, problem_instance, source_code):
            # Note that here is a call to problem controller
            source_code = problem_instance.problem.controller \
                .validate_source_code_coolness(request, problem_instance,
                                               source_code)
            if source_code.count('z') <= MIN_Z_COUNT:
                raise ValidationError(
                    "Too few letters 'z' found in source code!")
            return source_code

The time to bring our great idea to life has come. Let's say we have a view
which uses the following form::

    class SuperCoolForm(forms.Form):

        # ...

        def clean_source_code(self):
            try:
                pi = ProblemInstance.objects.get(
                    id=self.cleaned_data['problem_instance_id'])
            except ProblemInstance.DoesNotExists:
                pass  # handle error in a better way!
            return pi.validate_source_code_coolness(
                pi, self.cleaned_data['source_code'])

Let's break down how it works:

1. A user submits a submission.

2. The view calls the form which calls the
   :class:`~oioioi.contests.problem_instance_controller.ProblemInstanceController`.

3. Next:
  * If the submission was submitted to a problem instance without an attached
    contest, then
    :class:`~oioioi.contests.problem_instance_controller.ProblemInstanceController`
    calls the ``MaxEProblemController``, so we have only one validation -
    for letter ``e``.

  * If the submission was submitted to a problem instance with an attached
    contest, then
    :class:`~oioioi.contests.problem_instance_controller.ProblemInstanceController`
    calls the ``MinZContestController``, so we have two validations -
    for letter ``z`` which checks our contest controller. Moreover, it calls
    the ``MaxEProblemController``, so we have also validation for letter
    ``e``, too.

Notes:

* You can both define new methods and override existing methods.

* Outside the controllers you should call the
  :class:`~oioioi.contests.problem_instance_controller.ProblemInstanceController`.
  Please read the class summary if you haven't done it yet.

* Controllers are in power only if you assign them to given problem
  or contest.
