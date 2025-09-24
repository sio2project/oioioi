from django import forms
from django.utils.safestring import mark_safe


class TextInputWithGenerate(forms.TextInput):
    html_template = '<div id={id}>\n   {input_html}\n   <input type="button" value="Generate" />\n</div>'

    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault("attrs", {})
        attrs.setdefault("style", "width:200px;")
        super(TextInputWithGenerate, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        if self.attrs is not None and "id" in self.attrs:
            id = self.attrs.pop("id")
        elif attrs is not None and "id" in attrs:
            id = attrs.pop("id")
        else:
            id = "id"
        id += "_input-with-generate"

        html = super(TextInputWithGenerate, self).render(name, value, attrs, renderer)

        html = mark_safe(self.html_template.format(id=id, input_html=html))
        return html

    class Media:
        js = ("common/ajax-generate-key.js",)
