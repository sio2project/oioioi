# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'NotificationsSession'
        db.create_table(u'notifications_notificationssession', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('session', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sessions.Session'], unique=True)),
        ))
        db.send_create_signal(u'notifications', ['NotificationsSession'])


    def backwards(self, orm):
        # Deleting model 'NotificationsSession'
        db.delete_table(u'notifications_notificationssession')


    models = {
        u'notifications.notificationssession': {
            'Meta': {'object_name': 'NotificationsSession'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sessions.Session']", 'unique': 'True'}),
            'uid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        },
        u'sessions.session': {
            'Meta': {'object_name': 'Session', 'db_table': "'django_session'"},
            'expire_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'session_data': ('django.db.models.fields.TextField', [], {}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'})
        }
    }

    complete_apps = ['notifications']