# Generated by Django 3.2.16 on 2022-12-27 19:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0014_contest_enable_editor'),
        ('scoresreveal', '0005_auto_20211123_1728'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScoreRevealContestConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reveal_limit', models.IntegerField(blank=True, help_text='If empty, all submissions are revealed automatically.', null=True, verbose_name='reveal limit')),
                ('disable_time', models.IntegerField(blank=True, null=True, verbose_name='disable for last minutes of the round')),
                ('contest', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='scores_reveal_config', to='contests.contest', verbose_name='contest')),
            ],
            options={
                'verbose_name': 'score reveal contest config',
                'verbose_name_plural': 'score reveal contest configs',
            },
        ),
    ]