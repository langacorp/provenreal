"""Shared helpers for the tests. Standard library only, no network."""

import io
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import provenreal  # noqa: E402

SCRIPT = os.path.join(ROOT, "provenreal.py")


def src(name, command):
    return {"name": name, "command": command}


def subject(name, sources, **kw):
    d = {"name": name, "sources": sources}
    d.update(kw)
    return d


def run_cli(cfg, *args):
    """Run the tool as a user would, on a config written to a temp dir.

    `cfg` is a dict (written as JSON) or a str (written as is).
    Returns (exit code, stdout, stderr).
    """
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "subjects.json")
        with open(path, "w", encoding="utf-8") as fh:
            if isinstance(cfg, str):
                fh.write(cfg)
            else:
                json.dump(cfg, fh)
        r = subprocess.run([sys.executable, SCRIPT, "-c", path] + list(args),
                           capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout, r.stderr


def report_rc(results):
    buf = io.StringIO()
    rc = provenreal.report(results, buf)
    return rc, buf.getvalue()
