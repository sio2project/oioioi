# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    depends_on = (
            ("participants", "0003_auto__add_field_participant_anonymous"),
    )

    def forwards(self, orm):
        for reg in orm.PARegistration.objects.all():
            reg.participant.anonymous = reg.anonymous
            reg.participant.save()

    def backwards(self, orm):
        for reg in orm.PARegistration.objects.all():
            reg.anonymous = reg.participant.anonymous
            reg.save()

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
        u'pa.paregistration': {
            'Meta': {'object_name': 'PARegistration'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.CharField', [], {'max_length': '7'}),
            'job_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'participant': ('oioioi.participants.fields.OneToOneBothHandsCascadingParticipantField', [], {'related_name': "u'pa_paregistration'", 'unique': 'True', 'to': u"orm['participants.Participant']"}),
            'phone': ('oioioi.base.fields.PhoneNumberField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'postal_code': ('oioioi.base.fields.PostalCodeField', [], {'max_length': '6'}),
            't_shirt_size': ('django.db.models.fields.CharField', [], {'max_length': '7'}),
            'terms_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'participants.participant': {
            'Meta': {'unique_together': "(('contest', 'user'),)", 'object_name': 'Participant'},
            'anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'contest': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contests.Contest']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('oioioi.base.fields.EnumField', [], {'default': "'ACTIVE'", 'max_length': '64'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['pa']
    symmetrical = True
