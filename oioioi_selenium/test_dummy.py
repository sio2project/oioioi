from . import OIOIOISeleniumTestCase


class TestDummy(OIOIOISeleniumTestCase):
    def test_dummy(self):
        driver = self.driver
        driver.get("/")
        driver.save_screenshot("test_dummy.png")
