import time

from oioioi.base.cache import FaultTolerantPyMemcacheCache
from oioioi.base.tests import TestCase


class TestFaultTolerantPyMemcacheCache(TestCase):
    def test_unreachable_server_is_a_miss(self):
        # Nothing listens on port 1, so every operation fails to connect.
        cache = FaultTolerantPyMemcacheCache("127.0.0.1:1", {})
        with self.assertLogs("oioioi.base.cache", "WARNING"):
            self.assertIsNone(cache.get("key"))
        self.assertEqual(cache.get("key", "default"), "default")
        self.assertEqual(cache.get_many(["a", "b"]), {})
        self.assertFalse(cache.add("key", 1))
        cache.set("key", 1)
        self.assertEqual(cache.set_many({"a": 1}), ["a"])
        self.assertFalse(cache.delete("key"))
        cache.delete_many(["a"])

    def test_unresponsive_server_times_out_quickly(self):
        # address in TEST-NET-2 range for documentation and examples, shouldn't be reachable
        cache = FaultTolerantPyMemcacheCache("198.51.100.42:1", {})

        start = time.perf_counter()
        with self.assertLogs("oioioi.base.cache", "WARNING"):
            self.assertIsNone(cache.get("key"))
        self.assertLess(time.perf_counter() - start, 1)
