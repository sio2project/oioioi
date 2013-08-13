# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    depends_on = (
            ("contests", "0001_initial"),
    )

    def forwards(self, orm):
        # Adding model 'RoundRankingFreeze'
        db.create_table(u'acm_roundrankingfreeze', (
            ('round', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['contests.Round'], unique=True, primary_key=True)),
            ('frozen_ranking_minutes', self.gf('django.db.models.fields.IntegerField')(default=60)),
        ))
        db.send_create_signal(u'acm', ['RoundRankingFreeze'])

        # Adding model 'ContestDefaultRankingFreeze'
        db.create_table(u'acm_contestdefaultrankingfreeze', (
            ('contest', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['contests.Contest'], unique=True, primary_key=True)),
            ('frozen_ranking_minutes', self.gf('django.db.models.fields.IntegerField')(default=60)),
        ))
        db.send_create_signal(u'acm', ['ContestDefaultRankingFreeze'])


    def backwards(self, orm):
        # Deleting model 'RoundRankingFreeze'
        db.delete_table(u'acm_roundrankingfreeze')

        # Deleting model 'ContestDefaultRankingFreeze'
        db.delete_table(u'acm_contestdefaultrankingfreeze')


    models = {
        u'acm.contestdefaultrankingfreeze': {
            'Meta': {'object_name': 'ContestDefaultRankingFreeze'},
            'contest': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['contests.Contest']", 'unique': 'True', 'primary_key': 'True'}),
            'frozen_ranking_minutes': ('django.db.models.fields.IntegerField', [], {'default': '60'})
        },
        u'acm.roundrankingfreeze': {
            'Meta': {'object_name': 'RoundRankingFreeze'},
            'frozen_ranking_minutes': ('django.db.models.fields.IntegerField', [], {'default': '60'}),
            'round': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['contests.Round']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'contests.contest': {
            'Meta': {'object_name': 'Contest'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.contests.controllers.ContestController'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default_submissions_limit': ('django.db.models.fields.IntegerField', [], {'default': '10', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
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
        }
    }

    complete_apps = ['acm']
