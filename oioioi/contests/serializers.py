from rest_framework import serializers


class SubmissionSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="File with the problem solution. "
        "It should have name which allows "
        "programming language recognition."
    )
    kind = serializers.CharField(
        required=False,
        help_text="It is an advanced parameter determining "
        "submission kind. It usually defaults "
        "to normal and you should not "
        "set it manually.",
    )
    problem_instance = None

    def __init__(self, pi, *args, **kwargs):
        if pi is not None:
            self.problem_instance_id = serializers.HiddenField(default=pi.pk)
        self.problem_instance = pi
        super(SubmissionSerializer, self).__init__(*args, **kwargs)

    def validate(self, data):
        for field in SubmissionSerializer.Meta.fields:
            if data.get(field, None) is None and field in self.__dict__:
                data[field] = self.__dict__[field].default
        return data

    class Meta:
        fields = ('file', 'kind', 'problem_instance_id')
