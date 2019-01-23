Selenium tests
--------------

This module allows us to run selenium tests for OIOIOI.
As opposed to regular django tests these are integration tests
run under production-like environment, with external filetracker and
database.

USELEFUL TIPS AND TRICKS
........................

1. Do not run tests straight by invoking `test_selenium.sh` script.
   Instead build docker images without the -d flag in another terminal
   (just copy and paste the command from the script and remove -d)
   [`docker-compose -f docker-compose-selenium.yml up`]. Why?
   You can easily navigate through the logs there real-time
   (instance is visible at 8001 port).
2. Run the docker images and test from a different terminal
   (using pytest). There is one problem with this, though.
   When you need to reload the database, just connect to the docker
   and manually restart it.
3. Use firefox to take correct XPATHs to some elements (just inspect and copy).
   The alternatives are third-party extensions to Chrome, they can even export
   test to python2 code - but watch out here, sometimes the IDs in OIOIOI are broken
   (e.g. the ID of a date is a date itself).
4. When in trouble you can connect your own webdriver (f.e. chrome webdriver)
   and write tests to see the results right at your screen.
5. Firefox and selenium are broken. Clicking the element once is not enough
   for most cases, just click twice with an exception catching phrases or
   send some KEY presses to the element.

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
Any arguments passed to it are forwarded to pytest.
This script is responsible for launching docker containers with fresh OIOIOI
and stuff needed by Selenium. By default it take some time to perform whole
process so you may customize script to just wipe data between launches etc.

What to do when tests are not working
.....................................

Selenium tests easily get broken after frontend updates -- for example
adding new buttons.
If there were errors in testing the first place to go
are the logs. Unfortunately, you can't rely on screenshots because
stylesheets can't be parsed by Selenium (maybe that will be
fixed soon...). The best alternative we came up with is printing the
whole page source and url after each important step of a test.

Sometimes the tests themselves may be working fine and the real culprit
is Docker or Selenium. Sometimes new Firefox version may become incompatible
with Selenium, so update each of them with care.

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