from oioioi.base.cache import FaultTolerantPyLibMCCache
from oioioi.base.tests import TestCase


class TestFaultTolerantPyLibMCCache(TestCase):
    def test_unreachable_server_is_a_miss(self):
        # Nothing listens on port 1, so every operation fails to connect.
        cache = FaultTolerantPyLibMCCache("127.0.0.1:1", {})
        with self.assertLogs("oioioi.base.cache", "WARNING"):
            self.assertIsNone(cache.get("key"))
        self.assertEqual(cache.get("key", "default"), "default")
        self.assertEqual(cache.get_many(["a", "b"]), {})
        self.assertFalse(cache.add("key", 1))
        cache.set("key", 1)
        self.assertEqual(cache.set_many({"a": 1}), ["a"])
        self.assertFalse(cache.delete("key"))
        cache.delete_many(["a"])
