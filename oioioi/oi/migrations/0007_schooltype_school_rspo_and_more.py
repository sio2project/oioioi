# Generated by Django 4.2.4 on 2023-08-17 10:29

from django.db import migrations, models
import django.db.models.deletion
import oioioi.base.utils.validators
import oioioi.participants.fields


def create_default_school_types(apps, schema_editor):
    names = [
        'Szkoła podstawowa',
        'Liceum ogólnokształcące',
        'Technikum'
    ]
    SchoolType = apps.get_model('oi', 'SchoolType')
    for name in names:
        type = SchoolType(name=name)
        type.save()

class Migration(migrations.Migration):

    dependencies = [
        ('oi', '0006_auto_20210620_1806'),
    ]

    operations = [
        migrations.CreateModel(
            name='SchoolType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, validators=[oioioi.base.utils.validators.validate_whitespaces], verbose_name='name')),
            ],
        ),
        migrations.AddField(
            model_name='school',
            name='rspo',
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='school',
            name='type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='oi.schooltype'),
        ),
        migrations.RunPython(create_default_school_types),
    ]