from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("oi", "0009_sync_indexes_state"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "DROP TABLE IF EXISTS oi_oionsiteregistration CASCADE",
                "DROP TABLE IF EXISTS oi_region CASCADE",
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
