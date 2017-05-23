import unittest
import time
from functools import wraps

from selenium.webdriver.remote import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


class WebDriver(webdriver.WebDriver):
    def __init__(self):
        super(WebDriver, self).__init__(
                command_executor='http://127.0.0.1:4444/wd/hub',
                desired_capabilities=DesiredCapabilities.FIREFOX)
        self.set_page_load_timeout(60)
        self.implicitly_wait(60)
        self.base_url = "http://oioioi:8000"
        self.delete_all_cookies()

    def get(self, url):
        if url[0:4] != 'http' and url[0:1] == '/':
            url = self.base_url + url
        return super(WebDriver, self).get(url)

    def wait_for_load(self):
        time.sleep(2)

    def login(self, username, password):
        self.get("/login/")
        self.submit_form({
            'username': username,
            'password': password},
            submit="//*[@id='id_submit']")

        assert self.current_url.find("login") == -1, "Not logged in"

    def logout(self):
        self.get("/")
        self.find_element_by_id("navbar-username").click()
        self.find_element_by_link_text("Log out").click()
        self.wait_for_load()

    def submit_form(self, data, submit="//form//button[@type='submit']"):
        for k, v in data.iteritems():
            elem = self.find_element_by_name(k)
            elem.clear()
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


class TestCase(unittest.TestCase):
    __metaclass__ = WrapTestsWithScreenshots

    def setUp(self):
        self.driver = WebDriver()

    def tearDown(self):
        self.driver.quit()

    def wait_for_action(self, action, timeout=60, period=2,
                        url=None, **kwargs):
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
        cls.id_counter += 1
        return cls.id_counter

    # Methods that simplify html elements accessing.

    def get_from_table(self, table, search, n=1):
        """
        Tr[] count starts from 1, not 0!
        """
        return self.driver.find_element_by_xpath(
            "//*[{}]/tbody/tr[{}]"
            "{}".format(table, n, search))

    def get_from_result_table(self, search, n=1):
        return self.get_from_table("@id='result_list'", search, n)

    def get_primary_button_with_text(self, text, item=None):
        if not item:
            item = self.driver
        # pylint: disable=maybe-no-member
        return item.find_element_by_xpath("//button[@class='btn btn-primary' "
                                          "and text()='{}']".format(text))

    @staticmethod
    def xpath_contains(*args, **kwargs):
        return TestCase.xpath_method('contains', *args, **kwargs)

    @staticmethod
    def xpath_method(method, search, pref='//*', by='class'):
        return "{}[{}(@{}, '{}')]".format(pref, method, by, search)
