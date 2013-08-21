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


Exclusive contests
------------------

.. autoclass:: oioioi.contestexcl.middleware.ExclusiveContestsMiddleware

.. autoclass:: oioioi.participants.ExclusiveContestsWithParticipantsMiddlewareMixin

Checking for instance-level permissions in templates
----------------------------------------------------

To check for model-level permissions, one may use the `standard Django
mechanism <https://docs.djangoproject.com/en/1.5/topics/auth/default/#topic-authorization>`_.
To check for instance-level permissions, use ``{% check_perm %}`` template tag.

.. autofunction:: oioioi.base.templatetags.check_perm.check_perm

Conditions
----------

.. currentmodule:: oioioi.base.permissions

.. autoclass:: Condition

.. autoclass:: RequestBasedCondition

.. autofunction:: make_condition(condition_class=Condition)

To assign a condition to a view use the ``enforce_condition`` decorator:

.. autofunction:: enforce_condition

Additionally, the ``enforce_condition`` decorator adds a ``condition`` attribute
to the view, which can be later used by
:meth:`oioioi.base.menu.MenuRegistry.register_decorator`.

Menu
----

.. currentmodule:: oioioi.base.menu

In OIOIOI we have several menus, some of them are shown on the left.
Menu items are stored in registries like
:data:`oioioi.base.menu.menu_registry`, which is an instance of
:class:`oioioi.base.menu.MenuRegistry`. The most preferable way to add a new item
menu is to use the :meth:`~oioioi.base.menu.MenuRegistry.register_decorator`,
for example::

    from oioioi.base.menu import menu_registry
    @menu_registry.register_decorator(_("Problems"),
            lambda request: reverse('example', kwargs={'contest_id':
                request.contest.id},
            order=100)
    def example_view(request, contest_id):
        ...

The menu item will only be displayed when all the view's conditions are fulfilled.
Therefore you should place all :func:`~oioioi.base.permissions.enforce_condition`
decorators **below** the ``register_decorator`` decorator.

If you cannot use the ``register_decorator`` you can use
:meth:`~oioioi.base.menu.MenuRegistry.register`, preferably in
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

    .. automethod:: MenuRegistry.register_decorator(text, url_generator, order=sys.maxint)

    .. automethod:: MenuRegistry.unregister(name)

.. autodata:: menu_registry

.. autodata:: account_menu_registry

Feel free to create new menu registries. If you want it to be visible on the
left pane, register it in :data:`oioioi.base.menu.side_pane_menus_registry`, for
example::

    from oioioi.base.menu import MenuRegistry, side_pane_menus_registry
    from oioioi.base.permissions import not_anonymous
    new_menu_registry = MenuRegistry(_("Some Menu"), not_anonymous)
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
