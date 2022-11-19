import bleach
from django import forms
from django.utils.translation import gettext_lazy as _

from oioioi.dashboard.models import DashboardMessage


class DashboardMessageForm(forms.ModelForm):
    allowed_tags = [
        'a',
        'abbr',
        'acronym',
        'article',
        'b',
        'blockquote',
        'br',
        'center',
        'code',
        'em',
        'font',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'hr',
        'i',
        'img',
        'li',
        'ol',
        'p',
        'strong',
        'table',
        'td',
        'th',
        'tr',
        'u',
        'ul',
    ]

    allowed_attributes = {
        'a': ['href', 'title', 'target'],
        'acronym': ['title'],
        'abbr': ['title'],
        'img': ['src', 'width', 'height'],
        'font': ['color', 'size'],
        'table': ['align'],
    }

    def tag_as_str(self, tag):
        if tag in self.allowed_attributes:
            return '{} ({})'.format(
                tag, ', '.join(sorted(self.allowed_attributes[tag]))
            )
        else:
            return tag

    class Meta(object):
        model = DashboardMessage
        fields = ['content']

    def __init__(self, request, *args, **kwargs):
        super(DashboardMessageForm, self).__init__(*args, **kwargs)
        self.fields['content'].widget.attrs['class'] = 'monospace'
        self.contest = request.contest
        self.fields['content'].help_text = _(
            "You can use the following tags and attributes: {}."
        ).format(', '.join(self.tag_as_str(tag) for tag in sorted(self.allowed_tags)))

    def clean_content(self):
        return bleach.clean(
            self.cleaned_data['content'],
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            strip=True,
        )

    def save(self, commit=True, *args, **kwargs):
        instance = super(DashboardMessageForm, self).save(commit=False, *args, **kwargs)
        instance.contest = self.contest
        if commit:
            instance.save()
        return instance
