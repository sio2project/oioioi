from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testrun', '0008_auto_20201214_0012'),
    ]

    operations = [
        migrations.AddField(
            model_name='testrunreport',
            name='mem_used',
            field=models.IntegerField(blank=True, default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='testrunreport',
            name='test_mem_limit',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
