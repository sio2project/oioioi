import json
import urllib.parse

import pytest
from django.urls import reverse

from oioioi.base.tests import TestCase, TestsUtilsMixin
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.evalmgr.models import SavedEnviron
from oioioi.problems.models import Problem
from oioioi.programs.models import ProgramSubmission
from oioioi.sinolpack.tests import get_test_filename
from oioioi.zeus import handlers
from oioioi.zeus.backends import (
    Base64String,
    ZeusServer,
    _json_base64_decode,
    _json_base64_encode,
)
from oioioi.zeus.controllers import ZeusProblemController
from oioioi.zeus.models import ZeusProblemData
from oioioi.zeus.utils import verify_zeus_url_signature, zeus_url_signature


class ZeusDummyServer(ZeusServer):
    # pylint: disable=super-init-not-called
    def __init__(self, zeus_id, server_info):
        pass

    def send_regular(self, zeus_problem_id, kind, source_code, language, submission_id, return_url):
        pass


def _updated_copy(dict1, dict2):
    new_dict = dict1.copy()
    new_dict.update(dict2)
    return new_dict


class ZeusJsonTest(TestCase):
    def setUp(self):
        self._ob = {
            "dict": {"key": Base64String("somestring")},
            "key": Base64String("string"),
        }
        self._ob_json = '{"dict": {"key": "c29tZXN0cmluZw=="}, "key": "c3RyaW5n"}'

        with open("oioioi/zeus/fixtures/test_zeus_data.json") as f:
            self._jsons = [f["result"] for f in json.load(f)]

        self._json_base64_decode = lambda v: _json_base64_decode(v, wrap=True)

    def test_json_base64_encode(self):
        self.assertEqual(_json_base64_encode(self._ob), self._ob_json)

    def test_json_base64_decode(self):
        self.assertEqual(self._ob, self._json_base64_decode(self._ob_json))
        for j in self._jsons:
            self._json_base64_decode(j)

    def test_json_base64_identity(self):
        self.assertEqual(self._ob, self._json_base64_decode(_json_base64_encode(self._ob)))
        self.assertEqual(self._ob_json, _json_base64_encode(self._json_base64_decode(self._ob_json)))
        for j in self._jsons:
            self.assertEqual(j, _json_base64_encode(self._json_base64_decode(j)))


class ZeusSignatureTest(TestCase):
    def test_correct_signature(self):
        check_uid = "ZeusSubmissionIdIsARandomString"
        signature = zeus_url_signature(check_uid)
        self.assertTrue(verify_zeus_url_signature(check_uid, signature))

    def test_incorrect_signature(self):
        check_uid = "ZeusSubmissionIdIsARandomString"
        signature = zeus_url_signature("Blah")
        self.assertFalse(verify_zeus_url_signature(check_uid, signature))


