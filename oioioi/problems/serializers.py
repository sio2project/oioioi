from rest_framework import serializers

from oioioi.base.utils.validators import validate_db_string_id, validate_whitespaces


class PackageSerializer(serializers.Serializer):
    package_file = serializers.FileField(
        allow_empty_file=False,
        use_url=False,
        help_text="Problem package to be uploaded.",
    )


class PackageUploadSerializer(PackageSerializer):
    contest_id = serializers.CharField(
        max_length=32,
        allow_blank=False,
        validators=[validate_db_string_id],
        help_text="Unique contest id. Same as the name in contest's URL.",
    )

    round_name = serializers.CharField(
        max_length=255,
        validators=[validate_whitespaces],
        help_text="Round id string. "
        "Round names are unique in regards to single contest.",
    )


class PackageReuploadSerializer(PackageSerializer):
    problem_id = serializers.IntegerField(
        required=True,
        help_text="Integer id of problem to be reuploaded."
        "Same as value in package reupload form's URL "
        "availble through Contest Administration UI.",
    )
