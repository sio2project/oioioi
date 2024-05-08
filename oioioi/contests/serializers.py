from oioioi.contests.models import Contest, ProblemInstance, Round, UserResultForProblem
from rest_framework import serializers
from django.utils.timezone import now


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


class ContestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contest
        fields = ['id', 'name']


class RoundSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Round
        fields = [
            "name",
            "start_date",
            "end_date",
            "is_active",
            "results_date",
            "public_results_date",
            "is_trial",
        ]

    def get_is_active(self, obj: Round):
        if obj.end_date:
            return now() < obj.end_date
        return True


# This is a partial serializer and it serves as a base for the API response.
class ProblemSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProblemInstance
        exclude = ['needs_rejudge', 'problem', 'contest']


class UserResultForProblemSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserResultForProblem
        fields = ['score', 'status']
