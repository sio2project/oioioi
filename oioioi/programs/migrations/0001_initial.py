# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Test'
        db.create_table('programs_test', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['problems.Problem'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('input_file', self.gf('oioioi.filetracker.fields.FileField')(max_length=100, null=True, blank=True)),
            ('output_file', self.gf('oioioi.filetracker.fields.FileField')(max_length=100, null=True, blank=True)),
            ('kind', self.gf('oioioi.base.fields.EnumField')(max_length=64)),
            ('group', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('time_limit', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('memory_limit', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('max_score', self.gf('django.db.models.fields.IntegerField')(default=10)),
        ))
        db.send_create_signal('programs', ['Test'])

        # Adding model 'OutputChecker'
        db.create_table('programs_outputchecker', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['problems.Problem'], unique=True)),
            ('exe_file', self.gf('oioioi.filetracker.fields.FileField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal('programs', ['OutputChecker'])

        # Adding model 'ModelSolution'
        db.create_table('programs_modelsolution', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['problems.Problem'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('source_file', self.gf('oioioi.filetracker.fields.FileField')(max_length=100)),
            ('kind', self.gf('oioioi.base.fields.EnumField')(max_length=64)),
        ))
        db.send_create_signal('programs', ['ModelSolution'])

        # Adding model 'ProgramSubmission'
        db.create_table('programs_programsubmission', (
            ('submission_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['contests.Submission'], unique=True, primary_key=True)),
            ('source_file', self.gf('oioioi.filetracker.fields.FileField')(max_length=100)),
        ))
        db.send_create_signal('programs', ['ProgramSubmission'])

        # Adding model 'ModelProgramSubmission'
        db.create_table('programs_modelprogramsubmission', (
            ('programsubmission_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['programs.ProgramSubmission'], unique=True, primary_key=True)),
            ('model_solution', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['programs.ModelSolution'])),
        ))
        db.send_create_signal('programs', ['ModelProgramSubmission'])

        # Adding model 'CompilationReport'
        db.create_table('programs_compilationreport', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission_report', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.SubmissionReport'])),
            ('status', self.gf('oioioi.base.fields.EnumField')(max_length=64)),
            ('compiler_output', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('programs', ['CompilationReport'])

        # Adding model 'TestReport'
        db.create_table('programs_testreport', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission_report', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.SubmissionReport'])),
            ('status', self.gf('oioioi.base.fields.EnumField')(max_length=64)),
            ('comment', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('score', self.gf('oioioi.contests.fields.ScoreField')(max_length=255, blank=True)),
            ('time_used', self.gf('django.db.models.fields.IntegerField')(blank=True)),
            ('test', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['programs.Test'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('test_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('test_group', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('test_time_limit', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('test_max_score', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('programs', ['TestReport'])

        # Adding model 'GroupReport'
        db.create_table('programs_groupreport', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission_report', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.SubmissionReport'])),
            ('group', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('score', self.gf('oioioi.contests.fields.ScoreField')(max_length=255)),
            ('status', self.gf('oioioi.base.fields.EnumField')(max_length=64)),
        ))
        db.send_create_signal('programs', ['GroupReport'])


    def backwards(self, orm):
        # Deleting model 'Test'
        db.delete_table('programs_test')

        # Deleting model 'OutputChecker'
        db.delete_table('programs_outputchecker')

        # Deleting model 'ModelSolution'
        db.delete_table('programs_modelsolution')

        # Deleting model 'ProgramSubmission'
        db.delete_table('programs_programsubmission')

        # Deleting model 'ModelProgramSubmission'
        db.delete_table('programs_modelprogramsubmission')

        # Deleting model 'CompilationReport'
        db.delete_table('programs_compilationreport')

        # Deleting model 'TestReport'
        db.delete_table('programs_testreport')

        # Deleting model 'GroupReport'
        db.delete_table('programs_groupreport')


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
        'contests.probleminstance': {
            'Meta': {'ordering': "('round', 'short_name')", 'unique_together': "(('contest', 'short_name'),)", 'object_name': 'ProblemInstance'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.Contest']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['problems.Problem']"}),
            'round': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.Round']"}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'contests.round': {
            'Meta': {'ordering': "('contest', 'start_date')", 'unique_together': "(('contest', 'name'),)", 'object_name': 'Round'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.Contest']"}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'results_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'})
        },
        'contests.submission': {
            'Meta': {'object_name': 'Submission'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('oioioi.base.fields.EnumField', [], {'default': "'NORMAL'", 'max_length': '64'}),
            'problem_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.ProblemInstance']"}),
            'score': ('oioioi.contests.fields.ScoreField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'status': ('oioioi.base.fields.EnumField', [], {'default': "'?'", 'max_length': '64'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'contests.submissionreport': {
            'Meta': {'unique_together': "(('submission', 'creation_date'),)", 'object_name': 'SubmissionReport'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('oioioi.base.fields.EnumField', [], {'default': "'FINAL'", 'max_length': '64'}),
            'status': ('oioioi.base.fields.EnumField', [], {'default': "'INACTIVE'", 'max_length': '64'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.Submission']"})
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
        'programs.compilationreport': {
            'Meta': {'object_name': 'CompilationReport'},
            'compiler_output': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('oioioi.base.fields.EnumField', [], {'max_length': '64'}),
            'submission_report': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.SubmissionReport']"})
        },
        'programs.groupreport': {
            'Meta': {'object_name': 'GroupReport'},
            'group': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'score': ('oioioi.contests.fields.ScoreField', [], {'max_length': '255'}),
            'status': ('oioioi.base.fields.EnumField', [], {'max_length': '64'}),
            'submission_report': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.SubmissionReport']"})
        },
        'programs.modelprogramsubmission': {
            'Meta': {'object_name': 'ModelProgramSubmission', '_ormbases': ['programs.ProgramSubmission']},
            'model_solution': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['programs.ModelSolution']"}),
            'programsubmission_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['programs.ProgramSubmission']", 'unique': 'True', 'primary_key': 'True'})
        },
        'programs.modelsolution': {
            'Meta': {'object_name': 'ModelSolution'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('oioioi.base.fields.EnumField', [], {'max_length': '64'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['problems.Problem']"}),
            'source_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'})
        },
        'programs.outputchecker': {
            'Meta': {'object_name': 'OutputChecker'},
            'exe_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['problems.Problem']", 'unique': 'True'})
        },
        'programs.programsubmission': {
            'Meta': {'object_name': 'ProgramSubmission', '_ormbases': ['contests.Submission']},
            'source_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'}),
            'submission_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['contests.Submission']", 'unique': 'True', 'primary_key': 'True'})
        },
        'programs.test': {
            'Meta': {'object_name': 'Test'},
            'group': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'kind': ('oioioi.base.fields.EnumField', [], {'max_length': '64'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'memory_limit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'output_file': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'problem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['problems.Problem']"}),
            'time_limit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'programs.testreport': {
            'Meta': {'object_name': 'TestReport'},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'score': ('oioioi.contests.fields.ScoreField', [], {'max_length': '255', 'blank': 'True'}),
            'status': ('oioioi.base.fields.EnumField', [], {'max_length': '64'}),
            'submission_report': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.SubmissionReport']"}),
            'test': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['programs.Test']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'test_group': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'test_max_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'test_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'test_time_limit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_used': ('django.db.models.fields.IntegerField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['programs']
