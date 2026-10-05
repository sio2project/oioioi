from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0021_testreport_result_percentage_denominator_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='testreport',
            name='mem_used',
            field=models.IntegerField(blank=True, default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='testreport',
            name='test_mem_limit',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
