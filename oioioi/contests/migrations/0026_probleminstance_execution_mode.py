from django.db import migrations

import oioioi.base.fields


class Migration(migrations.Migration):

    dependencies = [
        ("contests", "0025_merge_0017_submission_max_score_0024_roundstartdelay"),
    ]

    operations = [
        migrations.AddField(
            model_name="probleminstance",
            name="execution_mode",
            field=oioioi.base.fields.EnumField(
                default="AUTO",
                help_text="If set to Auto, the execution mode is determined according to the contest or problem type.",
                max_length=64,
                verbose_name="execution mode",
            ),
        ),
    ]
