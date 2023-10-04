===========
Miscellanea
===========

Celery usages
-------------
This section briefly describes currently used applications of Celery across the infrastructure.

- :doc:`Problem uploading </sections/problem_uploading>`
- :doc:`Problem evaluation </sections/evaluation>`

.. _celery: http://docs.celeryproject.org/en/latest/django/index.html

Getting current time
--------------------

The main source of the current time in the request processing should be
the ``request.timestamp`` variable. This variable contains the time when
the request was initiated and, when used consistently, allows the admins
to time travel.

Usage of ``timezone.now()`` is highly discouraged.

.. autoclass:: oioioi.base.middleware.TimestampingMiddleware

Current contest mechanism
-------------------------

.. autoclass:: oioioi.contests.middleware.CurrentContestMiddleware

.. autofunction:: oioioi.contests.current_contest.reverse

.. autofunction:: oioioi.contests.urls.make_patterns

.. autodata:: oioioi.contests.admin.contest_site

.. autofunction:: oioioi.contests.processors.register_current_contest


Exclusive contests
------------------

.. autoclass:: oioioi.contestexcl.middleware.ExclusiveContestsMiddleware

.. autoclass:: oioioi.participants.ExclusiveContestsWithParticipantsMiddlewareMixin

Checking for instance-level permissions in templates
----------------------------------------------------

To check for model-level permissions, one may use the `standard Django
mechanism <https://docs.djangoproject.com/en/1.7/topics/auth/default/#topic-authorization>`_.
To check for instance-level permissions, use ``{% check_perm %}`` template tag.

.. autofunction:: oioioi.base.templatetags.check_perm.check_perm

Conditions
----------

.. currentmodule:: oioioi.base.permissions

.. autoclass:: Condition

.. autoclass:: RequestBasedCondition

.. autofunction:: make_condition(condition_class=Condition)

.. autofunction:: make_request_condition

To assign a condition to a view use the ``enforce_condition`` decorator:

.. autofunction:: enforce_condition

Additionally, the ``enforce_condition`` decorator adds a ``condition`` attribute
to the view, which can be later used by
:meth:`oioioi.base.menu.MenuRegistry.register_decorator`.

Mixing it all together in a simple example::

    @make_request_condition
    def is_superuser(request):
        return request.user.is_superuser

    @enforce_condition(is_superuser & ~is_superuser)
    def not_accessible_view(request):
        pass

Menu
----

.. currentmodule:: oioioi.base.menu

In OIOIOI we have several menus, some of them are shown on the left.
Menu items are stored in registries like
:data:`oioioi.base.menu.menu_registry`, which is an instance of
:class:`oioioi.base.menu.MenuRegistry`. The most preferable way to add a new item
menu is to use the :meth:`~oioioi.base.menu.MenuRegistry.register_decorator`,
for example::

    from oioioi.base.permissions import not_anonymous
    from oioioi.base.menu import menu_registry
    @menu_registry.register_decorator(_("Example"),
            lambda request: reverse('example', kwargs={'contest_id':
                request.contest.id}),
            order=100)
    @enforce_condition(not_anonymous)
    def example_view(request, contest_id):
        pass

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

Zeus integration (zeus)
-----------------------

.. currentmodule:: oioioi.zeus

.. automodule:: oioioi.zeus

Zeus instances are configured in ``settings.ZEUS_INSTANCES``, which is a dict
mapping ``zeus_id`` - unique identifier of a zeus instance - to ``(zeus_url,
zeus_login, zeus_secret)`` - base URL for zeus api (*ZBU*) and credentials.
It is also possible to use a mock instance (``ZeusTestServer``)
which allows manual testing for development purposes.

API specification
.................

Communication with zeus is done over HTTPS protocol, in a REST-like style. Data
is encoded using JSON. OIOIOI authorizes itself to zeus using HTTP Basic
Authentication, with login and secret fixed for a zeus instance.

Prefix **?** means optional attribute.

Sending submissions
~~~~~~~~~~~~~~~~~~~

:Request:

|    POST *ZBU*/dcj_problem/*zeus_problem_id*/submissions

:Data sent:

|   {
|       "submission_type": submission_type :: Base64String(SMALL|LARGE),
|       "return_url": return_url :: Base64String,
|       "username": username :: Base64String,
|       "metadata": metadata :: Base64String,
|       "source_code": source_code :: Base64String,
|       "language": source_language :: Base64String(CPP|...),
|   }

:Result:

Code 200 and data:

|    { "submission_id": unique_job_id :: Uint }

or code 4xx|5xx and data:

|    { **?** "error": error_description :: Base64String }

``username`` and ``metadata`` fields are not used by Zeus
and sent for debugging purposes only.


Receiving results
~~~~~~~~~~~~~~~~~


Zeus hits the "return_url" from submission data once it is graded.

:Data received:

|   {
|       "compilation_output": output :: Base64String,
|   }

in case of compilation failure or

|   {
|       "tests_info": list_of_results :: [TestInfo],
|   }

in case of compilation success, where

|    TestInfo = {
|        "time_limit_ms": execution_time_limit :: Int,
|        "memory_limit_byte": memory_limit :: Int,
|        "verdict": test_status :: Base64String(OK|WA|TLE|RE|RV|OLE|MSE|MCE),
|        "runtime": max_of_times_at_all_machines :: Int,
|        "metadata": more_data_about_test :: Base64String,
|        **?** "nof_nodes": number_of_nodes :: Int,
|    }


:Our response:

Code 200 and ``HttpResponse("Recorded!")``
or code 4xx|5xx and a lot of HTML (for example the one which normally displays
a message **Internal Server Error** in a browser). When server received
invalid JSON or strings are not encoded with Base64, then it will response with
code 400 and nice error message.

*MSE* and *MCE* are statuses meaning that size or count of outgoing messages
sent by submitted program has exceeded the limit.

Metadata is subject to coordination between judges and contest admin.
It may be passed through zeus, but in the most recent workflow
we sent meaningless metadata to zeus and received meaningful metadata
(zeus admins were provided with a file containing metadata for each test).
It is designed to contain additional data
about grouping, scoring etc. Currently we expect it to be in format:

| "*test name*,\ *group name*,\ *max score*"

Test name will be shown to users. All tests with the same, non-empty group name
will be grouped together. All tests in group shall have the same max score.
Example tests are expected to be in the group ``0``.
