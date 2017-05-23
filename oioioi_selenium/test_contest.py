from selenium.webdriver.support.ui import Select

from . import TestCase


class TestSimpleContest(TestCase):
    def test_contest(self):
        driver = self.driver
        driver.login("admin", "admin")

        # Let's create a new contest.
        contest_id = "c" + str(self.get_next_id())
        contest_name = "simple contest " + contest_id
        driver.get("/admin/contests/contest/add/")
        driver.wait_for_load()
        Select(driver.find_element_by_id("id_controller_name")).\
                select_by_visible_text("Simple programming contest")
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
        driver.find_element_by_id("id_package_file").send_keys(
                "../oioioi/sinolpack/files/test_full_package.tgz")
        self.get_primary_button_with_text("Submit").click()
        driver.wait_for_load()

        # Wait for problem package to process, at most ~25s.
        self.wait_for_action(self.wait_for_package, timeout=25,
                             url="/admin/problems/problempackage/")

        # Submit some dummy code as administrator.
        driver.get("/c/" + contest_id + "/submit/")
        driver.find_element_by_id("id_code").clear()
        driver.find_element_by_id("id_code").send_keys("int main(){}")
        Select(driver.find_element_by_id("id_prog_lang")).\
                select_by_visible_text("C")
        Select(driver.find_element_by_id("id_kind")).\
                select_by_visible_text("Normal")
        driver.find_element_by_css_selector(
                "div.form-group > button.btn.btn-primary").click()
        driver.wait_for_load()

        # Check if it was submitted.
        driver.get("/c/" + contest_id + "/admin/contests/submission/")

        self.get_from_result_table(
            "//th[@class='field-id']", 1).click()
        driver.wait_for_load()
        submission_url = driver.current_url

        # Wait for it to be judged, at most 1 min.
        self.wait_for_action(self.wait_for_submission_result,
                             url=submission_url)

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
