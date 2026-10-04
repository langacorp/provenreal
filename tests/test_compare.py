"""Verdicts of compare(), each exercised in the direction where it must fire
and in the one where it must stay silent."""

import unittest

from helpers import provenreal as pr, src, subject


class CompareVerdicts(unittest.TestCase):

    def test_diverge_fires_on_different_sets(self):
        r = pr.compare(subject("s", [src("A", "printf 'one\\ntwo\\n'"),
                                     src("B", "printf 'one\\nthree\\n'")]))
        self.assertEqual(r["verdict"], pr.DIVERGE)
        c = r["comparisons"][0]
        self.assertEqual(c["only_in_a"], ["two"])
        self.assertEqual(c["only_in_b"], ["three"])
        self.assertEqual(c["in_both"], 1)
        self.assertEqual(c["verdict"], pr.DIVERGE)

    def test_agree_on_same_set_in_another_order(self):
        r = pr.compare(subject("s", [src("A", "printf 'one\\ntwo\\n'"),
                                     src("B", "printf 'two\\none\\n'")]))
        self.assertEqual(r["verdict"], pr.AGREE)
        self.assertEqual(r["comparisons"][0]["verdict"], pr.AGREE)

    def test_blank_lines_and_surrounding_spaces_are_not_keys(self):
        r = pr.compare(subject("s", [src("A", "printf '  one \\n\\n\\ntwo\\n'"),
                                     src("B", "printf 'one\\ntwo\\n'")]))
        self.assertEqual(r["verdict"], pr.AGREE)
        self.assertEqual(r["sources"][0]["lines"], 2)

    def test_failed_source_is_unmeasured_not_empty(self):
        r = pr.compare(subject("s", [src("A", "printf 'one\\n'"),
                                     src("broken", "echo nope >&2; exit 3")]))
        self.assertEqual(r["verdict"], pr.UNMEASURED)
        self.assertEqual(r["coverage"]["sources_failed"], 1)
        reason = r["coverage"]["not_measured"][0]["reason"]
        self.assertIn("exit 3", reason)
        self.assertIn("nope", reason)
        self.assertEqual(r["comparisons"], [])

    def test_empty_source_that_succeeds_is_a_set_with_no_keys(self):
        # The documented limit: an empty answer is not a failure.
        r = pr.compare(subject("s", [src("A", "printf 'one\\n'"),
                                     src("B", "true")]))
        self.assertEqual(r["verdict"], pr.DIVERGE)
        self.assertIsNone(r["sources"][1]["failed"])

    def test_two_failed_sources_are_unmeasured(self):
        r = pr.compare(subject("s", [src("A", "exit 1"), src("B", "exit 2")]))
        self.assertEqual(r["verdict"], pr.UNMEASURED)
        self.assertEqual(r["coverage"]["sources_answered"], 0)

    def test_three_sources_one_failed_still_compares_the_two(self):
        r = pr.compare(subject("s", [src("A", "printf 'x\\n'"),
                                     src("B", "printf 'x\\n'"),
                                     src("C", "exit 5")]))
        self.assertEqual(r["verdict"], pr.AGREE)
        self.assertEqual(r["coverage"]["sources_failed"], 1)
        self.assertEqual(len(r["comparisons"]), 1)

    def test_three_sources_compared_pairwise(self):
        r = pr.compare(subject("s", [src("A", "printf 'x\\n'"),
                                     src("B", "printf 'x\\n'"),
                                     src("C", "printf 'y\\n'")]))
        self.assertEqual(len(r["comparisons"]), 3)
        self.assertEqual(r["verdict"], pr.DIVERGE)

    def test_timeout_is_unmeasured(self):
        s = pr.Source("slow", "sleep 3").run(timeout=1)
        self.assertIn("timed out", s.failed)

    def test_every_source_reports_its_command(self):
        r = pr.compare(subject("s", [src("A", "printf 'a\\n'"),
                                     src("B", "exit 1")]))
        self.assertEqual([f["command"] for f in r["sources"]],
                         ["printf 'a\\n'", "exit 1"])


class Claimed(unittest.TestCase):

    def test_claimed_that_does_not_hold_fires(self):
        r = pr.compare(subject("s", [src("A", "printf 'a\\nb\\nc\\n'"),
                                     src("B", "printf 'a\\nb\\nc\\n'")],
                               claimed=5))
        self.assertEqual(r["verdict"], pr.DIVERGE)
        self.assertFalse(r["claimed_vs_measured"]["agrees"])

    def test_claimed_that_holds_stays_silent(self):
        r = pr.compare(subject("s", [src("A", "printf 'a\\nb\\nc\\n'"),
                                     src("B", "printf 'a\\nb\\nc\\n'")],
                               claimed=3))
        self.assertEqual(r["verdict"], pr.AGREE)
        self.assertTrue(r["claimed_vs_measured"]["agrees"])

    def test_claimed_null_is_not_checked(self):
        r = pr.compare(subject("s", [src("A", "printf 'a\\n'"),
                                     src("B", "printf 'a\\n'")], claimed=None))
        self.assertNotIn("claimed_vs_measured", r)
        self.assertEqual(r["verdict"], pr.AGREE)


class Normalize(unittest.TestCase):

    def test_each_rule(self):
        n = pr.apply_normalize
        self.assertEqual(n("ABC", [{"type": "lowercase"}]), "abc")
        self.assertEqual(n("www.a", [{"type": "strip-prefix", "value": "www."}]), "a")
        self.assertEqual(n("a.", [{"type": "strip-suffix", "value": "."}]), "a")
        self.assertEqual(n("a1b2", [{"type": "regex", "find": "[0-9]"}]), "ab")
        self.assertEqual(n("a1", [{"type": "regex", "find": "1", "replace": "X"}]), "aX")
        self.assertEqual(n(" a ", [{"type": "trim"}]), "a")

    def test_rules_apply_in_order(self):
        spec = [{"type": "strip-prefix", "value": "www."}, {"type": "lowercase"}]
        self.assertEqual(pr.apply_normalize("WWW.A", spec), "www.a")
        self.assertEqual(pr.apply_normalize("WWW.A", spec[::-1]), "a")

    def test_prefix_not_present_is_left_alone(self):
        self.assertEqual(pr.apply_normalize(
            "one.example", [{"type": "strip-prefix", "value": "www."}]),
            "one.example")

    def test_normalisation_applies_to_every_source(self):
        norm = [{"type": "strip-prefix", "value": "www."}]
        r = pr.compare(subject("s", [
            src("server", "printf 'www.one.example\\n'"),
            src("table", "printf 'one.example\\n'")], normalize=norm))
        self.assertEqual(r["verdict"], pr.AGREE)

    def test_without_normalisation_the_same_pair_diverges(self):
        r = pr.compare(subject("s", [
            src("server", "printf 'www.one.example\\n'"),
            src("table", "printf 'one.example\\n'")]))
        self.assertEqual(r["verdict"], pr.DIVERGE)


if __name__ == "__main__":
    unittest.main()
