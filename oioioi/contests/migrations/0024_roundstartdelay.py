import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0023_alter_probleminstance_round'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RoundStartDelay',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('delay', models.PositiveIntegerField(verbose_name='Delay (in minutes)')),
                ('round', models.ForeignKey(to='contests.round', on_delete=django.db.models.deletion.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
                'verbose_name': 'round start delay',
                'verbose_name_plural': 'round start delays',
            },
        ),
        migrations.AlterUniqueTogether(
            name='roundstartdelay',
            unique_together={('user', 'round')},
        ),
    ]
