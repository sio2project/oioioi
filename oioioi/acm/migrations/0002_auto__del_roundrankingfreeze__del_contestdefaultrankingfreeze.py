# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'RoundRankingFreeze'
        db.delete_table(u'acm_roundrankingfreeze')

        # Deleting model 'ContestDefaultRankingFreeze'
        db.delete_table(u'acm_contestdefaultrankingfreeze')


    def backwards(self, orm):
        # Adding model 'RoundRankingFreeze'
        db.create_table(u'acm_roundrankingfreeze', (
            ('frozen_ranking_minutes', self.gf('django.db.models.fields.IntegerField')(default=60)),
            ('round', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['contests.Round'], unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'acm', ['RoundRankingFreeze'])

        # Adding model 'ContestDefaultRankingFreeze'
        db.create_table(u'acm_contestdefaultrankingfreeze', (
            ('frozen_ranking_minutes', self.gf('django.db.models.fields.IntegerField')(default=60)),
            ('contest', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['contests.Contest'], unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'acm', ['ContestDefaultRankingFreeze'])


    models = {
        
    }

    complete_apps = ['acm']