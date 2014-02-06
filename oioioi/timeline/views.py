import datetime

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.forms.forms import ValidationError
from django.template.response import TemplateResponse
from django.utils import timezone

from oioioi.base.permissions import enforce_condition
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.utils import is_contest_admin, contest_exists
from oioioi.contests.date_registration import date_registry


def _get_date_id(registry_item):
    date_id = unicode(registry_item['model']._meta.verbose_name) + ":" + \
              str(registry_item['id']) + ":" + \
              unicode(registry_item['date_field'])
    return date_id.replace(' ', '_')

@contest_admin_menu_registry.register_decorator(_("Timeline"), lambda request:
        reverse('timeline_view', kwargs={'contest_id': request.contest.id}))
@enforce_condition(contest_exists & is_contest_admin)
def timeline_view(request, contest_id):
    registry = date_registry.tolist(contest_id)

    for item in registry:
        item['date_id'] = _get_date_id(item)

    if request.POST:
        tosave = {}
        error_dict = {}

        for item in registry:
            date = request.POST.get(item['date_id'], None)
            obj = item['model'].objects.get(pk=item['id'])
            if date is None or getattr(obj, item['date_field']) is None:
                continue
            try:
                current_tz = timezone.get_current_timezone()
                parsed_date = current_tz.localize(datetime.datetime.strptime(
                        date, "%Y-%m-%d %H:%M"))
            except ValueError:
                parsed_date = None
                error_dict[unicode(item['text'])] = \
                        {'date_format': [_("Date format is invalid")]}
            if parsed_date is not None:
                item['date'] = parsed_date
                obj_str = unicode(item['model']) + str(item['id'])
                if obj_str in tosave:
                    setattr(tosave[obj_str]['obj'], item['date_field'],
                            parsed_date)
                    tosave[obj_str]['name'] += ", " + unicode(item['text'])
                else:

                    setattr(obj, item['date_field'], parsed_date)
                    tosave[obj_str] = {'obj': obj, 'name': item['text']}

        for item in tosave.values():
            try:
                item['obj'].full_clean()
            except ValidationError as e:
                error_dict[item['name']] = e.message_dict

        if error_dict:
            return TemplateResponse(request, 'timeline/timeline_view.html',
                    {'registry': registry,
                    'error_dict': error_dict})

        for item in tosave.values():
            item['obj'].save()

    return TemplateResponse(request, 'timeline/timeline_view.html',
                {'registry': registry})
