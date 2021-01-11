from . import OIOIOISeleniumTestCase


class TestAuth(OIOIOISeleniumTestCase):
    def test_registration(self):
        driver = self.driver
        username = "selenium" + str(self.get_next_id())
        password = "password" + str(self.get_next_id())
        driver.get("/")
        driver.find_element_by_id("navbar-username").click()
        driver.find_element_by_link_text("Register").click()
        driver.wait_for_load()
        driver.submit_form(
            {
                'username': username,
                'first_name': username,
                'last_name': username,
                'email': username + '@example.com',
                'password1': password,
                'password2': password,
            },
            "//button[text()='Submit']",
        )
        driver.wait_for_load()
        driver.login(username, password)
        driver.logout()
        driver.login(username, password)
        driver.get("/edit_profile/")
        driver.wait_for_load()
        driver.find_element_by_xpath("//a[text()='Delete account']").click()
        driver.wait_for_load()
        driver.find_element_by_xpath("//button[@type='submit']").click()
        driver.wait_for_load()
        with self.assertRaises(AssertionError):
            driver.login(username, password)

    def test_admin(self):
        driver = self.driver
        driver.login("admin", "admin")
        driver.logout()
