from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_delete
from south.modelsinspector import add_introspection_rules, \
    introspection_details


def delete_related_participants_handler(sender, instance, **kwargs):
    try:
        instance.participant.delete()
    except ObjectDoesNotExist:
        # already deleted - nothing to do
        pass


class OneToOneBothHandsCascadingParticipantField(models.OneToOneField):
    def contribute_to_class(self, cls, name):
        super(OneToOneBothHandsCascadingParticipantField, self) \
                .contribute_to_class(cls, name)
        post_delete.connect(delete_related_participants_handler, sender=cls)


for fields, arg, rule in introspection_details:
    if models.OneToOneField in fields:
        add_introspection_rules(
            [(
                [OneToOneBothHandsCascadingParticipantField],
                arg,
                rule
            )],
            [r'^oioioi\.participants\.fields\.'
             'OneToOneBothHandsCascadingParticipantField']
        )
