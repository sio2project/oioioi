import time

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException
from . import OIOIOISeleniumTestCase
import os


class TestSimpleContest(OIOIOISeleniumTestCase):
    def test_contest(self):
        driver = self.driver
        driver.login("admin", "admin")

        # Let's create a new contest.
        contest_id = "c" + str(self.get_next_id())
        contest_name = "simple contest " + contest_id
        driver.get("/admin/contests/contest/add/")
        driver.wait_for_load()
        Select(driver.find_element_by_id("id_controller_name")). \
            select_by_visible_text("Simple programming contest")
        driver.find_element_by_id("id_name").click()
        driver.find_element_by_id("id_name").clear()
        driver.find_element_by_id("id_name").send_keys(contest_name)
        driver.find_element_by_id("id_id").clear()
        driver.find_element_by_id("id_id").send_keys(contest_id)
        driver.find_element_by_name("_save").click()
        driver.wait_for_load()
        self.assertEqual("Contest dashboard - OIOIOI", driver.title)

        # Let's add a problem.
        driver.get("/c/" + contest_id + "/admin/contests/probleminstance/")
        driver.find_element_by_link_text("Add problem").click()
        driver.find_element_by_id("id_package_file").clear()
        driver.find_element_by_id("id_package_file").send_keys(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))) + "/oioioi/sinolpack/files/test_full_package.tgz")
        submit_problem_button = driver.find_element_by_xpath("/html/body/div[2]/div/div/section/div/form/div[2]/button")
        submit_problem_button.click()
        try:
            submit_problem_button.send_keys(Keys.RETURN)
        except StaleElementReferenceException:
            pass

        driver.wait_for_load()

        # Wait for problem package to process, at most ~20s.
        time.sleep(20)
        driver.get("/c/" + contest_id + "/admin/problems/problempackage/")
        self.assertEqual("Uploaded", driver.find_element_by_xpath(
            "/html/body/div[2]/div[1]/div/section/div/div[2]/div/div/form/div[2]/table/tbody/tr[1]/td[4]/span").text)

        # Submit some dummy code as administrator.
        driver.get("/c/" + contest_id + "/submit/")
        driver.find_element_by_id("id_code").click()
        driver.find_element_by_id("id_code").clear()
        driver.find_element_by_id("id_code").send_keys("int main() {}")
        driver.find_element_by_id("id_prog_lang").click()
        Select(driver.find_element_by_id("id_prog_lang")).select_by_visible_text("C")
        driver.find_element_by_id("id_prog_lang").click()
        Select(driver.find_element_by_id("id_kind")).select_by_visible_text("Normal")
        driver.find_element_by_id("id_kind").click()
        submit_solution_button = driver.find_element_by_xpath(
            "(.//*[normalize-space(text()) and normalize-space(.)='Kind'])[1]/following::button[1]")
        submit_solution_button.click()
        try:
            submit_solution_button.send_keys(Keys.RETURN)
        except StaleElementReferenceException:
            pass

        # Check if it was submitted.
        time.sleep(30)
        driver.get("/c/" + contest_id + "/submissions/")
        self.assertEqual("0", driver.find_element_by_xpath(
            "(.//*[normalize-space(text()) and normalize-space(.)='Score'])[1]/following::td[6]").text)

    def wait_for_package(self):
        state = self.get_from_result_table(
            self.xpath_contains('prob-pack--'), 1).text

        if state == "Uploaded":
            return True
        elif state == "Pending problem package":
            return False
        else:
            self.fail("Unexpected problem with package upload: " + state)

    def wait_for_submission_result(self):
        state = self.get_from_table(
            "@id='submission-status-table'",
            self.xpath_contains('submission--'), 1).text

        if state == "Pending":
            return False
        elif state == "Initial tests: failed":
            return True
        else:
            self.fail("Unexpected submission state: " + state)
