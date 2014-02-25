# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DashboardMessage'
        db.create_table(u'dashboard_dashboardmessage', (
            ('contest', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['contests.Contest'], unique=True, primary_key=True)),
            ('content', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'dashboard', ['DashboardMessage'])


    def backwards(self, orm):
        # Deleting model 'DashboardMessage'
        db.delete_table(u'dashboard_dashboardmessage')


    models = {
        u'contests.contest': {
            'Meta': {'object_name': 'Contest'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.contests.controllers.ContestController'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default_submissions_limit': ('django.db.models.fields.IntegerField', [], {'default': '10', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'dashboard.dashboardmessage': {
            'Meta': {'object_name': 'DashboardMessage'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'contest': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['contests.Contest']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['dashboard']
