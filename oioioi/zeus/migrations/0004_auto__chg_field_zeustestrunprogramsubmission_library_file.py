# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'ZeusTestRunProgramSubmission.library_file'
        db.alter_column(u'zeus_zeustestrunprogramsubmission', 'library_file', self.gf('oioioi.filetracker.fields.FileField')(max_length=100, null=True))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'ZeusTestRunProgramSubmission.library_file'
        raise RuntimeError("Cannot reverse this migration. 'ZeusTestRunProgramSubmission.library_file' and its values cannot be restored.")

        # The following code is provided here to aid in writing a correct migration
        # Changing field 'ZeusTestRunProgramSubmission.library_file'
        db.alter_column(u'zeus_zeustestrunprogramsubmission', 'library_file', self.gf('oioioi.filetracker.fields.FileField')(max_length=100))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'contests.contest': {
            'Meta': {'object_name': 'Contest'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.contests.controllers.ContestController'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'default_submissions_limit': ('django.db.models.fields.IntegerField', [], {'default': '10', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'contests.probleminstance': {
            'Meta': {'ordering': "('round', 'short_name')", 'unique_together': "(('contest', 'short_name'),)", 'object_name': 'ProblemInstance'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.Contest']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['problems.Problem']"}),
            'round': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.Round']", 'null': 'True', 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'submissions_limit': ('django.db.models.fields.IntegerField', [], {'default': '10', 'blank': 'True'})
        },
        u'contests.round': {
            'Meta': {'ordering': "('contest', 'start_date')", 'unique_together': "(('contest', 'name'),)", 'object_name': 'Round'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.Contest']"}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_trial': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'results_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        u'contests.submission': {
            'Meta': {'object_name': 'Submission'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('oioioi.base.fields.EnumField', [], {'default': "'NORMAL'", 'max_length': '64'}),
            'problem_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.ProblemInstance']"}),
            'score': ('oioioi.contests.fields.ScoreField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'status': ('oioioi.base.fields.EnumField', [], {'default': "'?'", 'max_length': '64'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'contests.submissionreport': {
            'Meta': {'ordering': "('-creation_date',)", 'object_name': 'SubmissionReport', 'index_together': "(('submission', 'creation_date'),)"},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('oioioi.base.fields.EnumField', [], {'default': "'FINAL'", 'max_length': '64'}),
            'status': ('oioioi.base.fields.EnumField', [], {'default': "'INACTIVE'", 'max_length': '64'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.Submission']"})
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
        u'programs.programsubmission': {
            'Meta': {'object_name': 'ProgramSubmission', '_ormbases': [u'contests.Submission']},
            'source_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'}),
            'source_length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'submission_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['contests.Submission']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'testrun.testrunprogramsubmission': {
            'Meta': {'object_name': 'TestRunProgramSubmission', '_ormbases': [u'programs.ProgramSubmission']},
            'input_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'}),
            u'programsubmission_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['programs.ProgramSubmission']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'testrun.testrunreport': {
            'Meta': {'object_name': 'TestRunReport'},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'output_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'}),
            'status': ('oioioi.base.fields.EnumField', [], {'max_length': '64'}),
            'submission_report': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.SubmissionReport']"}),
            'test_time_limit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_used': ('django.db.models.fields.IntegerField', [], {'blank': 'True'})
        },
        u'zeus.zeusasyncjob': {
            'Meta': {'object_name': 'ZeusAsyncJob'},
            'check_uid': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'environ': ('django.db.models.fields.TextField', [], {}),
            'kind': ('oioioi.base.fields.EnumField', [], {'max_length': '64'})
        },
        u'zeus.zeusfetchseq': {
            'Meta': {'object_name': 'ZeusFetchSeq'},
            'next_seq': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'zeus_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'primary_key': 'True'})
        },
        u'zeus.zeusproblemdata': {
            'Meta': {'object_name': 'ZeusProblemData'},
            'problem': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['problems.Problem']", 'unique': 'True', 'primary_key': 'True'}),
            'zeus_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'zeus_problem_id': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'zeus.zeustestrunprogramsubmission': {
            'Meta': {'object_name': 'ZeusTestRunProgramSubmission', '_ormbases': [u'testrun.TestRunProgramSubmission']},
            'library_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100', 'null': 'True'}),
            u'testrunprogramsubmission_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['testrun.TestRunProgramSubmission']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'zeus.zeustestrunreport': {
            'Meta': {'object_name': 'ZeusTestRunReport', '_ormbases': [u'testrun.TestRunReport']},
            'full_out_handle': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'full_out_size': ('django.db.models.fields.IntegerField', [], {}),
            u'testrunreport_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['testrun.TestRunReport']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['zeus']
