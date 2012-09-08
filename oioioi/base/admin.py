from django.template.response import TemplateResponse
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.contrib.admin.util import unquote
from django.contrib.admin.sites import AdminSite as DjangoAdminSite
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django import forms
from django.utils.translation import ugettext_lazy as _
from djcelery.models import TaskState, WorkerState
from djcelery.admin import TaskMonitor, WorkerMonitor
from oioioi.base.utils import ObjectWithMixins, ClassInitMeta
from oioioi.base.menu import MenuRegistry
import urllib

TabularInline = admin.TabularInline
StackedInline = admin.StackedInline

class ModelAdminMeta(forms.MediaDefiningClass, ClassInitMeta):
    pass

class ModelAdmin(admin.ModelAdmin, ObjectWithMixins):
    __metaclass__ = ModelAdminMeta

    # This is handled by AdminSite._reinit_model_admins
    allow_too_late_mixins = True

    def response_change(self, request, obj):
        if '_continue' in request.POST and '_popup' not in request.REQUEST:
            return HttpResponseRedirect(request.get_full_path())
        if 'came_from' in request.GET and '_continue' not in request.POST \
                and '_saveasnew' not in request.POST \
                and '_addanother' not in request.POST:
            return HttpResponseRedirect(request.GET['came_from'])
        return super(ModelAdmin, self).response_change(request, obj)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        response = super(ModelAdmin, self).change_view(request, object_id,
                form_url, extra_context)
        if isinstance(response, TemplateResponse) \
                and 'came_from' in request.GET:
            response.context_data['form_url'] += '?' + \
                    urllib.urlencode({'came_from': request.GET['came_from']})
        return response

    def response_delete(self, request):
        opts = self.model._meta
        if 'came_from' in request.GET:
            return HttpResponseRedirect(request.GET['came_from'])
        if not self.has_change_permission(request, None):
            return HttpResponseRedirect(reverse('admin:index',
                                            current_app=self.admin_site.name))
        return HttpResponseRedirect(reverse('admin:%s_%s_changelist' %
                                    (opts.app_label, opts.module_name),
                                    current_app=self.admin_site.name))

    def delete_view(self, request, object_id, extra_context=None):
        opts = self.model._meta
        app_label = opts.app_label
        obj = self.get_object(request, unquote(object_id))
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does '
                'not exist.') % {'name': force_unicode(opts.verbose_name),
                    'key': escape(object_id)})

        if request.POST: # The user has already confirmed the deletion.
            obj_display = force_unicode(obj)
            self.log_deletion(request, obj, obj_display)
            self.delete_model(request, obj)
            self.message_user(request, _('The %(name)s "%(obj)s" was deleted '
                'successfully.') % {'name': force_unicode(opts.verbose_name),
                    'obj': force_unicode(obj_display)})
            return self.response_delete(request)

        object_name = force_unicode(opts.verbose_name)
        context = {
            "object_name": object_name,
            "object": obj,
            "opts": opts,
            "app_label": app_label,
        }
        context.update(extra_context or {})

        return TemplateResponse(request, self.delete_confirmation_template or [
            "admin/%s/%s/delete_confirmation.html" % (app_label,
                opts.object_name.lower()),
            "admin/%s/delete_confirmation.html" % app_label,
            "admin/delete_confirmation.html"
        ], context, current_app=self.admin_site.name)

class AdminSite(DjangoAdminSite):
    def has_permission(self, request):
        return request.user.is_active

    def _reinit_model_admins(self):
        for model, model_admin in self._registry.items():
            cls = model_admin.__class__
            cls = getattr(cls, '__unmixed_class__', cls)
            self._registry[model] = cls(model, self)

    def get_urls(self):
        self._reinit_model_admins()
        return super(AdminSite, self).get_urls()

    def login(self, request, extra_context=None):
        query = urllib.urlencode({'next': request.get_full_path()})
        return HttpResponseRedirect(reverse('auth_login') + '?' + query)

site = AdminSite(name='oioioiadmin')

contest_admin_menu_registry = MenuRegistry()
system_admin_menu_registry = MenuRegistry()

#contest_admin_menu_registry.register('dashboard', _("Dashboard"),
#        lambda request: reverse('oioioiadmin:index'), order=10)

class OioioiUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_superuser',
                                       'groups')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    list_display = ['username', 'email', 'first_name', 'last_name',
            'is_active']

site.register(User, OioioiUserAdmin)

system_admin_menu_registry.register('users', _("Users"),
        lambda request: reverse('oioioiadmin:auth_user_changelist'), order=10)

class InstanceDependentAdmin(admin.ModelAdmin):
    default_model_admin = admin.ModelAdmin

    def _model_admin_for_instance(self, request, instance=None):
        raise NotImplementedError

    def _find_model_admin(self, request, object_id):
        if object_id is None:
            obj = None
        else:
            obj = self.get_object(request, unquote(object_id))
        model_admin = self._model_admin_for_instance(request, obj)
        if not model_admin:
            model_admin = self.default_model_admin(self.model, self.admin_site)
        return model_admin

    def add_view(self, request, form_url='', extra_context=None):
        model_admin = self._find_model_admin(request, None)
        return model_admin.add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        model_admin = self._find_model_admin(request, object_id)
        return model_admin.change_view(request, object_id, form_url,
                extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        model_admin = self._find_model_admin(request, object_id)
        return model_admin.delete_view(request, object_id, extra_context)

    def changelist_view(self, request, extra_context=None):
        model_admin = self._find_model_admin(request, None)
        return model_admin.changelist_view(request, extra_context)

    def history_view(self, request, object_id, extra_context=None):
        model_admin = self._find_model_admin(request, object_id)
        return model_admin.history_view(request, object_id, extra_context)

class MixinsAdmin(InstanceDependentAdmin):
    def __init__(self, *args, **kwargs):
        super(InstanceDependentAdmin, self).__init__(*args, **kwargs)
        if not issubclass(self.default_model_admin, ObjectWithMixins):
            raise AssertionError('MixinsAdmin.default_model_admin must '
                'be a subclass of ObjectWithMixins')

    def _model_admin_for_instance(self, request, instance=None):
        mixins = self._mixins_for_instance(request, instance)
        if mixins:
            return self.default_model_admin(self.model, self.admin_site,
                mixins=mixins)

    def _mixins_for_instance(self, request, instance=None):
        raise NotImplementedError
