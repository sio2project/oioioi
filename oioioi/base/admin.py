import urllib

from django.template.response import TemplateResponse
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.utils.encoding import force_unicode, force_text
from django.utils.html import escape
from django.contrib.admin import helpers
from django.contrib.admin.utils import unquote, model_ngettext, NestedObjects
from django.contrib.admin.sites import AdminSite as DjangoAdminSite
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst
from django.contrib import messages
from django.db import router

from oioioi.base.permissions import is_superuser
from oioioi.base.utils import ObjectWithMixins, ClassInitMeta
from oioioi.base.utils.redirect import safe_redirect
from oioioi.base.menu import MenuRegistry, side_pane_menus_registry
from oioioi.base.forms import OioioiUserChangeForm, OioioiUserCreationForm

TabularInline = admin.TabularInline
StackedInline = admin.StackedInline


class ModelAdminMeta(admin.ModelAdmin.__class__, ClassInitMeta):
    pass


class ModelAdmin(admin.ModelAdmin, ObjectWithMixins):
    __metaclass__ = ModelAdminMeta

    # This is handled by AdminSite._reinit_model_admins
    allow_too_late_mixins = True

    def response_change(self, request, obj):
        not_popup = '_popup' not in request.GET and \
                    '_popup' not in request.POST
        if '_continue' in request.POST and not_popup:
            return HttpResponseRedirect(request.get_full_path())
        if 'came_from' in request.GET and '_continue' not in request.POST \
                and '_saveasnew' not in request.POST \
                and '_addanother' not in request.POST:
            return safe_redirect(request, request.GET.get('came_from'))
        return super(ModelAdmin, self).response_change(request, obj)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        response = super(ModelAdmin, self).change_view(request, object_id,
                form_url, extra_context)
        if isinstance(response, TemplateResponse) \
                and 'came_from' in request.GET:
            response.context_data['form_url'] += '?' + \
                    urllib.urlencode({
                        'came_from': request.GET.get('came_from')
                    })
        return response

    def response_delete(self, request):
        opts = self.model._meta
        if 'came_from' in request.GET:
            return safe_redirect(request, request.GET.get('came_from'))
        if not self.has_change_permission(request):
            return HttpResponseRedirect(reverse('admin:index',
                                            current_app=self.admin_site.name))
        return HttpResponseRedirect(reverse('admin:%s_%s_changelist' %
                                    (opts.app_label, opts.model_name),
                                    current_app=self.admin_site.name))

    def delete_view(self, request, object_id, extra_context=None):
        opts = self.model._meta
        app_label = opts.app_label
        obj = self.get_object(request, unquote(object_id))
        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_("%(name)s object with primary key %(key)r does "
                "not exist.") % {'name': force_unicode(opts.verbose_name),
                    'key': escape(object_id)})

        if request.POST:  # The user has already confirmed the deletion.
            obj_display = force_unicode(obj)
            self.log_deletion(request, obj, obj_display)
            self.delete_model(request, obj)
            self.message_user(request, _("The %(name)s \"%(obj)s\" was "
                "deleted successfully.") % {
                    'name': force_unicode(opts.verbose_name),
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

    def get_custom_list_select_related(self):
        """Returns a list of fields passed to queryset.select_related
           By default - empty list. Override this method (instead of
           get_queryset()) to pass another field to the select_related.
        """
        return []

    def get_queryset(self, request):
        qs = super(ModelAdmin, self).get_queryset(request)
        list_select_related = self.get_custom_list_select_related()
        if list_select_related:
            return qs.select_related(*list_select_related)
        else:
            return qs


def delete_selected(modeladmin, request, queryset):
    """Default ModelAdmin action that deletes the selected objects.

       Django's default handler doesn't even check the
       has_delete_permission() of corresponding ModelAdmin with specific
       instances (only the general permission), and requires django's User
       model permissions as well. Theese aren't currently used in OIOIOI, so
       this custom method doesn't care about them.

       This implementation checks if deleted model is registered in the
       current AdminSite and if it is, then uses has_delete_permission() with
       it's instance.

       It first displays a confirmation page that shows all the
       deleteable objects, or, if the user has no permission for one of the
       related objects (foreignkeys), a "permission denied" message.
       Next, it deletes all selected objects and redirects back
       to the change list.
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label

    # Find related objects and check their permissions
    # This is a custom method as well
    to_delete, perms_needed, protected = \
            collect_deleted_objects(modeladmin, request, queryset)

    # The user has already confirmed the deletion.
    # Do the deletion and return a None to display the change list view again.
    if request.POST.get('post'):
        if perms_needed:
            raise PermissionDenied
        n = queryset.count()
        if n:
            for obj in queryset:
                obj_display = force_text(obj)
                modeladmin.log_deletion(request, obj, obj_display)
            queryset.delete()
            message_text = _("Successfully deleted %(count)d %(items)s.") % {
                "count": n,
                "items": model_ngettext(modeladmin.opts, n)
            }
            modeladmin.message_user(request, message_text, messages.SUCCESS)
        # Return None to display the change list page again.
        return None

    if len(queryset) == 1:
        objects_name = force_text(opts.verbose_name)
    else:
        objects_name = force_text(opts.verbose_name_plural)

    if perms_needed or protected:
        title = _("Cannot delete %(name)s") % {"name": objects_name}
    else:
        title = _("Are you sure?")

    context = dict(
        modeladmin.admin_site.each_context(request),
        title=title,
        objects_name=objects_name,
        deletable_objects=[to_delete],
        queryset=queryset,
        perms_lacking=perms_needed,
        protected=protected,
        opts=opts,
        action_checkbox_name=helpers.ACTION_CHECKBOX_NAME,
    )

    request.current_app = modeladmin.admin_site.name

    custom_template = modeladmin.delete_selected_confirmation_template

    # Display the confirmation page
    return TemplateResponse(request, custom_template or [
        "admin/%s/%s/delete_selected_confirmation.html" % (app_label,
            opts.model_name),
        "admin/%s/delete_selected_confirmation.html" % app_label,
        "admin/delete_selected_confirmation.html"
    ], context)

delete_selected.short_description = \
    _("Delete selected %(verbose_name_plural)s")


def collect_deleted_objects(modeladmin, request, queryset):
    """Collects objects that are related to queryset items and checks
       their permissions.

       This method checks if the user has permissions to delete items that are
       anyhow related to theese in the queryset (regardless of the depth).

       ``modeladmin`` is expected to be a ModelAdmin instance corresponding
       to the class of items contained in the ``queryset``.
    """
    db_backend = router.db_for_write(queryset.first().__class__)
    # NestedObjects is undocumented API, can blow up at any time
    collector = NestedObjects(using=db_backend)
    collector.collect(queryset)

    # Check permissions and return a human-readable string representation
    perms_needed = set()

    def format_callback(obj):
        admin_site = modeladmin.admin_site
        has_admin = obj.__class__ in admin_site._registry
        opts = obj._meta

        if has_admin:
            model_admin = admin_site._registry[obj.__class__]
            if not request.user.is_superuser and \
                    not model_admin.has_delete_permission(request, obj):
                perms_needed.add(opts.verbose_name)

        return '%s: %s' % (capfirst(force_text(opts.verbose_name)),
                           force_text(obj))

    # Get a nested list of dependent objects
    to_delete = collector.nested(format_callback)

    protected = [format_callback(obj) for obj in collector.protected]

    return to_delete, perms_needed, protected


class AdminSite(DjangoAdminSite):
    def __init__(self, *args, **kwargs):
        super(AdminSite, self).__init__(*args, **kwargs)
        # Override default delete_selected action handler
        # See delete_selected() docstring for further information
        self._actions['delete_selected'] = delete_selected
        self._global_actions['delete_selected'] = delete_selected

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

system_admin_menu_registry = MenuRegistry(_("System Administration"),
                                          is_superuser)
side_pane_menus_registry.register(system_admin_menu_registry, order=10)


class OioioiUserAdmin(UserAdmin, ObjectWithMixins):
    form = OioioiUserChangeForm
    add_form = OioioiUserCreationForm

    __metaclass__ = ModelAdminMeta

    # This is handled by AdminSite._reinit_model_admins
    allow_too_late_mixins = True

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_("Personal info"), {'fields': ('first_name', 'last_name', 'email')}),
        (_("Permissions"), {'fields': ('is_active', 'is_superuser',
                                       'groups')}),
        (_("Important dates"), {'fields': ('last_login', 'date_joined')}),
    )
    list_filter = ['is_superuser', 'is_active']
    list_display = ['username', 'email', 'first_name', 'last_name',
            'is_active']
    filter_horizontal = ()
    actions = ['activate_user']

    def activate_user(self, request, qs):
        qs.update(is_active=True)
    activate_user.short_description = _("Mark users as active")


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
