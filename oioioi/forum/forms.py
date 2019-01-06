from django import forms
from django.utils.translation import ugettext_lazy as _

from oioioi.forum.models import Post, Thread, Ban


class PostForm(forms.ModelForm):
    class Meta(object):
        model = Post
        fields = ['content']

    def __init__(self, request, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['content'].widget.attrs['class'] = \
                'input-xxlarge monospace'


class NewThreadForm(forms.ModelForm):
    class Meta(object):
        model = Thread
        fields = ['name']

    content = forms.CharField(widget=forms.Textarea, required=True)

    def __init__(self, request, *args, **kwargs):
        super(NewThreadForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = _("Topic")
        self.fields['name'].widget.attrs['class'] = 'input-xxlarge monospace'
        self.fields['content'].widget.attrs['class'] = \
                'input-xxlarge monospace'


class BanForm(forms.ModelForm):
    class Meta(object):
        model = Ban
        fields = ['reason']

    delete_reports = forms.BooleanField(widget=forms.CheckboxInput(),
                                        label=_("Remove user reports"),
                                        required=False)

    def __init__(self, *args, **kwargs):
        super(BanForm, self).__init__(*args, **kwargs)
        self.fields['reason'].label = _("Reason")
        self.fields['reason'].widget.attrs['class'] = 'input-xxlarge monospace'
