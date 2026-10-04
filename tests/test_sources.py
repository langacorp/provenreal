"""How a source's output becomes keys, and what is left behind when it fails."""

import os
import tempfile
import time
import unittest

from helpers import provenreal as pr, src, subject


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # A zombie still answers kill(0); read its state where /proc exists.
    try:
        with open(f"/proc/{pid}/stat") as fh:
            return fh.read().split(")")[-1].split()[0] != "Z"
    except OSError:
        return True


class Encoding(unittest.TestCase):

    def test_two_different_undecodable_keys_stay_two(self):
        # Before: b'caf\xe9' and b'caf\xe8' both decoded to 'caf\ufffd',
        # became one key, and the comparison agreed with a source that had
        # only one of them.
        r = pr.compare(subject("s", [
            src("A", "printf 'caf\\351\\ncaf\\350\\n'"),
            src("B", "printf 'caf\\351\\n'")]))
        self.assertEqual(r["sources"][0]["keys"], 2)
        self.assertEqual(r["verdict"], pr.DIVERGE)

    def test_undecodable_keys_can_be_printed_and_dumped(self):
        from helpers import run_cli
        cfg = {"subjects": [subject("s", [
            src("A", "printf 'caf\\351\\n'"), src("B", "printf 'x\\n'")])]}
        rc, out, err = run_cli(cfg)
        self.assertEqual(rc, 1, err)
        self.assertIn("caf\\xe9", out)
        rc, out, err = run_cli(cfg, "--json")
        self.assertEqual(rc, 1, err)
        self.assertIn("caf\\\\xe9", out)

    def test_same_undecodable_bytes_still_agree(self):
        r = pr.compare(subject("s", [src("A", "printf 'caf\\351\\n'"),
                                     src("B", "printf 'caf\\351\\n'")]))
        self.assertEqual(r["verdict"], pr.AGREE)

    def test_utf8_is_read_as_utf8(self):
        r = pr.compare(subject("s", [src("A", "printf 'caf\\303\\251\\n'"),
                                     src("B", "printf 'café\\n'")]))
        self.assertEqual(r["verdict"], pr.AGREE)

    def test_crlf_line_endings_are_not_part_of_the_key(self):
        r = pr.compare(subject("s", [src("A", "printf 'a\\r\\nb\\r\\n'"),
                                     src("B", "printf 'a\\nb\\n'")]))
        self.assertEqual(r["verdict"], pr.AGREE)


class Timeout(unittest.TestCase):

    def test_timed_out_source_leaves_no_process_behind(self):
        # Before: the shell was killed, its child kept running after the
        # report was printed.
        with tempfile.TemporaryDirectory() as d:
            pidfile = os.path.join(d, "pid")
            cmd = f"sleep 30 & echo $! > {pidfile}; wait"
            s = pr.Source("slow", cmd).run(timeout=1)
            self.assertIn("timed out", s.failed)
            with open(pidfile) as fh:
                pid = int(fh.read())
            deadline = time.time() + 3
            while alive(pid) and time.time() < deadline:
                time.sleep(0.05)
            still = alive(pid)
            if still:
                os.kill(pid, 9)
            self.assertFalse(still, "the source's child outlived the timeout")

    def test_timeout_returns_on_time(self):
        t0 = time.time()
        pr.Source("slow", "sleep 30").run(timeout=1)
        self.assertLess(time.time() - t0, 5)

    def test_freshness_timeout_is_reported(self):
        fr = pr.check_freshness({"name": "s", "sources": [], "freshness": {
            "name": "d", "command": "sleep 30"}}, timeout=1)
        self.assertIn("timed out", fr["failed"])


class FreshnessDates(unittest.TestCase):

    def run_dates(self, lines):
        cmd = "printf '" + "".join(f"{k}\\t{v}\\n" for k, v in lines) + "'"
        return pr.check_freshness({"name": "s", "sources": [], "freshness": {
            "name": "d", "days": 30, "command": cmd}})

    def test_not_a_date_is_still_undated(self):
        r = self.run_dates([("a", "never"), ("b", "0000-00-00 00:00:00"),
                            ("c", "NULL")])
        self.assertEqual(r["undated"], ["a", "b", "c"])
        self.assertEqual(r["stale"], [])

    def test_failed_freshness_keeps_the_reason(self):
        fr = pr.check_freshness({"name": "s", "sources": [], "freshness": {
            "name": "d", "command": "echo 'no such table' >&2; exit 4"}})
        self.assertIn("exit 4", fr["failed"])
        self.assertIn("no such table", fr["failed"])


class FreshnessProvenance(unittest.TestCase):

    def test_freshness_count_carries_its_command(self):
        from helpers import run_cli
        cmd = "printf 'a\\t2020-01-01\\n'"
        cfg = {"subjects": [subject("s", [src("A", "printf 'a\\n'"),
                                          src("B", "printf 'a\\n'")],
                                    freshness={"name": "d", "command": cmd})]}
        _, out, _ = run_cli(cfg)
        self.assertIn("freshness d from: " + cmd, out)
        fr = pr.check_freshness(cfg["subjects"][0])
        self.assertEqual(fr["command"], cmd)
        fr = pr.check_freshness({"name": "s", "sources": [], "freshness": {
            "name": "d", "command": "exit 2"}})
        self.assertEqual(fr["command"], "exit 2")


if __name__ == "__main__":
    unittest.main()
