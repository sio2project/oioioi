===========
Miscellanea
===========

Dynamic mixins
--------------

.. currentmodule:: oioioi.base.utils

.. autoclass:: oioioi.base.utils.ObjectWithMixins
   :members:

Getting current time
--------------------

The main source of the current time in the request processing should be
the ``request.timestamp`` variable. This variable contains the time when
the request was initiated and, when used consistently, allows the admins
to time travel.

Usage of ``timezone.now()`` is highly discouraged.

.. autoclass:: oioioi.base.middleware.TimestampingMiddleware

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
mechanism <https://docs.djangoproject.com/en/1.6/topics/auth/default/#topic-authorization>`_.
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

API specification
.................

Communication with zeus is done over HTTPS protocol, in a REST-like style. Data
are encoded using JSON. OIOIOI authorizes itself to zeus using HTTP Basic
Authentication, with login and secret fixed for a contest.

Prefix **?** means optional attribute, prefix **T** marks attribute only for
testrun.

Sending submissions
~~~~~~~~~~~~~~~~~~~

:Request:

|    POST *ZBU*/problem/*zeus_problem_id*/job/*INITIAL|NORMAL|TESTRUN*/

:Data sent:

|   {
|       "source_code": source_code :: Base64String,
|       **T** "library": library_generating_input :: Base64String,
|       **T** "input_test" input_for_library :: Base64String,
|       "language": source_language :: Base64String(CPP|...),
|   }

:Result:

Code 200 and data:

|    { "check_uid": unique_job_id :: Uint }

or code 4xx|5xx and data:

|    { **?** "error": error_description :: Base64String }

Fetching results
~~~~~~~~~~~~~~~~

Fetching results is done using long polling.

:Request:

|   GET *ZBU*/reports_since/*last_seq*/

:Result:

Code 200 and data:

|    {
|        "next_seq": next_sequential_number :: Int,
|        "reports": list_of_reports :: [Report]
|    }

where

|    Report = {
|        "check_uid": job_id :: Int,
|        **T** "stdout_uid": unique_output_id :: Int,
|        "compilation_successful": was_compilation_successful :: Bool,
|        "compilation_message": compiler_result :: Base64String,
|        "report_kind": check_kind :: Base64String(INITIAL|NORMAL|TESTRUN),
|        "status": test_status :: Base64String(OK|WA|TLE|RE|RV|MSE|MCE),
|        "result_string": status_description :: Base64String,
|        "metadata": more_data_about_test :: Base64String,
|        **T** "stdout": first_10kB_of_output :: Base64String
|        **T** "stdout_size": size_of_full_stdout_in_bytes :: Int,
|        "execution_time_ms": max_of_times_at_all_machines :: Int,
|        "time_limit_ms": execution_time_limit :: Int,
|        "memory_limit_byte": memory_limit :: Int,
|    }

or code 4xx|5xx and data:

|    { **?** "error": error_description :: Base64String }

Each check_uid will appear in at most one result - results for given job will
be sent together, when all are ready.

*MSE* and *MCE* are statuses meaning that size or count of outgoing messages
sent by submitted program has exceeded the limit.

Metadata are subject to coordination between judges and contest admins, they
are just passed through zeus. They are designed to contain additional data
about grouping, scoring etc. Currently we expect them to be in format:

| "*test name*,\ *group name*,\ *max score*"

Test name will be shown to users. All tests with the same, non-empty group name
will be grouped together. All tests in group shall have the same max score.

Fetching full output
~~~~~~~~~~~~~~~~~~~~

:Request:

|   GET *ZBU*/full_stdout/*stdout_uid*/

:Result:

Code 200 and data:

|   { "full_stdout" : full_stdout_limited_to_1MB :: Base64String }

or code 4xx|5xx and data:

|    { **?** "error": error_description :: Base64String }
