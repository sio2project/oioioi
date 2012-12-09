# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Contest'
        db.create_table('contests_contest', (
            ('id', self.gf('django.db.models.fields.CharField')(max_length=32, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('controller_name', self.gf('oioioi.base.fields.DottedNameField')(max_length=255, superclass='oioioi.contests.controllers.ContestController')),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('contests', ['Contest'])

        # Adding model 'ContestAttachment'
        db.create_table('contests_contestattachment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contest', self.gf('django.db.models.fields.related.ForeignKey')(related_name='attachments', to=orm['contests.Contest'])),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('content', self.gf('oioioi.filetracker.fields.FileField')(max_length=100)),
        ))
        db.send_create_signal('contests', ['ContestAttachment'])

        # Adding model 'Round'
        db.create_table('contests_round', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contest', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.Contest'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('results_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('contests', ['Round'])

        # Adding unique constraint on 'Round', fields ['contest', 'name']
        db.create_unique('contests_round', ['contest_id', 'name'])

        # Adding model 'ProblemInstance'
        db.create_table('contests_probleminstance', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contest', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.Contest'])),
            ('round', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.Round'])),
            ('problem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['problems.Problem'])),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('contests', ['ProblemInstance'])

        # Adding unique constraint on 'ProblemInstance', fields ['contest', 'short_name']
        db.create_unique('contests_probleminstance', ['contest_id', 'short_name'])

        # Adding model 'Submission'
        db.create_table('contests_submission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('problem_instance', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.ProblemInstance'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('kind', self.gf('oioioi.base.fields.EnumField')(default='NORMAL', max_length=64)),
            ('score', self.gf('oioioi.contests.fields.ScoreField')(max_length=255, null=True, blank=True)),
            ('status', self.gf('oioioi.base.fields.EnumField')(default='?', max_length=64)),
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('contests', ['Submission'])

        # Adding model 'SubmissionReport'
        db.create_table('contests_submissionreport', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.Submission'])),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('kind', self.gf('oioioi.base.fields.EnumField')(default='FINAL', max_length=64)),
            ('status', self.gf('oioioi.base.fields.EnumField')(default='INACTIVE', max_length=64)),
        ))
        db.send_create_signal('contests', ['SubmissionReport'])

        # Adding unique constraint on 'SubmissionReport', fields ['submission', 'creation_date']
        db.create_unique('contests_submissionreport', ['submission_id', 'creation_date'])

        # Adding model 'ScoreReport'
        db.create_table('contests_scorereport', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission_report', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.SubmissionReport'])),
            ('status', self.gf('oioioi.base.fields.EnumField')(max_length=64, null=True, blank=True)),
            ('score', self.gf('oioioi.contests.fields.ScoreField')(max_length=255, null=True, blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('contests', ['ScoreReport'])

        # Adding model 'FailureReport'
        db.create_table('contests_failurereport', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission_report', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.SubmissionReport'])),
            ('message', self.gf('django.db.models.fields.TextField')()),
            ('json_environ', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('contests', ['FailureReport'])

        # Adding model 'UserResultForProblem'
        db.create_table('contests_userresultforproblem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('problem_instance', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.ProblemInstance'])),
            ('score', self.gf('oioioi.contests.fields.ScoreField')(max_length=255, null=True, blank=True)),
            ('status', self.gf('oioioi.base.fields.EnumField')(max_length=64, null=True, blank=True)),
        ))
        db.send_create_signal('contests', ['UserResultForProblem'])

        # Adding unique constraint on 'UserResultForProblem', fields ['user', 'problem_instance']
        db.create_unique('contests_userresultforproblem', ['user_id', 'problem_instance_id'])

        # Adding model 'UserResultForRound'
        db.create_table('contests_userresultforround', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('round', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.Round'])),
            ('score', self.gf('oioioi.contests.fields.ScoreField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal('contests', ['UserResultForRound'])

        # Adding unique constraint on 'UserResultForRound', fields ['user', 'round']
        db.create_unique('contests_userresultforround', ['user_id', 'round_id'])

        # Adding model 'UserResultForContest'
        db.create_table('contests_userresultforcontest', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('contest', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.Contest'])),
            ('score', self.gf('oioioi.contests.fields.ScoreField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal('contests', ['UserResultForContest'])

        # Adding unique constraint on 'UserResultForContest', fields ['user', 'contest']
        db.create_unique('contests_userresultforcontest', ['user_id', 'contest_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'UserResultForContest', fields ['user', 'contest']
        db.delete_unique('contests_userresultforcontest', ['user_id', 'contest_id'])

        # Removing unique constraint on 'UserResultForRound', fields ['user', 'round']
        db.delete_unique('contests_userresultforround', ['user_id', 'round_id'])

        # Removing unique constraint on 'UserResultForProblem', fields ['user', 'problem_instance']
        db.delete_unique('contests_userresultforproblem', ['user_id', 'problem_instance_id'])

        # Removing unique constraint on 'SubmissionReport', fields ['submission', 'creation_date']
        db.delete_unique('contests_submissionreport', ['submission_id', 'creation_date'])

        # Removing unique constraint on 'ProblemInstance', fields ['contest', 'short_name']
        db.delete_unique('contests_probleminstance', ['contest_id', 'short_name'])

        # Removing unique constraint on 'Round', fields ['contest', 'name']
        db.delete_unique('contests_round', ['contest_id', 'name'])

        # Deleting model 'Contest'
        db.delete_table('contests_contest')

        # Deleting model 'ContestAttachment'
        db.delete_table('contests_contestattachment')

        # Deleting model 'Round'
        db.delete_table('contests_round')

        # Deleting model 'ProblemInstance'
        db.delete_table('contests_probleminstance')

        # Deleting model 'Submission'
        db.delete_table('contests_submission')

        # Deleting model 'SubmissionReport'
        db.delete_table('contests_submissionreport')

        # Deleting model 'ScoreReport'
        db.delete_table('contests_scorereport')

        # Deleting model 'FailureReport'
        db.delete_table('contests_failurereport')

        # Deleting model 'UserResultForProblem'
        db.delete_table('contests_userresultforproblem')

        # Deleting model 'UserResultForRound'
        db.delete_table('contests_userresultforround')

        # Deleting model 'UserResultForContest'
        db.delete_table('contests_userresultforcontest')


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
        'contests.contestattachment': {
            'Meta': {'object_name': 'ContestAttachment'},
            'content': ('oioioi.filetracker.fields.FileField', [], {'max_length': '100'}),
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': "orm['contests.Contest']"}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contests.failurereport': {
            'Meta': {'object_name': 'FailureReport'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'json_environ': ('django.db.models.fields.TextField', [], {}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'submission_report': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.SubmissionReport']"})
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
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'contests.scorereport': {
            'Meta': {'object_name': 'ScoreReport'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'score': ('oioioi.contests.fields.ScoreField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'status': ('oioioi.base.fields.EnumField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'submission_report': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.SubmissionReport']"})
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
        'contests.userresultforcontest': {
            'Meta': {'unique_together': "(('user', 'contest'),)", 'object_name': 'UserResultForContest'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.Contest']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'score': ('oioioi.contests.fields.ScoreField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'contests.userresultforproblem': {
            'Meta': {'unique_together': "(('user', 'problem_instance'),)", 'object_name': 'UserResultForProblem'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problem_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.ProblemInstance']"}),
            'score': ('oioioi.contests.fields.ScoreField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'status': ('oioioi.base.fields.EnumField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'contests.userresultforround': {
            'Meta': {'unique_together': "(('user', 'round'),)", 'object_name': 'UserResultForRound'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'round': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.Round']"}),
            'score': ('oioioi.contests.fields.ScoreField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'problems.problem': {
            'Meta': {'object_name': 'Problem'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contests.Contest']", 'null': 'True', 'blank': 'True'}),
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.problems.controllers.ProblemController'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'package_backend_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'null': 'True', 'superclass': "'oioioi.problems.package.ProblemPackageBackend'", 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        }
    }

    complete_apps = ['contests']