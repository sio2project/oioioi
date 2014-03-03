# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ("contests", "0003_auto__add_field_contest_default_submissions_limit__add_field_problemin"),
    )

    def forwards(self, orm):
        # Adding model 'StatisticsConfig'
        db.create_table(u'statistics_statisticsconfig', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contest', self.gf('django.db.models.fields.related.OneToOneField')(related_name='statistics_config', unique=True, to=orm['contests.Contest'])),
            ('visible_to_users', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('visibility_date', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal(u'statistics', ['StatisticsConfig'])


    def backwards(self, orm):
        # Deleting model 'StatisticsConfig'
        db.delete_table(u'statistics_statisticsconfig')


    models = {
        u'contests.contest': {
            'Meta': {'object_name': 'Contest'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.contests.controllers.ContestController'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'default_submissions_limit': ('django.db.models.fields.IntegerField', [], {'default': '10', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'statistics.statisticsconfig': {
            'Meta': {'object_name': 'StatisticsConfig'},
            'contest': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'statistics_config'", 'unique': 'True', 'to': u"orm['contests.Contest']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'visibility_date': ('django.db.models.fields.DateTimeField', [], {}),
            'visible_to_users': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['statistics']
