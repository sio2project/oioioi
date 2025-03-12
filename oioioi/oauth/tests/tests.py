import bs4
import os
import re
from datetime import datetime, timedelta, timezone  # pylint: disable=E0611

import pytest
import pytz

from django.conf import settings
from django.contrib.admin.utils import quote
from django.contrib.auth.models import AnonymousUser, User
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.http import HttpResponse
from django.template import RequestContext, Template
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import NoReverseMatch, reverse
from oioioi.base.permissions import is_superuser