class ZeusHandlersTest(TestsUtilsMixin, TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_submission",
        "test_zeus_problem",
    ]

    def _verify_metadata_decoder(self, data):
        self.assertAllIn(["name", "group", "max_score"], data)

    def test_csv_metadata_decoder(self):
        def check_str(metadata, name, group, score):
            data = handlers.from_csv_metadata(metadata)
            self._verify_metadata_decoder(data)
            self.assertEqual(data, {"name": name, "group": group, "max_score": score})

        check_str("1b,1,99", "1b", "1", 99)
        check_str("test32d  ,  ,  123", "test32d", "test32d", 123)

    def _get_base_test_info(self, metadata=""):
        return {
            "verdict": "OK",
            "metadata": metadata,
            "runtime": 100,
            "time_limit_ms": 1000,
            "memory_limit_byte": 2**24,
        }

    def _assert_dict_contains_subset(self, subset, dictionary):
        """Replacement for deprecated assertDictContainsSubset"""
        self.assertEqual(dict(dictionary, **subset), dictionary)

    def test_assert_dict_contains_subset(self):
        self._assert_dict_contains_subset({"a": "a"}, {"a": "a", "b": "b"})
        self._assert_dict_contains_subset({}, {"a": "a", "b": "b"})
        self._assert_dict_contains_subset({"a": {"a": "a"}}, {"a": {"a": "a"}, "b": "b"})
        self._assert_dict_contains_subset({"a": "a", "b": "b"}, {"a": "a", "b": "b"})

    @pytest.mark.xfail
    def test_assert_dict_contains_subset_fail_no_overlap(self):
        self._assert_dict_contains_subset({"c": "a"}, {"a": "a", "b": "b"})

    @pytest.mark.xfail
    def test_assert_dict_contains_subset_fail_wrong_value(self):
        self._assert_dict_contains_subset({"a": "b"}, {"a": "a", "b": "b"})

    @pytest.mark.xfail
    def test_assert_dict_contains_subset_fail_not_full_overlap(self):
        self._assert_dict_contains_subset({"a": "a", "b": "b", "c": "a"}, {"a": "a", "b": "b"})

    @pytest.mark.xfail
    def test_assert_dict_contains_subset_fail_empty_dict(self):
        self._assert_dict_contains_subset({"c": "a"}, {})

    def test_compilation_failure(self):
        test_info = self._get_base_test_info()

        results = [
            _updated_copy(test_info, {"metadata": "0a,0,0"}),
            _updated_copy(test_info, {"metadata": "0b,0,0"}),
        ]
        env = {"zeus_results": results, "compilation_result": "CE"}
        env = handlers.import_results(env, kind="INITIAL")
        self.assertNotIn("tests", env)
        self.assertNotIn("test_results", env)

    def test_importing(self):
        test_info = self._get_base_test_info()
        test_info_2 = _updated_copy(test_info, {"metadata": "2,2,55"})

        results = [
            _updated_copy(test_info, {"metadata": "1a,1,2"}),
            _updated_copy(test_info, {"metadata": "1b,1,2", "verdict": "Wrong answer"}),
            test_info_2,
        ]
        env = {"zeus_results": results, "compilation_result": "OK"}
        env = handlers.import_results(env)
        self.assertEqual(env["compilation_result"], "OK")

        tests = env["tests"]
        test_results = env["test_results"]
        self.assertEqual(len(tests), 3)
        self.assertEqual(len(test_results), 3)
        self.assertAllIn(["1a", "1b", "2"], tests)

        self._assert_dict_contains_subset(
            {
                "name": "1a",
                "kind": "NORMAL",
                "group": "1",
                "max_score": 2,
                "exec_time_limit": 1000,
                "exec_memory_limit": 2**14,
                "zeus_metadata": "1a,1,2",
            },
            tests["1a"],
        )
        self._assert_dict_contains_subset(
            {"result_code": "WA", "result_string": "", "time_used": 100},
            test_results["1b"],
        )
        self.assertDictEqual(test_info_2, test_results["2"]["zeus_test_result"])

        env["zeus_results"].append(self._get_base_test_info(metadata="0,0,0"))
        env = handlers.import_results(env)
        self.assertEqual(len(tests), 4)
        self.assertEqual(len(test_results), 4)
        self._assert_dict_contains_subset({"name": "0", "kind": "EXAMPLE"}, env["tests"]["0"])


class ZeusViewsTest(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_submission",
        "test_zeus_problem",
    ]

    def test_push_grade(self):
        submission = ProgramSubmission.objects.get()
        problem = Problem.objects.get(id=1)
        problem.controller_name = "oioioi.zeus.tests.ZeusProblemController"
        problem.save()
        ZeusProblemController(problem).judge(submission)
        self.assertEqual(SavedEnviron.objects.count(), 1)

        saved_environ = SavedEnviron.objects.get()
        saved_environ_id = saved_environ.id
        signature = zeus_url_signature(saved_environ_id)

        url = reverse(
            "zeus_push_grade_callback",
            kwargs={"saved_environ_id": saved_environ_id, "signature": signature},
        )
        data = {"compilation_output": Base64String("CE")}
        response = self.client.post(url, _json_base64_encode(data), follow=True, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        submission = ProgramSubmission.objects.get()
        self.assertEqual(submission.status, "CE")


class TestZeusProblemUpload(TestCase):
    fixtures = ["test_users", "test_contest"]

    def test_upload_package(self):
        ProblemInstance.objects.all().delete()

        contest = Contest.objects.get()
        filename = get_test_filename("test_simple_package.zip")
        self.assertTrue(self.client.login(username="test_admin"))
        url = reverse("add_or_update_problem", kwargs={"contest_id": contest.id}) + "?" + urllib.parse.urlencode({"key": "zeus"})
        data = {
            "package_file": open(filename, "rb"),
            "zeus_id": "dummy",
            "zeus_problem_id": 1,
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(ProblemInstance.objects.count(), 2)
        self.assertEqual(ZeusProblemData.objects.count(), 1)
        self.assertEqual(SavedEnviron.objects.count(), 2)
