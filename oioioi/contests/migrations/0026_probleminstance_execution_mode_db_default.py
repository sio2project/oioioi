from django.db import migrations

import oioioi.base.fields


class Migration(migrations.Migration):

    dependencies = [
        ("contests", "0025_probleminstance_execution_mode"),
    ]

    operations = [
        migrations.AlterField(
            model_name="probleminstance",
            name="execution_mode",
            field=oioioi.base.fields.EnumField(
                db_default="AUTO",
                default="AUTO",
                help_text="If set to Auto, the execution mode is determined according to the contest or problem type.",
                max_length=64,
                verbose_name="execution mode",
            ),
        ),
    ]
