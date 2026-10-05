# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import oioioi.base.utils.validators
import oioioi.participants.fields


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0001_initial'),
        ('contests', '0002_auto_20141219_1346'),
    ]

    operations = [
        migrations.CreateModel(
            name='OIOnsiteRegistration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(verbose_name='number')),
                ('local_number', models.IntegerField(verbose_name='local number')),
                ('participant', oioioi.participants.fields.OneToOneBothHandsCascadingParticipantField(related_name='oi_oionsiteregistration', to='participants.Participant', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OIRegistration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.CharField(max_length=255, verbose_name='address')),
                ('postal_code', models.CharField(max_length=6, verbose_name='postal code', validators=[django.core.validators.RegexValidator(b'^\\d{2}-\\d{3}$', 'Enter a postal code in the format XX-XXX')])),
                ('city', models.CharField(max_length=100, verbose_name='city')),
                ('phone', models.CharField(blank=True, max_length=64, null=True, verbose_name='phone number', validators=[django.core.validators.RegexValidator(b'\\+?[0-9() -]{6,}', 'Invalid phone number')])),
                ('birthday', models.DateField(verbose_name='birth date')),
                ('birthplace', models.CharField(max_length=255, verbose_name='birthplace')),
                ('t_shirt_size', models.CharField(max_length=7, verbose_name='t-shirt size', choices=[(b'S', b'S'), (b'M', b'M'), (b'L', b'L'), (b'XL', b'XL'), (b'XXL', b'XXL')])),
                ('class_type', models.CharField(max_length=7, verbose_name='class', choices=[(b'1LO', b'pierwsza szko\xc5\x82y ponadgimnazjalnej'), (b'2LO', b'druga szko\xc5\x82y ponadgimnazjalnej'), (b'3LO', b'trzecia szko\xc5\x82y ponadgimnazjalnej'), (b'4LO', b'czwarta szko\xc5\x82y ponadgimnazjalnej'), (b'1G', b'pierwsza gimnazjum'), (b'2G', b'druga gimnazjum'), (b'3G', b'trzecia gimnazjum'), (b'1SP', b'pierwsza szko\xc5\x82y podstawowej'), (b'2SP', b'druga szko\xc5\x82y podstawowej'), (b'3SP', b'trzecia szko\xc5\x82y podstawowej'), (b'4SP', b'czwarta szko\xc5\x82y podstawowej'), (b'5SP', b'pi\xc4\x85ta szko\xc5\x82y podstawowej'), (b'6SP', b'sz\xc3\xb3sta szko\xc5\x82y podstawowej')])),
                ('terms_accepted', models.BooleanField(default=False, verbose_name='terms accepted')),
                ('participant', oioioi.participants.fields.OneToOneBothHandsCascadingParticipantField(related_name='oi_oiregistration', to='participants.Participant', on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('short_name', models.CharField(max_length=10, validators=[django.core.validators.RegexValidator(re.compile(b'^[a-z0-9_-]+$'), "Enter a valid 'slug' consisting of lowercase letters, numbers, underscores or hyphens.", b'invalid')])),
                ('name', models.CharField(max_length=255)),
                ('contest', models.ForeignKey(to='contests.Contest', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='School',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='name', validators=[oioioi.base.utils.validators.validate_whitespaces])),
                ('address', models.CharField(max_length=255, verbose_name='address')),
                ('postal_code', models.CharField(db_index=True, max_length=6, verbose_name='postal code', validators=[django.core.validators.RegexValidator(b'^\\d{2}-\\d{3}$', 'Enter a postal code in the format XX-XXX')])),
                ('city', models.CharField(max_length=100, verbose_name='city', db_index=True)),
                ('province', models.CharField(db_index=True, max_length=100, verbose_name='province', choices=[('dolno\u015bl\u0105skie', 'dolno\u015bl\u0105skie'), ('kujawsko-pomorskie', 'kujawsko-pomorskie'), ('lubelskie', 'lubelskie'), ('lubuskie', 'lubuskie'), ('\u0142\xf3dzkie', '\u0142\xf3dzkie'), ('ma\u0142opolskie', 'ma\u0142opolskie'), ('mazowieckie', 'mazowieckie'), ('opolskie', 'opolskie'), ('podkarpackie', 'podkarpackie'), ('podlaskie', 'podlaskie'), ('pomorskie', 'pomorskie'), ('\u015bl\u0105skie', '\u015bl\u0105skie'), ('\u015bwi\u0119tokrzyskie', '\u015bwi\u0119tokrzyskie'), ('warmi\u0144sko-mazurskie', 'warmi\u0144sko-mazurskie'), ('wielkopolskie', 'wielkopolskie'), ('zachodniopomorskie', 'zachodniopomorskie')])),
                ('phone', models.CharField(blank=True, max_length=64, null=True, verbose_name='phone number', validators=[django.core.validators.RegexValidator(b'\\+?[0-9() -]{6,}', 'Invalid phone number')])),
                ('email', models.EmailField(max_length=75, verbose_name='email', blank=True)),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('is_approved', models.BooleanField(default=True, verbose_name='approved')),
            ],
            options={
                'ordering': ['province', 'city', 'address', 'name'],
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='school',
            unique_together=set([('name', 'postal_code')]),
        ),
        migrations.AlterUniqueTogether(
            name='region',
            unique_together=set([('contest', 'short_name')]),
        ),
        migrations.AddField(
            model_name='oiregistration',
            name='school',
            field=models.ForeignKey(verbose_name='school', to='oi.School', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='oionsiteregistration',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='region', to='oi.Region', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='oionsiteregistration',
            unique_together=set([('region', 'local_number')]),
        ),
    ]
