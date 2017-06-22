Selenium tests
--------------

This module allows us to run selenium tests for OIOIOI.
As opposed to regular django tests these are integration tests
run under production-like environment, with external filetracker and
database.

Test creation process
.....................

Tests may be created in two ways:
  * Simply write test in python, basing on existing one,
  * Use Selenium IDE plugin for Firefox.

Writing tests with Selenium IDE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With Selenium IDE it's possible to record mouse and keyboard events
in order to create a test.

Before you start look at `Predefined selenium actions`_, there are some
helpful methods that simplify common tasks like login or form submit.

Let's assume you have recorded a test. What's next?

  #. | Export the test to proper python file.
     | File -> Export Test Case As... -> Python 2 / unittest / WebDriver
  #. Remove setUp and tearDown functions and set
     OIOIOISeleniumTestCase as a superclass.
  #. **Important!** Even if test is doing what it's supposed to do, there's
     still some work left. Selenium recorder will recognize elements in
     the easiest possible way. That's not what we want, things may change
     and test will broke because of insufficient description.
     `Simplified html access`_ section may be helpful now.
     The goal is to find elements that are poorly accessed by Selenium
     (for ex. by a class that is not guaranteed to be unique).
     Usually it applies to tables, buttons. The best solution is to access
     elements by ID's, if there's no corresponding ID,
     just do the best you can. It's recommended to find elements by xpath,
     that way you can nicely access nested elements with specific classes,
     ids or tags.

Running Selenium tests
......................

Selenium tests are excluded from default Django tests because they need
different environment.
In OIOIOI's root directory there's script `test_selenium.sh`
which runs all Selenium tests.
Any arguments passed to it are forwarded to nose.
This script is responsible for launching docker containers with fresh OIOIOI
and stuff needed by Selenium. By default it take some time to perform whole
process so you may customize script to just wipe data between launches etc.

What to do when tests are not working
.....................................

If there were errors in testing, the first place to go
is `test_screenshots.tar.gz` archive in project root directory. Test engine
makes screenshot on every failure so you can determine what's gone wrong.
When screen looks like page is not loaded properly, consider adding
:meth:`~oioioi_selenium.__init__.WebDriver.wait_for_load` to wait for it.

.. _`Predefined selenium actions`:

Predefined selenium actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Methods to perform common actions.

If you write some code that fits this section, don't hesitate
to add it there!

.. autoclass:: oioioi_selenium.__init__.WebDriver
   :members:
   :undoc-members:

.. _`Simplified html access`:

Simplified html access
~~~~~~~~~~~~~~~~~~~~~~

If you write some code that fits this section, don't hesitate
to add it there!

.. autoclass:: oioioi_selenium.__init__.OIOIOISeleniumTestCase
   :members:
   :undoc-members:
