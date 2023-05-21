import sys

from oioioi.base.menu import OrderedRegistry


class DateRegistry(object):
    """Maintains a collection of important changeable date fields."""

    def __init__(self):
        self._registry = OrderedRegistry()

    class DateItem(object):
        def __init__(self, date_field, name_generator, round_chooser, qs_filter, model):
            self.date_field = date_field
            self.name_generator = name_generator
            self.round_chooser = round_chooser
            self.qs_filter = qs_filter
            self.model = model

    def register(
        self,
        date_field,
        name_generator=None,
        round_chooser=None,
        qs_filter=None,
        model=None,
        order=sys.maxsize,
    ):
        """Registers a new date item.

        :param date_field: the date's field in the model
        :param name_generator: function taking model's object and returning
                     the name to be displayed with the date.
        :param round_chooser: function taking model's object and returning
                     the round it belongs to.
        :param qs_filter: function taking a (queryset, contest id)
                     pair and returning a queryset limited to
                     instances related to the contest.
        :param model: the date's model. If the model is not provided the
                     method returns a decorator for a model.
        :param order: the date's order. The lower the order, the higher the
                     priority of the date.
        """

        def decorator(original_class):
            self.register(
                date_field,
                name_generator,
                round_chooser,
                qs_filter,
                original_class,
                order,
            )
            return original_class

        def none_returner(obj):
            return None

        def default_name_generator(obj):
            return str(model._meta.verbose_name) + " " + str(model._meta.get_field(date_field).verbose_name)

        if model is None:
            return decorator

        if name_generator is None:
            name_generator = default_name_generator

        if round_chooser is None:
            round_chooser = none_returner

        if qs_filter is None:
            def qs_filter(qs, contest_id):
                return qs.filter(contest=contest_id)

        date_item = self.DateItem(
            date_field, name_generator, round_chooser, qs_filter, model
        )
        self._registry.register(date_item, order)

    def tolist(self, contest_id):
        """Returns a list of items to pass to a template for rendering."""
        context_items = []
        for idx, item in enumerate(self._registry):
            model = item.model
            instances = item.qs_filter(model.objects.all(), contest_id)
            for instance in instances:
                context_items.append(
                    dict(
                        text=item.name_generator(instance),
                        date=getattr(instance, item.date_field),
                        date_field=item.date_field,
                        model=model,
                        id=instance.id,
                        round=item.round_chooser(instance),
                        order=self._registry.keys[idx],
                    )
                )
        return context_items


# The default date registry.
date_registry = DateRegistry()
