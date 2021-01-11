from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _

validate_origintag = RegexValidator(
    r'^[0-9a-z-]+$',
    _("Enter a valid name consisting only of lowercase letters, numbers, and hyphens."),
)
