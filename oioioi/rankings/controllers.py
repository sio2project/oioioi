from collections import defaultdict
from operator import itemgetter
import unicodecsv

from django.http import HttpResponse
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from oioioi.base.utils import RegisteredSubclassesBase, ObjectWithMixins
from oioioi.contests.models import ProblemInstance, UserResultForProblem
from oioioi.contests.controllers import ContestController


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

    def render_ranking_to_csv(self, request, key):
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

    def render_ranking_to_csv(self, request, key):
        data = self.serialize_ranking(request, key)

        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = \
            'attachment; filename=%s-%s-%s.csv' % \
            ("ranking", request.contest.id, key)
        writer = unicodecsv.writer(response)

        header = [_("No."), _("First name"), _("Last name")]
        for pi in data['problem_instances']:
            header.append(pi.short_name)
        header.append(_("Sum"))
        writer.writerow(map(force_unicode, header))

        def default_if_none(value, arg):
            if value is None:
                return arg
            return value

        for row in data['rows']:
            line = [row['place'], row['user'].first_name, row['user'].last_name]
            line += [default_if_none(getattr(r, 'score', None), '')
                for r in row['results']]
            line.append(row['sum'])
            writer.writerow(map(force_unicode, line))

        return response

    def filter_users_for_ranking(self, request, key, queryset):
        return queryset.filter(is_superuser=False)

    def serialize_ranking(self, request, key):
        rounds = list(self._rounds_for_ranking(request, key))
        pis = list(ProblemInstance.objects.filter(round__in=rounds))
        users = self.filter_users_for_ranking(request, key, User.objects.all())
        results = UserResultForProblem.objects.filter(problem_instance__in=pis,
                user__in=users)
        by_user = defaultdict(dict)
        for r in results:
            by_user[r.user_id][r.problem_instance_id] = r
        users = users.filter(id__in=by_user.keys())

        data = []
        all_rounds_trial = all(r.is_trial for r in rounds)

        for user in users.order_by('last_name', 'first_name', 'username'):
            by_user_row = by_user[user.id]
            user_results = []
            user_data = {
                    'user': user,
                    'results': user_results,
                    'sum': None
                }

            for pi in pis:
                result = by_user_row.get(pi.id)
                user_results.append(result)
                if result and result.score and \
                    (not pi.round.is_trial or all_rounds_trial):
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
        data.sort(key=itemgetter('sum'), reverse=True)
        prev_sum = None
        place = None
        for i, row in enumerate(data):
            if row['sum'] != prev_sum:
                place = i + 1
                prev_sum = row['sum']
            row['place'] = place

        return {'rows': data, 'problem_instances': pis}
