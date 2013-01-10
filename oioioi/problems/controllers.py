from oioioi.base.utils import RegisteredSubclassesBase, ObjectWithMixins

class ProblemController(RegisteredSubclassesBase, ObjectWithMixins):

    modules_with_subclasses = ['controllers']
    abstract = True

    def __init__(self, problem):
        self.problem = problem

    def fill_evaluation_environ(self, environ, **kwargs):
        """Fills a minimal environment with evaluation receipt and other values
           required by the evaluation machinery.

           Passed ``environ`` should already contain entries for the actiual
           data to be judged (for example the source file to evaluate).

           Details on which keys need to be present should be specified by
           particular subclasses.

           As the result, ``environ`` will be filled at least with a suitable
           evaluation ``recipe``.
        """
        raise NotImplementedError

    def adjust_problem(self):
        """Called whan a (usually new) problem has just got the controller
           attached or after the problem has been modified.
        """
        pass

    def mixins_for_admin(self):
        """Returns an iterable of mixins to add to the default
           :class:`oioioi.problems.admin.ProblemAdmin` for
           this particular problem.

           The default implementation returns an empty tuple.
        """
        return ()
