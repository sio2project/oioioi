======================
Contributing to OIOIOI
======================

How to create Pull Request
--------------------------

Follow generic guidelines from https://docs.github.com/en/pull-requests/collaborating-with-pull-requests

Before you start
    Pick an issue and say in a comment that you want to work on it.
    Wait until a maintainer assigns the issue to you, then start.
    If you want to fix something that has no issue yet, open the issue first.
    A pull request for an issue that is not assigned to you may be closed without review.
    Small fixes, such as typos in the documentation, don't need an issue.

What a pull request should contain
    One issue per pull request. Link it in the description (``Fixes #123``).
    Describe what you changed and why in your own words; don't copy the text of the issue.
    Follow the code style and run the checks described in ``README.rst`` and ``AGENTS.md``
    (ruff, the tests for the apps you touched, migrations and lockfiles committed with the change).

Run your change
    Before you open the pull request, run the change yourself, not only the unit tests.
    If the issue lists steps to check the change, do them and report the results.
    Write in the description what you ran and what you saw.
    If you could not run something (for example, you have no Docker), say so.
    A pull request that was never run is not ready: open it as a draft.

AI tools
    You may use AI coding assistants, but you are responsible for the result.
    You must understand every line of your change and be able to explain it in the review.
    Say in the description which tools you used and for what.

Maintainers may close pull requests that don't follow these rules.


Populating the Task Archive locally
-----------------------------------

The Task Archive (``/task_archive/``) lists the problems attached to an origin tag,
grouped by the tag's origin info categories. The score badges show the results of the
logged-in user. There are three ways to fill it in the Docker setup.

Mock competition
    ::

        ./easy_toolbox.py exec python manage.py create_mock_competition -b 3 -l 2 --with-instances --results-for admin

    Creates an origin tag with a tree of problems: ``-b`` top-level branches, ``-l`` levels,
    3 problems per leaf group. ``--with-instances`` makes the problem pages open.
    ``--results-for USERNAME`` (requires ``--with-instances``) adds results for that user:
    at least one full, partial and zero score, in at least two groups, and at least one
    problem without a result. ``-s SEED`` makes the data reproducible; use a different seed
    for each run on the same database.

    The problems have no statements or tests: you cannot submit to them, and the
    submission pages behind the badges cannot be opened.

Real problems
    Add a package, e.g. one of the samples in ``oioioi/sinolpack/files/``::

        ./easy_toolbox.py exec python manage.py addproblem ../oioioi/oioioi/sinolpack/files/test_full_package.tgz

    As a superuser in the admin panel, create a tag under *Origin tags*, a category under
    *Origin tags - information categories* (set its *grouping order*, otherwise the archive
    does not group by it) and a value under *Origin tags - information values*. Each of them
    needs a name in every language. Then add the tag and the value to the problem on its
    edit page, under *Origin tags* and *Additional origin information*.

    Badges appear only for your own judged submissions.

Fixtures
    ::

        ./easy_toolbox.py exec python manage.py loaddata test_users test_task_archive
        ./easy_toolbox.py exec python manage.py loaddata test_task_archive_progress_labels

    Keep the two commands separate: loaded together on PostgreSQL, the second fixture's
    problems silently end up without a tag. Load them into a fresh database only, as they
    use fixed ids and overwrite existing rows; they also need the user with id 1 (``admin``
    in the Docker setup). The test users have no password, so set one with
    ``./easy_toolbox.py exec python manage.py changepassword test_user``. ``test_user`` and
    ``test_user2`` have results in the ``oi`` tag; only its problems ``hel``, ``sum`` and
    ``sim`` can be opened.


SIO2 Translator's Guide
-----------------------

We use Transifex_ to manage translations.

Why translate?
    It's always better to see an application in you mother tongue.
    No matter how well you speak English, it's always nice to use applications in the language you think in, isn't it?
    And as SIO2 aims to be accessible to everybody around the world, we want it to be translated to as many languages as possible.
    And unfortunately we don't speak that many languages, so we need to rely on your help!
    If you speak a language other than English and think you're capable of translating, try it!
    It's really easy, there is no technical knowledge required and you can get started really fast!

I want to help!
    That's great! Everybody wanting to help will be welcome!
    To start you need to go to our page on Transifex, create an account and start translating!
    Transifex_ has a very comprehensive help, which you may use to learn how to use it.
    You're welcome to translate as many messages you see, and create your own languages!

.. _Transifex: https://app.transifex.com/sio2project/sio2project/

Advice
    The text on the left is the text to translate, and the text on the right is the translated text, that's easy.
    But what to do with strange %(gizmo)s? It's also simple, they are just placeholders which will be changed
    to real words during SIO2 execution. You just need to place them in the same exact form where they should be used in your language.

What to do with plural forms?!
    Plural forms are tricky, and they are not very well explained.
    When a message contains a plural form, it has to be translated into a few different versions.
    English has only 2 (singular and plural), but if your language is more complicated you need to watch out.
    Generally you will have a few text areas to write different plural versions.
    The best way to know where goes which is to find other project translated into that language.
    There is also a small note to the right of each text area, but it may be hard to understand.
    For example for Polish it should be:
+-----------------------+-----------------------+
| English               | Polish                |
+=======================+=======================+
| Ala has %(cats)d cat  | Ala ma jednego kota   |
+------------+----------+-----------------------+
| Ala has %(cats)d cats | Ala ma %(cats)d koty  |
+-----------------------+-----------------------+
|                       | Ala ma %(cats)d kotów |
+-----------------------+-----------------------+

Working with Transifex and SIO2 guide (for developers translating)
    Correcting original English strings
        Unfortunately, Transifex does not allow for editing English strings in its editor.
        They need to be changed in the source files, preferably along with msgid.
        The files you need are in *oioioi/_locale/locale/<lang>/LC_MESSAGES/*,
        where <lang> is the short version (pl, en, de) of one of the currently supported
        languages defined in the **settings.py** file.
        You can edit only the *.po* files, however if you change msgid (preferable)
        you have to also change it in all the other languages and all the source files the id occurs in.
        The source files are all listed above the strings in the *.po* files.
        Some original strings are also used in unit tests, so if you change them, Hudson will notify about the failed build.
    Applying changes from Transifex
        To apply the changes made to localized strings in Transifex you need to sign in to Hudson
        and launch the 'oioioi-translations-download' job.
        To avoid cluttering the commit list it is preferable to only launch that before deploying changes to production.
    Applying changes to Transifex
        This is done automatically by Hudson when submitting a change.
