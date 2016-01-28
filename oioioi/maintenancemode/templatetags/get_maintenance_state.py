from django import template

from oioioi.maintenancemode.models import is_maintenance_mode_enabled
register = template.Library()


@register.assignment_tag
def is_maintenance_enabled():
    return is_maintenance_mode_enabled()
