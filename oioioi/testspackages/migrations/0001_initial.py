# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
            ("problems", "0003_auto__add_field_problem_package_backend_name"),
    )

    def forwards(self, orm):
        # Adding model 'TestsPackage'
        db.create_table(u'testspackages_testspackage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['problems.Problem'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('description', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('package', self.gf('oioioi.filetracker.fields.FileField')(max_length=100, null=True, blank=True)),
            ('publish_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'testspackages', ['TestsPackage'])

        # Adding M2M table for field tests on 'TestsPackage'
        m2m_table_name = db.shorten_name(u'testspackages_testspackage_tests')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('testspackage', models.ForeignKey(orm[u'testspackages.testspackage'], null=False)),
            ('test', models.ForeignKey(orm[u'programs.test'], null=False))
        ))
        db.create_unique(m2m_table_name, ['testspackage_id', 'test_id'])


    def backwards(self, orm):
        # Deleting model 'TestsPackage'
        db.delete_table(u'testspackages_testspackage')

        # Removing M2M table for field tests on 'TestsPackage'
        db.delete_table(db.shorten_name(u'testspackages_testspackage_tests'))


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
        u'programs.test': {
            'Meta': {'ordering': "['order']", 'object_name': 'Test'},
            'group': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'kind': ('oioioi.base.fields.EnumField', [], {'max_length': '64'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'memory_limit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'output_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['problems.Problem']"}),
            'time_limit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'testspackages.testspackage': {
            'Meta': {'object_name': 'TestsPackage'},
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'package': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['problems.Problem']"}),
            'publish_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'tests': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['programs.Test']", 'symmetrical': 'False'})
        }
    }

    complete_apps = ['testspackages']
