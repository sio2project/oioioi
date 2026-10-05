from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('oi', '0008_schooltype_school_rspo_school_type'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name="school",
            index_together=set(),
        ),
        migrations.AddIndex(
            model_name="school",
            index=models.Index(
                fields=['city', 'is_active'],
                name="oi_school_city_21f890_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="school",
            index=models.Index(
                fields=['province', 'is_active'],
                name="oi_school_provinc_42dc90_idx",
            ),
        ),
    ]