from oioioi.programs.controllers import ProgrammingContestController
from oioioi.publicsolutions.utils import get_public_solutions


class PublicSolutionsContestControllerMixin(object):

    def can_see_publicsolutions(self, request, round):
        """Determines whether solutions for the round have been published.

           :rtype: bool
        """
        return False

    def solutions_must_be_public(self, qs):
        """This fuction takes for a parameter a queryset
           with submissions for published rounds.

           It should return a filtered queryset with exactly these submissions
           for which solution is mandatorily public.
        """
        return qs.none()

    def solutions_may_be_published(self, qs):
        """This fuction takes for a parameter a queryset
           with submissions for published rounds.

           It should return a filtered queryset with exactly these submissions
           that a user can decide themself to (un)publish.

           You can assume that none of given submissions meets
           :meth:'solutions_must_be_public' predicate.

           At the start these submission are unpublished.
        """
        return qs.none()

    def filter_visible_sources(self, request, queryset):
        subs = get_public_solutions(request)
        prev = super(PublicSolutionsContestControllerMixin, self) \
                    .filter_visible_sources(request, queryset)
        return (prev | (subs & queryset)).distinct()

ProgrammingContestController.mix_in(PublicSolutionsContestControllerMixin)
