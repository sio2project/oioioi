from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ('contests', '0020_contest_school_year'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name="contestview",
            index_together=set(),
        ),
        migrations.AddIndex(
            model_name="contestview",
            index=models.Index(
                fields=['user', 'timestamp'],
                name="contests_co_user_id_9b1d73_idx"
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
                name="contests_su_submiss_4331a6_idx"
            ),
        ),
    ]
