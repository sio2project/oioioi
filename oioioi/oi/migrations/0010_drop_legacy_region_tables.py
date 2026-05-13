from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("oi", "0009_sync_indexes_state"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "DROP TABLE IF EXISTS oi_oionsiteregistration",
                "DROP TABLE IF EXISTS oi_region",
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
