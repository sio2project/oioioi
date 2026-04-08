from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0021_testreport_result_percentage_denominator_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupreport',
            name='score_affected_by_dependency',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='groupreport',
            name='dependency_prereqs',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
