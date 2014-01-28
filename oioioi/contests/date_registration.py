import datetime

from django.utils.timezone import utc

from oioioi.base.menu import OrderedRegistry


class DateRegistry(object):
    """Maintains a collection of important changeable date fields.
    """
    def __init__(self):
        self._registry = OrderedRegistry()

    class DateItem(object):
        def __init__(self, date_field, name_generator, model):
            self.date_field = date_field
            self.name_generator = name_generator
            self.model = model

    def register(self, date_field, name_generator=None, model=None):
        """Registers a new date item.

           :param date_field: the date's field in the model
           :param name_generator: function taking model's object and returning
                        the name to be displayed with the date.
           :param model: the date's model. If the model is not provided the
                        method returns a decorator.
        """

        def decorator(original_class):
            self.register(date_field, name_generator, original_class)
            return original_class

        if model is None:
            return decorator

        if name_generator is None:
            name_generator = lambda obj: \
                unicode(model._meta.verbose_name) + " " + unicode(model. \
                        _meta.get_field_by_name(date_field)[0].verbose_name)

        date_item = self.DateItem(date_field, name_generator, model)
        self._registry.register(date_item)

    def tolist(self, contest_id):
        """Returns a list of items to pass to a template for rendering."""
        context_items = []
        for item in self._registry:
            model = item.model
            data = model.objects.filter(contest=contest_id).values()
            for record in data:
                context_items.append(dict(
                    text=item.name_generator(record),
                    date=record[item.date_field]))
        return sorted(context_items,
                        key=lambda k: k['date'] if k['date'] is not None \
                        else datetime.datetime.min.replace(tzinfo=utc))

# The default date registry.
date_registry = DateRegistry()
