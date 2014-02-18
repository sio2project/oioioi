# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'ContestIcon.image'
        db.alter_column(u'contestlogo_contesticon', 'image', self.gf('oioioi.filetracker.fields.FileField')(default='', max_length=100))

        # Changing field 'ContestLogo.image'
        db.alter_column(u'contestlogo_contestlogo', 'image', self.gf('oioioi.filetracker.fields.FileField')(default='', max_length=100))

    def backwards(self, orm):

        # Changing field 'ContestIcon.image'
        db.alter_column(u'contestlogo_contesticon', 'image', self.gf('oioioi.filetracker.fields.FileField')(max_length=100, null=True))

        # Changing field 'ContestLogo.image'
        db.alter_column(u'contestlogo_contestlogo', 'image', self.gf('oioioi.filetracker.fields.FileField')(max_length=100, null=True))

    models = {
        u'contestlogo.contesticon': {
            'Meta': {'object_name': 'ContestIcon'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.Contest']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        u'contestlogo.contestlogo': {
            'Meta': {'object_name': 'ContestLogo'},
            'contest': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['contests.Contest']", 'unique': 'True', 'primary_key': 'True'}),
            'image': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        u'contests.contest': {
            'Meta': {'object_name': 'Contest'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.contests.controllers.ContestController'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'default_submissions_limit': ('django.db.models.fields.IntegerField', [], {'default': '10', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['contestlogo']