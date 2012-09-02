# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Problem'
        db.create_table('problems_problem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('controller_name', self.gf('oioioi.base.fields.DottedNameField')(max_length=255, superclass='oioioi.problems.controllers.ProblemController')),
        ))
        db.send_create_signal('problems', ['Problem'])

        # Adding model 'ProblemStatement'
        db.create_table('problems_problemstatement', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(related_name='statements', to=orm['problems.Problem'])),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=6, null=True, blank=True)),
            ('content', self.gf('oioioi.filetracker.fields.FileField')(max_length=100)),
        ))
        db.send_create_signal('problems', ['ProblemStatement'])

        # Adding model 'ProblemAttachment'
        db.create_table('problems_problemattachment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(related_name='attachments', to=orm['problems.Problem'])),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('content', self.gf('oioioi.filetracker.fields.FileField')(max_length=100)),
        ))
        db.send_create_signal('problems', ['ProblemAttachment'])


    def backwards(self, orm):
        # Deleting model 'Problem'
        db.delete_table('problems_problem')

        # Deleting model 'ProblemStatement'
        db.delete_table('problems_problemstatement')

        # Deleting model 'ProblemAttachment'
        db.delete_table('problems_problemattachment')


    models = {
        'problems.problem': {
            'Meta': {'object_name': 'Problem'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.problems.controllers.ProblemController'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'problems.problemattachment': {
            'Meta': {'object_name': 'ProblemAttachment'},
            'content': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['problems.Problem']"})
        },
        'problems.problemstatement': {
            'Meta': {'object_name': 'ProblemStatement'},
            'content': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'statements'", 'to': "orm['problems.Problem']"})
        }
    }

    complete_apps = ['problems']
