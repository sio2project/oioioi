# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Region'
        db.create_table('oi_region', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('contest', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.Contest'])),
        ))
        db.send_create_signal('oi', ['Region'])

        # Adding unique constraint on 'Region', fields ['contest', 'short_name']
        db.create_unique('oi_region', ['contest_id', 'short_name'])

        # Adding model 'School'
        db.create_table('oi_school', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('postal_code', self.gf('django.db.models.fields.CharField')(max_length=6)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('province', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
        ))
        db.send_create_signal('oi', ['School'])

        # Adding model 'OIRegistration'
        db.create_table('oi_oiregistration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.OneToOneField')(related_name='oi_oiregistration', unique=True, to=orm['participants.Participant'])),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('postal_code', self.gf('django.db.models.fields.CharField')(max_length=6)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('birthday', self.gf('django.db.models.fields.DateField')()),
            ('birthplace', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('t_shirt_size', self.gf('django.db.models.fields.CharField')(max_length=7)),
            ('school', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['oi.School'], null=True, on_delete=models.SET_NULL)),
            ('class_type', self.gf('django.db.models.fields.CharField')(max_length=7)),
            ('terms_accepted', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('oi', ['OIRegistration'])

        # Adding model 'OIOnsiteRegistration'
        db.create_table('oi_oionsiteregistration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.OneToOneField')(related_name='oi_oionsiteregistration', unique=True, to=orm['participants.Participant'])),
            ('number', self.gf('django.db.models.fields.IntegerField')(unique=True)),
            ('region', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['oi.Region'], null=True, on_delete=models.SET_NULL)),
            ('local_number', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('oi', ['OIOnsiteRegistration'])

        # Adding unique constraint on 'OIOnsiteRegistration', fields ['region', 'local_number']
        db.create_unique('oi_oionsiteregistration', ['region_id', 'local_number'])


    def backwards(self, orm):
        # Removing unique constraint on 'OIOnsiteRegistration', fields ['region', 'local_number']
        db.delete_unique('oi_oionsiteregistration', ['region_id', 'local_number'])

        # Removing unique constraint on 'Region', fields ['contest', 'short_name']
        db.delete_unique('oi_region', ['contest_id', 'short_name'])

        # Deleting model 'Region'
        db.delete_table('oi_region')

        # Deleting model 'School'
        db.delete_table('oi_school')

        # Deleting model 'OIRegistration'
        db.delete_table('oi_oiregistration')

        # Deleting model 'OIOnsiteRegistration'
        db.delete_table('oi_oionsiteregistration')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'contests.contest': {
            'Meta': {'object_name': 'Contest'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.contests.controllers.ContestController'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'oi.oionsiteregistration': {
            'Meta': {'unique_together': "(('region', 'local_number'),)", 'object_name': 'OIOnsiteRegistration'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'local_number': ('django.db.models.fields.IntegerField', [], {}),
            'number': ('django.db.models.fields.IntegerField', [], {'unique': 'True'}),
            'participant': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'oi_oionsiteregistration'", 'unique': 'True', 'to': "orm['participants.Participant']"}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oi.Region']", 'null': 'True', 'on_delete': 'models.SET_NULL'})
        },
        'oi.oiregistration': {
            'Meta': {'object_name': 'OIRegistration'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'birthday': ('django.db.models.fields.DateField', [], {}),
            'birthplace': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'class_type': ('django.db.models.fields.CharField', [], {'max_length': '7'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'participant': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'oi_oiregistration'", 'unique': 'True', 'to': "orm['participants.Participant']"}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'postal_code': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'school': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oi.School']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            't_shirt_size': ('django.db.models.fields.CharField', [], {'max_length': '7'}),
            'terms_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'oi.region': {
            'Meta': {'unique_together': "(('contest', 'short_name'),)", 'object_name': 'Region'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.Contest']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        'oi.school': {
            'Meta': {'object_name': 'School'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'postal_code': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'province': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        'participants.participant': {
            'Meta': {'unique_together': "(('contest', 'user'),)", 'object_name': 'Participant'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.Contest']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('oioioi.base.fields.EnumField', [], {'default': "'ACTIVE'", 'max_length': '64'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['oi']