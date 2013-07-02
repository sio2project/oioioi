from django import forms
from django.utils.translation import ugettext_lazy as _
from oioioi.forum.models import Post, Thread


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content']

    def __init__(self, request, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields['content'].widget.attrs['class'] = 'input-xxlarge monospace'


class NewThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ['name']

    content = forms.CharField(widget=forms.Textarea, required=True)

    def __init__(self, request, *args, **kwargs):
        super(NewThreadForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = _("Topic")
        self.fields['name'].widget.attrs['class'] = 'input-xxlarge monospace'
        self.fields['content'].widget.attrs['class'] = 'input-xxlarge monospace'
