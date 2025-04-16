from django.template.base import Variable
from django.template import TemplateSyntaxError

class StrictVariable(Variable):
    def resolve(self, context):
        try:
            return super().resolve(context)
        except KeyError:
            raise TemplateSyntaxError(f"Undefined variable: '{self.var}'")
