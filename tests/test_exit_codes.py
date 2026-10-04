"""Exit codes must say the same thing in text and in JSON, and a subject that
was not measured must never let the run exit as a pass."""

import unittest

from helpers import run_cli, src, subject

AGREEING = subject("ok", [src("A", "printf 'a\\n'"), src("B", "printf 'a\\n'")])
DIVERGING = subject("bad", [src("A", "printf 'a\\n'"), src("B", "printf 'b\\n'")])
BROKEN = subject("broken", [src("A", "exit 3"), src("B", "exit 4")])
SINGLE = subject("single", [src("only", "printf 'a\\n'")])
STALE = dict(AGREEING, freshness={"name": "d", "days": 30,
                                  "command": "printf 'a\\t2020-01-01\\n'"})


class ExitCodes(unittest.TestCase):

    def both(self, subjects):
        rc_text, out, _ = run_cli({"subjects": subjects})
        rc_json, _, _ = run_cli({"subjects": subjects}, "--json")
        return rc_text, rc_json, out

    def test_single_source_is_2_in_json_too(self):
        self.assertEqual(self.both([SINGLE])[:2], (2, 2))

    def test_stale_keys_are_1_in_json_too(self):
        self.assertEqual(self.both([STALE])[:2], (1, 1))

    def test_agreeing_is_0_in_both(self):
        self.assertEqual(self.both([AGREEING])[:2], (0, 0))

    def test_diverging_is_1_in_both(self):
        self.assertEqual(self.both([DIVERGING])[:2], (1, 1))

    def test_one_subject_agrees_one_not_measured_is_not_a_pass(self):
        rc_text, rc_json, out = self.both([AGREEING, BROKEN])
        self.assertEqual((rc_text, rc_json), (2, 2))
        self.assertIn("NOT MEASURED", out)
        self.assertIn("This is not a pass", out)

    def test_freshness_that_failed_is_not_a_pass(self):
        s = dict(AGREEING, freshness={"name": "d", "days": 30,
                                      "command": "exit 7"})
        rc_text, rc_json, out = self.both([s])
        self.assertEqual((rc_text, rc_json), (2, 2))
        self.assertIn("freshness NOT MEASURED", out)

    def test_freshness_of_an_unmeasured_subject_is_still_printed(self):
        s = dict(SINGLE, freshness={"name": "d", "days": 30,
                                    "command": "printf 'a\\t2020-01-01\\n'"})
        rc_text, rc_json, out = self.both([s])
        self.assertIn("past 30 days", out)
        self.assertIn("NO COMPARISON WAS MADE", out)
        self.assertEqual((rc_text, rc_json), (1, 1))

    def test_divergence_wins_over_not_measured(self):
        self.assertEqual(self.both([DIVERGING, BROKEN])[:2], (1, 1))


if __name__ == "__main__":
    unittest.main()
