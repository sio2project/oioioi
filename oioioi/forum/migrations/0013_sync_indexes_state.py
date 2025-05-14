from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0012_merge_20231222_1900'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name="post",
            index_together=set(),
        ),
        migrations.AddIndex(
            model_name="post",
            index=models.Index(
                fields=['thread', 'add_date'],
                name="forum_post_thread__54acb8_idx"
            ),
        ),
    ]