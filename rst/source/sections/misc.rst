===========
Miscellanea
===========

Dynamic mixins
--------------

.. currentmodule:: oioioi.base.utils

.. autoclass:: oioioi.base.utils.ObjectWithMixins
   :members:

Remembering the current contest
-------------------------------

.. autoclass:: oioioi.contests.middleware.CurrentContestMiddleware

.. autofunction:: oioioi.contests.processors.register_current_contest


Checking for instance-level permissions in templates
----------------------------------------------------

To check for model-level permissions, one may use the `standard Django
mechanism <https://docs.djangoproject.com/en/1.4/topics/auth/#id9>`_. To check
for instance-level permissions, use ``{% check_perm %}`` template tag.

.. autofunction:: oioioi.base.templatetags.check_perm.check_perm


Menu
----

.. currentmodule:: oioioi.base.menu

In OIOIOI we have several menus, some of them are shown on the left.
Menu items are stored in registries like
:data:`oioioi.base.menu.menu_registry`, which is an instance of
:class:`oioioi.base.menu.MenuRegistry`. To add a new menu item,
use :meth:`~oioioi.base.menu.MenuRegistry.register`, preferably in
``views.py``, for example::

    from oioioi.base.menu import menu_registry
    menu_registry.register_item(
            'problems_list',
            _("Problems"),
            lambda request: reverse('problems_list', kwargs={'contest_id':
                request.contest.id}),
            order=100)

.. autoclass:: MenuRegistry

    .. automethod:: MenuRegistry.register(name, text, url_generator, order=sys.maxint, condition=None)

    .. automethod:: MenuRegistry.unregister(name)

.. autodata:: menu_registry

.. autodata:: account_menu_registry

Feel free to create new menu registries. If you want it to be visible on the
left pane, register it in :data:`oioioi.base.menu.side_pane_menus_registry`, for
example::

    from oioioi.base.menu import MenuRegistry, side_pane_menus_registry
    new_menu_registry = MenuRegistry(_("Some Menu"),
        lambda request: request.user.is_authenticated())
    side_pane_menus_registry.register(new_menu_registry, order=500)

.. autodata:: side_pane_menus_registry

For rendering the menu inside a template, a special ``{% generate_menu %}`` tag is used.

.. autofunction:: oioioi.base.templatetags.menu.generate_menu

Switching users (su)
--------------------

.. currentmodule:: oioioi.su

.. automodule:: oioioi.su

.. autofunction:: oioioi.su.utils.su_to_user

.. autofunction:: oioioi.su.utils.reset_to_real_user
