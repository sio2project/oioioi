from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from oioioi.forum.models import Ban, Post, Thread


class PostForm(forms.ModelForm):
    class Meta(object):
        model = Post
        fields = ['content']

    def __init__(self, request, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['content'].widget.attrs['class'] = 'monospace'

    def is_valid(self):
        valid = super(PostForm, self).is_valid()
        if not valid:
            return valid
        if len(self.cleaned_data['content']) > getattr(settings, 'FORUM_POST_MAX_LENGTH', 20000):
            self.add_error('content', _('Post is too long'))
            return False
        return True


class NewThreadForm(forms.ModelForm):
    class Meta(object):
        model = Thread
        fields = ['name']

    content = forms.CharField(widget=forms.Textarea, required=True)

    def __init__(self, request, *args, **kwargs):
        super(NewThreadForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = _("Topic")
        self.fields['name'].widget.attrs['class'] = 'monospace'
        self.fields['content'].widget.attrs['class'] = 'monospace'


class BanForm(forms.ModelForm):
    class Meta(object):
        model = Ban
        fields = ['reason']

    delete_reports = forms.BooleanField(
        widget=forms.CheckboxInput(), label=_("Remove user reports"), required=False
    )

    def __init__(self, *args, **kwargs):
        super(BanForm, self).__init__(*args, **kwargs)
        self.fields['reason'].label = _("Reason")
        self.fields['reason'].widget.attrs['class'] = 'monospace'


class ReportForm(forms.ModelForm):
    class Meta(object):
        model = Post
        fields = ['report_reason']

    def __init__(self, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)
        self.fields['report_reason'].label = _("Reason")
        self.fields['report_reason'].widget.attrs['class'] = 'monospace non-resizable'
