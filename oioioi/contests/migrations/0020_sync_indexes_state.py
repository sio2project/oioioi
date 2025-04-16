from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0019_submissionmessage'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterIndexTogether(
                    name="contestview",
                    index_together=set(),
                ),
                migrations.AddIndex(
                    model_name="contestview",
                    index=models.Index(
                        fields=['user', 'timestamp'],
                        name="contests_contestview_user_id_timestamp_a0151775_idx",
                    ),
                ),
                migrations.AlterIndexTogether(
                    name="submissionreport",
                    index_together=set(),
                ),
                migrations.AddIndex(
                    model_name="submissionreport",
                    index=models.Index(
                        fields=['submission', 'creation_date'],
                        name="contests_submissionrepor_submission_id_creation_d_df45e5ee_idx",
                    ),
                ),
            ]
        )
    ]