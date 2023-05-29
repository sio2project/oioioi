from django.contrib.admin import SimpleListFilter
from django.db.models import Case, F, Subquery, When
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from oioioi.problems.models import ProblemName


class ProblemNameListFilter(SimpleListFilter):
    title = _("problem")
    parameter_name = 'pi'

    def lookups(self, request, model_admin):
        # Match legacy problem names with localized problem names, if the translated
        # name in the currently chosen language exists. Otherwise, use legacy problem
        # name twice.
        matched_problem_names = list(
            self.initial_query_manager.annotate(pi_contest=self.contest_field)
            .filter(pi_contest=(request.contest.id if request.contest else None))
            .prefetch_related(self.related_names)
            .annotate(problem_legacy_name=self.legacy_name_field)
            .annotate(
                problem_localized_name=Subquery(
                    ProblemName.objects.filter(
                        problem=self.outer_ref, language=get_language()
                    ).values('name')
                )
            )
            .annotate(
                problem_display_name=Case(
                    When(
                        problem_localized_name__isnull=True,
                        then=F('problem_legacy_name'),
                    ),
                    default=F('problem_localized_name'),
                )
            )
            .values_list('problem_legacy_name', 'problem_display_name')
        )

        # Uniquefy matches by legacy names.
        matched_problem_names_unique = {
            legacy_name: display_name
            for legacy_name, display_name in matched_problem_names
        }

        return sorted(
            [
                (legacy_name, display_name)
                for legacy_name, display_name in matched_problem_names_unique.items()
            ],
            key=lambda matched_names: matched_names[1].lower(),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.annotate(problem_legacy_name=self.legacy_name_field).filter(
                problem_legacy_name=self.value()
            )
        else:
            return queryset
