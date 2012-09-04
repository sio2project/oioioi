from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from oioioi.base.utils import RegisteredSubclassesBase, ObjectWithMixins
from oioioi.contests.models import ProblemInstance, UserResultForProblem, \
        Round
from oioioi.contests.controllers import ContestController
from collections import defaultdict
from operator import itemgetter

CONTEST_RANKING_KEY = 'c'

class RankingMixinForContestController(object):
    def ranking_controller(self):
        """Return the actual :class:`RankingController` for the contest."""
        return DefaultRankingController(self.contest)
ContestController.mix_in(RankingMixinForContestController)

class RankingController(RegisteredSubclassesBase, ObjectWithMixins):

    modules_with_subclasses = ['controllers']
    abstract = True

    def __init__(self, contest):
        self.contest = contest

    def available_rankings(self, request):
        """Returns a list of available rankings.

           Each ranking is a pair ``(key, description)``.
        """
        raise NotImplementedError

    def render_ranking(self, request, key):
        raise NotImplementedError

    def serialize_ranking(self, request, key):
        raise NotImplementedError

class DefaultRankingController(RankingController):
    description = _("Default ranking")

    def _rounds_for_ranking(self, request, key=CONTEST_RANKING_KEY):
        is_admin = request.user.has_perm('contests.contest_admin',
                request.contest)
        ccontroller = self.contest.controller
        queryset = self.contest.round_set.all()
        if key != CONTEST_RANKING_KEY:
            queryset = queryset.filter(id=key)
        for round in queryset:
            times = ccontroller.get_round_times(request, round)
            if is_admin or times.results_visible(request.timestamp):
                yield round

    def available_rankings(self, request):
        rankings = [(CONTEST_RANKING_KEY, _("Contest"))]
        ccontroller = self.contest.controller
        for round in self._rounds_for_ranking(request):
            rankings.append((str(round.id), round.name))
        if len(rankings) == 1:
            # No rounds have visible results
            return []
        if len(rankings) == 2:
            # Only a single round => call this "contest ranking".
            return rankings[:1]
        return rankings

    def render_ranking(self, request, key):
        data = self.serialize_ranking(request, key)
        return render_to_string('rankings/default_ranking.html',
                context_instance=RequestContext(request, data))

    def serialize_ranking(self, request, key):
        rounds = list(self._rounds_for_ranking(request, key))
        pis = list(ProblemInstance.objects.filter(round__in=rounds))
        results = UserResultForProblem.objects.filter(problem_instance__in=pis)
        by_user = defaultdict(dict)
        for r in results:
            by_user[r.user_id][r.problem_instance_id] = r
        users = User.objects.in_bulk(by_user.keys())

        data = []
        for user in users.itervalues():
            by_user_row = by_user[user.id]
            user_results = []
            user_data = {
                    'user': user,
                    'user_sort_key': (user.last_name, user.first_name,
                        user.id),
                    'results': user_results,
                    'sum': None
                }
            for pi in pis:
                result = by_user_row.get(pi.id)
                user_results.append(result)
                if result and result.score:
                    if user_data['sum'] is None:
                        user_data['sum'] = result.score
                    else:
                        user_data['sum'] += result.score
            if user_data['sum'] is not None:
                # This rare corner case with sum being None may happen if all
                # user's submissions do not have scores (for example the
                # problems do not support scoring, or all the evaluations
                # failed with System Errors).
                data.append(user_data)
        data.sort(key=itemgetter('user_sort_key'))
        data.sort(key=itemgetter('sum'), reverse=True)
        prev_sum = None
        place = None
        for i, row in enumerate(data):
            if row['sum'] != prev_sum:
                place = i + 1
                prev_sum = row['sum']
            row['place'] = place

        return {'rows': data, 'problem_instances': pis}
