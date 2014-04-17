# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
            ("contests", "0001_initial"),
            ("participants", "0001_initial"),
    )

    def forwards(self, orm):
        # Adding model 'Team'
        db.create_table(u'teams_team', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('login', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True, primary_key=True)),
            ('contest', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contests.Contest'])),
            ('join_key', self.gf('django.db.models.fields.CharField')(max_length=40)),
        ))
        db.send_create_signal(u'teams', ['Team'])

        # Adding model 'TeamMembership'
        db.create_table(u'teams_teammembership', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('team', self.gf('django.db.models.fields.related.ForeignKey')(related_name='members', to=orm['teams.Team'])),
        ))
        db.send_create_signal(u'teams', ['TeamMembership'])

        # Adding unique constraint on 'TeamMembership', fields ['user', 'team']
        db.create_unique(u'teams_teammembership', ['user_id', 'team_id'])

        # Adding model 'TeamsConfig'
        db.create_table(u'teams_teamsconfig', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contest', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['contests.Contest'], unique=True)),
            ('max_team_size', self.gf('django.db.models.fields.IntegerField')(default=3)),
            ('modify_begin_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('modify_end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'teams', ['TeamsConfig'])


    def backwards(self, orm):
        # Removing unique constraint on 'TeamMembership', fields ['user', 'team']
        db.delete_unique(u'teams_teammembership', ['user_id', 'team_id'])

        # Deleting model 'Team'
        db.delete_table(u'teams_team')

        # Deleting model 'TeamMembership'
        db.delete_table(u'teams_teammembership')

        # Deleting model 'TeamsConfig'
        db.delete_table(u'teams_teamsconfig')


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
        u'teams.team': {
            'Meta': {'object_name': 'Team'},
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.Contest']"}),
            'join_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'login': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'teams.teammembership': {
            'Meta': {'unique_together': "(('user', 'team'),)", 'object_name': 'TeamMembership'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'members'", 'to': u"orm['teams.Team']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'teams.teamsconfig': {
            'Meta': {'object_name': 'TeamsConfig'},
            'contest': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['contests.Contest']", 'unique': 'True'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_team_size': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'modify_begin_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'modify_end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['teams']
