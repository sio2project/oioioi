# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    depends_on = (
        ("problems", "0003_auto__add_field_problem_package_backend_name"),
        ("contests", "0003_auto__add_field_contest_default_submissions_limit__add_field_problemin"),
    )

    def forwards(self, orm):
        # Adding model 'ZeusProblemData'
        db.create_table(u'zeus_zeusproblemdata', (
            ('problem', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['problems.Problem'], unique=True, primary_key=True)),
            ('zeus_id', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('zeus_problem_id', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'zeus', ['ZeusProblemData'])


    def backwards(self, orm):
        # Deleting model 'ZeusProblemData'
        db.delete_table(u'zeus_zeusproblemdata')


    models = {
        u'contests.contest': {
            'Meta': {'object_name': 'Contest'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.contests.controllers.ContestController'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'default_submissions_limit': ('django.db.models.fields.IntegerField', [], {'default': '10', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'problems.problem': {
            'Meta': {'object_name': 'Problem'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.Contest']", 'null': 'True', 'blank': 'True'}),
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.problems.controllers.ProblemController'"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'package_backend_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'null': 'True', 'superclass': "'oioioi.problems.package.ProblemPackageBackend'", 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        u'zeus.zeusproblemdata': {
            'Meta': {'object_name': 'ZeusProblemData'},
            'problem': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['problems.Problem']", 'unique': 'True', 'primary_key': 'True'}),
            'zeus_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'zeus_problem_id': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['zeus']
