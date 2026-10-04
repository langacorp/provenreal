"""The command line: report, exit codes, JSON, self-test, version."""

import json
import subprocess
import sys
import unittest

from helpers import SCRIPT, provenreal as pr, report_rc, run_cli, src, subject

AGREEING = subject("ok", [src("A", "printf 'a\\n'"), src("B", "printf 'a\\n'")])
DIVERGING = subject("bad", [src("A", "printf 'a\\n'"), src("B", "printf 'b\\n'")])
SINGLE = subject("single", [src("only", "printf 'a\\n'")])


class TextReport(unittest.TestCase):

    def test_exit_0_when_everything_agrees(self):
        rc, out, _ = run_cli({"subjects": [AGREEING]})
        self.assertEqual(rc, 0, out)
        self.assertIn("they agree", out)

    def test_exit_1_on_divergence(self):
        rc, out, _ = run_cli({"subjects": [DIVERGING]})
        self.assertEqual(rc, 1, out)
        self.assertIn("only A: a", out)
        self.assertIn("only B: b", out)

    def test_exit_2_when_no_comparison_was_made(self):
        rc, out, _ = run_cli({"subjects": [SINGLE]})
        self.assertEqual(rc, 2, out)
        self.assertIn("NO COMPARISON WAS MADE", out)

    def test_exit_1_on_false_claim(self):
        s = dict(AGREEING, claimed=7)
        rc, out, _ = run_cli({"subjects": [s]})
        self.assertEqual(rc, 1, out)
        self.assertIn("CLAIMED 7", out)

    def test_exit_1_on_stale_keys(self):
        s = dict(AGREEING, freshness={"name": "d", "days": 30,
                                      "command": "printf 'a\\t2020-01-01\\n'"})
        rc, out, _ = run_cli({"subjects": [s]})
        self.assertEqual(rc, 1, out)
        self.assertIn("past 30 days", out)

    def test_provenance_is_printed(self):
        rc, out, _ = run_cli({"subjects": [AGREEING]})
        self.assertIn("from: printf 'a\\n'", out)

    def test_normalisation_is_declared_in_the_report(self):
        s = dict(AGREEING, normalize=[{"type": "lowercase"}])
        _, out, _ = run_cli({"subjects": [s]})
        self.assertIn("normalisation applied to ALL of them", out)

    def test_failed_source_is_printed_as_not_measured(self):
        s = subject("s", [src("A", "printf 'a\\n'"), src("B", "printf 'a\\n'"),
                          src("C", "exit 9")])
        rc, out, _ = run_cli({"subjects": [s]})
        self.assertIn("NOT MEASURED", out)
        self.assertIn("not measured: C", out)


class Json(unittest.TestCase):

    def test_json_structure(self):
        rc, out, _ = run_cli({"subjects": [AGREEING]}, "--json")
        data = json.loads(out)
        self.assertEqual(data["version"], pr.__version__)
        self.assertEqual(data["subjects"][0]["verdict"], pr.AGREE)
        self.assertEqual(rc, 0)

    def test_json_exit_1_on_divergence(self):
        rc, _, _ = run_cli({"subjects": [DIVERGING]}, "--json")
        self.assertEqual(rc, 1)


class Flags(unittest.TestCase):

    def test_selftest_passes(self):
        r = subprocess.run([sys.executable, SCRIPT, "--selftest"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("self-test passed", r.stdout)

    def test_version_prints_the_constant(self):
        r = subprocess.run([sys.executable, SCRIPT, "--version"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), pr.__version__)

    def test_missing_config_flag_is_a_usage_error(self):
        r = subprocess.run([sys.executable, SCRIPT],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertIn("--config is required", r.stderr)


class ReportFunction(unittest.TestCase):

    def test_report_of_nothing_is_not_a_pass(self):
        rc, out = report_rc([])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
