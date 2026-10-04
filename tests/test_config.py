"""A configuration error is not a divergence and not a pass.

Before anything runs, the configuration is checked. Every case here was
measured on the code before this check existed: some crashed with a
traceback and exit 1 (the exit code for divergence), others ran and gave a
wrong verdict without saying so.
"""

import os
import subprocess
import sys
import tempfile
import unittest

from helpers import SCRIPT, run_cli, src, subject

OK_SOURCES = [src("A", "printf 'a\\n'"), src("B", "printf 'a\\n'")]


class ConfigErrors(unittest.TestCase):

    def assertConfigError(self, cfg, needle):
        rc, out, err = run_cli(cfg)
        self.assertEqual(rc, 2, out + err)
        self.assertNotIn("Traceback", err)
        self.assertIn(needle, err)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, SCRIPT, "-c",
                                os.path.join(d, "absent.json")],
                               capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("absent.json", r.stderr)

    def test_invalid_json(self):
        self.assertConfigError("{not json", "not valid JSON")

    def test_no_subjects_key(self):
        self.assertConfigError({"subject": []}, "subjects")

    def test_source_without_command(self):
        self.assertConfigError(
            {"subjects": [subject("s", [{"name": "A"}, OK_SOURCES[1]])]},
            "command")

    def test_strip_prefix_without_value(self):
        self.assertConfigError(
            {"subjects": [subject("s", OK_SOURCES,
                                  normalize=[{"type": "strip-prefix"}])]},
            "value")

    def test_freshness_days_not_a_number(self):
        self.assertConfigError(
            {"subjects": [subject("s", OK_SOURCES, freshness={
                "name": "d", "days": "thirty", "command": "true"})]},
            "days")


class SilentWrongResults(unittest.TestCase):
    """Configs that ran, and gave a verdict that was not what they declared."""

    def assertConfigError(self, cfg, needle):
        rc, out, err = run_cli(cfg)
        self.assertEqual(rc, 2, out + err)
        self.assertIn(needle, err)

    def test_unknown_normalize_rule_is_rejected(self):
        # Before: "lower-case" was skipped, the report said normalisation was
        # applied to every source, and ONE against one diverged.
        cfg = {"subjects": [subject("s", [
            src("A", "printf 'ONE\\n'"), src("B", "printf 'one\\n'")],
            normalize=[{"type": "lower-case"}])]}
        self.assertConfigError(cfg, "lower-case")

    def test_claimed_as_string_is_rejected(self):
        # Before: "25" was not an int, so the claim was never checked and the
        # subject agreed.
        cfg = {"subjects": [subject("s", OK_SOURCES, claimed="25")]}
        self.assertConfigError(cfg, "claimed")

    def test_claimed_as_boolean_is_rejected(self):
        # Before: true was compared as the number 1.
        cfg = {"subjects": [subject("s", OK_SOURCES, claimed=True)]}
        self.assertConfigError(cfg, "claimed")

    def test_duplicate_source_names_are_rejected(self):
        # Before: claimed 5, sources with 3 and 5 keys, both named "db".
        # The measured counts were keyed by name, the 3 was overwritten,
        # and the claim was reported as holding.
        cfg = {"subjects": [subject("s", [
            src("db", "printf 'a\\nb\\nc\\n'"),
            src("db", "printf 'a\\nb\\nc\\nd\\ne\\n'")], claimed=5)]}
        self.assertConfigError(cfg, "db")

    def test_valid_config_still_runs(self):
        cfg = {"subjects": [subject("s", OK_SOURCES, claimed=1,
                                    normalize=[{"type": "trim"}])]}
        rc, out, err = run_cli(cfg)
        self.assertEqual(rc, 0, out + err)


if __name__ == "__main__":
    unittest.main()
