# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ContestIcon'
        db.create_table(u'contestlogo_contesticon', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contest', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.Contest'])),
            ('image', self.gf('oioioi.filetracker.fields.FileField')(max_length=100, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal(u'contestlogo', ['ContestIcon'])

        # Deleting field 'ContestLogo.logo_url'
        db.delete_column(u'contestlogo_contestlogo', 'logo_url')

        # Adding field 'ContestLogo.image'
        db.add_column(u'contestlogo_contestlogo', 'image',
                      self.gf('oioioi.filetracker.fields.FileField')(max_length=100, null=True, blank=True),
                      keep_default=False)

        # Adding field 'ContestLogo.updated_at'
        db.add_column(u'contestlogo_contestlogo', 'updated_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'ContestIcon'
        db.delete_table(u'contestlogo_contesticon')

        # Adding field 'ContestLogo.logo_url'
        db.add_column(u'contestlogo_contestlogo', 'logo_url',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255),
                      keep_default=False)

        # Deleting field 'ContestLogo.image'
        db.delete_column(u'contestlogo_contestlogo', 'image')

        # Deleting field 'ContestLogo.updated_at'
        db.delete_column(u'contestlogo_contestlogo', 'updated_at')


    models = {
        u'contestlogo.contesticon': {
            'Meta': {'object_name': 'ContestIcon'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.Contest']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        u'contestlogo.contestlogo': {
            'Meta': {'object_name': 'ContestLogo'},
            'contest': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['contests.Contest']", 'unique': 'True', 'primary_key': 'True'}),
            'image': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        u'contests.contest': {
            'Meta': {'object_name': 'Contest'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.contests.controllers.ContestController'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default_submissions_limit': ('django.db.models.fields.IntegerField', [], {'default': '10', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['contestlogo']