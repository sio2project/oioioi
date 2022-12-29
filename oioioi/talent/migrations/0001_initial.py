# -*- coding: utf-8 -*-
from django.db import migrations, models


def change_contest_controllers(apps, schema_editor):
    Contest = apps.get_model('contests', 'Contest')
    for contest in Contest.objects.all():
        if contest.controller_name == 'oioioi.phase.controllers.PhaseOpenContestController':
            contest.controller_name = 'oioioi.talent.controllers.TalentOpenContestController'
        elif contest.controller_name == 'oioioi.phase.controllers.PhaseContestController':
            contest.controller_name = 'oioioi.talent.controllers.TalentContestController'
        contest.save()

class Migration(migrations.Migration):

    dependencies = [
        ('phase', '0002_auto_20171031_2133')
    ]

    operations = [
        migrations.RunPython(change_contest_controllers),
        migrations.CreateModel(
            name='TalentRegistrationSwitch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False,  verbose_name='ID'),),
                ('status', models.BooleanField(default=True, verbose_name='status'),),
            ]
        ),
    ]
