# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    depends_on = (
            ("contests", "0001_initial"),
    )

    def forwards(self, orm):
        # Adding model 'ContestLogo'
        db.create_table(u'contestlogo_contestlogo', (
            ('contest', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['contests.Contest'], unique=True, primary_key=True)),
            ('logo_url', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'contestlogo', ['ContestLogo'])


    def backwards(self, orm):
        # Deleting model 'ContestLogo'
        db.delete_table(u'contestlogo_contestlogo')


    models = {
        u'contestlogo.contestlogo': {
            'Meta': {'object_name': 'ContestLogo'},
            'contest': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['contests.Contest']", 'unique': 'True', 'primary_key': 'True'}),
            'logo_url': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'contests.contest': {
            'Meta': {'object_name': 'Contest'},
            'controller_name': ('oioioi.base.fields.DottedNameField', [], {'max_length': '255', 'superclass': "'oioioi.contests.controllers.ContestController'"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default_submissions_limit': ('django.db.models.fields.IntegerField', [], {'default': '10', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['contestlogo']
