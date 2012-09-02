# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ExtraConfig'
        db.create_table('sinolpack_extraconfig', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['problems.Problem'], unique=True)),
            ('config', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sinolpack', ['ExtraConfig'])

        # Adding model 'ExtraFile'
        db.create_table('sinolpack_extrafile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['problems.Problem'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('file', self.gf('oioioi.filetracker.fields.FileField')(max_length=100)),
        ))
        db.send_create_signal('sinolpack', ['ExtraFile'])


    def backwards(self, orm):
        # Deleting model 'ExtraConfig'
        db.delete_table('sinolpack_extraconfig')

        # Deleting model 'ExtraFile'
        db.delete_table('sinolpack_extrafile')


    models = {
        'contests.contest': {
            'Meta': {'object_name': 'Contest'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.contests.controllers.ContestController'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'problems.problem': {
            'Meta': {'object_name': 'Problem'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.Contest']", 'null': 'True', 'blank': 'True'}),
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.problems.controllers.ProblemController'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'package_backend_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'null': 'True', 'superclass': "'oioioi.problems.package.ProblemPackageBackend'", 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'sinolpack.extraconfig': {
            'Meta': {'object_name': 'ExtraConfig'},
            'config': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['problems.Problem']", 'unique': 'True'})
        },
        'sinolpack.extrafile': {
            'Meta': {'object_name': 'ExtraFile'},
            'file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['problems.Problem']"})
        }
    }

    complete_apps = ['sinolpack']
