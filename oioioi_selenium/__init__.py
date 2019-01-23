import unittest
import time
from functools import wraps

from selenium.webdriver.remote import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
import six
from six.moves import range


class WebDriver(webdriver.WebDriver):
    def __init__(self):
        firefox_profile = FirefoxProfile()
        # we need to turn off stylesheets because otherwise Selenium couldn't find
        # the the buttons in tests
        firefox_profile.set_preference('permissions.default.stylesheet', 2)
        super(WebDriver, self).__init__(
                command_executor='http://127.0.0.1:4444/wd/hub',
                browser_profile=firefox_profile,
                desired_capabilities=DesiredCapabilities.FIREFOX)
        self.set_page_load_timeout(60)
        self.implicitly_wait(60)
        self.base_url = "http://oioioi:8000"
        self.delete_all_cookies()

    def get(self, url):
        """:param url: Url to load, may be absolute or local.
        """
        if url[0:4] != 'http' and url[0:1] == '/':
            url = self.base_url + url
        return super(WebDriver, self).get(url)

    def wait_for_load(self):
        """This method should be called every time Selenium should wait
           for page to load. It should be used when page is loaded or
           there's a need to wait for javascript.
        """
        time.sleep(2)

    def login(self, username, password):
        """Redirects to login page and submits form with given credentials.
           :raises: Assertion error when login fails.
        """
        self.get("/login/")
        self.wait_for_load()
        self.submit_form({
            'auth-username': username,
            'auth-password': password},
            submit="//button[@type='submit']")

        assert self.current_url.find("login") == -1, "Not logged in"

    def logout(self):
        self.get("/")
        self.find_element_by_id("navbar-username").click()
        self.wait_for_load()
        self.find_element_by_link_text("Log out").click()
        self.wait_for_load()

    def submit_form(self, data, submit="//form//button[@type='submit']"):
        """:param data: Dict, element name -> element value.
           :param submit: XPath to form submit button.
        """
        for k, v in six.iteritems(data):
            elem = self.find_element_by_name(k)
            elem.clear()
            elem.click()
            elem.send_keys(v)
        self.find_element_by_xpath(submit).click()
        self.wait_for_load()


class WrapTestsWithScreenshots(type):
    """Metaclass that wraps every method starting with "test_" so that
       a screenshot will be saved on exception.
    """
    @classmethod
    def wrap(mcs, name, test):
        @wraps(test)
        def wrapped(*args, **kwargs):
            try:
                test(*args, **kwargs)
            except:
                args[0].driver.save_screenshot(name + '.png')
                raise
        return wrapped

    def __new__(mcs, class_name, class_parents, class_attrs):
        new_attrs = {}
        for name, attr in class_attrs.items():
            if name.startswith("test_"):
                new_attrs[name] = WrapTestsWithScreenshots.wrap(name, attr)
            else:
                new_attrs[name] = attr
        return type.__new__(mcs, class_name, class_parents, new_attrs)


class OIOIOISeleniumTestCaseBase(six.with_metaclass(WrapTestsWithScreenshots,
        unittest.TestCase)):
    def setUp(self):
        self.driver = WebDriver()

    def tearDown(self):
        self.driver.quit()

    def wait_for_action(self, action, timeout=60, period=2,
                        url=None, **kwargs):
        """:param action: Function to run every `period` seconds, returns True\
                  if expected behaviour was detected, None otherwise.
           :param timeout: After this time test failure is raised.
           :param period: After every `period` seconds action condition\
                  is checked.
           :param url: If not None this url will be loaded before checking.
           :param kwargs: Arguments for action.
        """
        for _ in range(0, timeout, period):
            time.sleep(period)

            if url:
                self.driver.get(url)

            if action(**kwargs):
                return

        self.fail("Timeout")

    id_counter = 0

    @classmethod
    def get_next_id(cls):
        """Should be used every time unique id number is needed.
           :return: Next free id.
        """
        cls.id_counter += 1
        return cls.id_counter


class OIOIOISeleniumTestCase(OIOIOISeleniumTestCaseBase):
    """Adds methods that simplify html elements accessing.
    """

    def get_from_table(self, table, search, n=1):
        """:param table: XPath table identifier like "@id='result_list'".
           :param n: search will be performed in nth row.
                  Tr[] count starts from 1, not 0!
        """
        return self.driver.find_element_by_xpath(
            "//*[{}]/tbody/tr[{}]"
            "{}".format(table, n, search))

    def get_from_result_table(self, search, n=1):
        """Just apply result table to
           :meth:`.get_from_table`.
        """
        return self.get_from_table("@id='result_list'", search, n)

    def get_primary_button_with_text(self, text, item=None):
        if not item:
            item = self.driver
        # pylint: disable=maybe-no-member
        return item.find_element_by_xpath("//button[@class='btn btn-primary' "
                                          "and text()='{}']".format(text))

    @staticmethod
    def xpath_contains(*args, **kwargs):
        """Return xpath contains method, see
           :meth:`.xpath_method` for details.
        """
        return OIOIOISeleniumTestCase.xpath_method('contains', *args, **kwargs)

    @staticmethod
    def xpath_method(method, search, pref='//*', by='class'):
        """:param method: XPath method name.
           :param search: method argument.
           :param pref: Query prefix, //* by default, may be ex. //div/button
           :param by: Attribute to apply method to, may be 'class' or 'id' etc.
           Return xpath method that has quite complicated body. Can be used
           only as a standalone query. However, it's worth notice that xpath
           methods may be easily connected with 'and' or 'or' ex.
           //button[@class='clazz' and text()='sometext'].
        """
        return "{}[{}(@{}, '{}')]".format(pref, method, by, search)
