"""check_freshness(): stale, recent and undated are three different things."""

import time
import unittest

from helpers import provenreal as pr


def fresh(command, days=30, normalize=None):
    s = {"name": "f", "sources": [],
         "freshness": {"name": "dates", "days": days, "command": command}}
    if normalize:
        s["normalize"] = normalize
    return pr.check_freshness(s)


TODAY = time.strftime("%Y-%m-%d")


class Freshness(unittest.TestCase):

    def test_no_freshness_declared(self):
        self.assertIsNone(pr.check_freshness({"name": "s", "sources": []}))

    def test_old_key_is_stale(self):
        r = fresh("printf 'a\\t2020-01-01\\n'")
        self.assertEqual([v["key"] for v in r["stale"]], ["a"])
        self.assertEqual(r["recent"], 0)

    def test_recent_key_is_not_stale(self):
        r = fresh("printf 'a\\t%s\\n' " + TODAY)
        self.assertEqual(r["stale"], [])
        self.assertEqual(r["recent"], 1)

    def test_key_without_date_is_undated_not_stale(self):
        r = fresh("printf 'a\\n'")
        self.assertEqual(r["undated"], ["a"])
        self.assertEqual(r["stale"], [])

    def test_garbage_date_is_undated(self):
        r = fresh("printf 'a\\tyesterday\\n'")
        self.assertEqual(r["undated"], ["a"])

    def test_accepted_legacy_formats(self):
        r = fresh("printf 'a\\t2020-01-01 10:00:00\\nb\\t2020-01-01T10:00:00\\n"
                  "c\\t2020-01-01\\n'")
        self.assertEqual(len(r["stale"]), 3)
        self.assertEqual(r["undated"], [])

    def test_threshold_is_respected(self):
        r = fresh("printf 'a\\t2020-01-01\\n'", days=100000)
        self.assertEqual(r["stale"], [])
        self.assertEqual(r["recent"], 1)

    def test_failed_command_is_reported(self):
        r = fresh("exit 4")
        self.assertIn("exit 4", r["failed"])

    def test_normalisation_applies_to_freshness_keys(self):
        r = fresh("printf 'WWW.A\\n'", normalize=[{"type": "lowercase"}])
        self.assertEqual(r["undated"], ["www.a"])


if __name__ == "__main__":
    unittest.main()
