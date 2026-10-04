#!/usr/bin/env python3
"""Compare what a system CLAIMS with what can be MEASURED.

It answers two questions, not one: **how many**, and **of what**.

THE DEFECT IT WAS BORN FROM — 27 August 2026, all in a single day:

  - SIX different numbers for the same question ("how many services are we"):
    25, 22, 12, 16, one derived from a catalogue that said 26, and one agreed
    verbally. Five public pages, five answers.
  - THREE SETS MIXED IN ONE TABLE: an inventory table counted the systems of
    two different servers together, with no column telling them apart. Every
    count taken from it counted a set nobody had asked for.
  - THE REAL PERIMETER found only by looking at the SERVER instead of the
    DATABASE: 41 installations with the component, against the 47 the table
    reported and a 16 estimated by hand. Three numbers, one measured.

The common shape is always the same: a FULL field saying something other than
what is there. No completeness check sees it, because nothing is missing.

THREE RULES, and they are the three things that went wrong that day:

  1. A SOURCE THAT FAILED IS NOT AN EMPTY SOURCE.
     A command that does not run returns zero lines, exactly like a command
     that runs and finds nothing. Confusing the two is the fastest way to
     declare "they agree" about a comparison that never happened.

  2. NORMALISATION APPLIES TO EVERY SIDE OR TO NONE, AND IT IS DECLARED.
     That day a comparison stripped the "www." prefix from one side only: the
     pairs did not match and the result said "no correspondence". The command
     was right about the wrong comparison.

  3. EVERY COUNT CARRIES ITS OWN PROVENANCE.
     A source name is a label chosen by whoever writes the configuration: it
     can say "table" and query something else entirely. The report prints the
     COMMAND that produced each number. A number without provenance cannot be
     compared with another number.

IT NEVER DECIDES WHICH SOURCE IS RIGHT. It shows where they disagree.
Choosing is a decision, and a decision made silently by a program always picks
the most convenient source, not the truest one.

Standard library only.
"""

import argparse
import calendar
import json
import os
import re
import signal
import subprocess
import sys
import time

__version__ = "0.1.0"

AGREE = "agree"
DIVERGE = "diverge"
UNMEASURED = "unmeasured"


# --------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------

class CommandTimeout(Exception):
    pass


def run_command(command, timeout):
    """Run a shell command; return (returncode, stdout bytes, stderr bytes).

    The command runs in its own process group, and on timeout the whole group
    is killed. Killing only the shell, as subprocess.run does, left its
    children running after the report had already called the source
    unmeasured.
    """
    posix = hasattr(os, "killpg")
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=posix)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if posix:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass  # the group is already gone: nothing left to kill
        else:
            proc.kill()
        proc.communicate()
        raise CommandTimeout(f"timed out after {timeout}s")
    return proc.returncode, out or b"", err or b""


def decode_lines(data):
    """Bytes to lines of text, one key per line.

    Bytes that are not UTF-8 are kept as \\xNN escapes. Replacing them with
    U+FFFD, as before, turned b"caf\\xe9" and b"caf\\xe8" into the same key,
    and two different keys were counted as one.
    """
    return data.decode("utf-8", "backslashreplace").split("\n")


def describe_exit(returncode, stderr):
    err = stderr.decode("utf-8", "replace").strip()
    return f"exit {returncode}" + (f": {err[:120]}" if err else "")


class Source:
    """A source: a command printing one key per line.

    `failed` and `keys == set()` are two DIFFERENT states and must not be
    collapsed into one.
    """

    def __init__(self, name, command, normalize=None):
        self.name = name
        self.command = command
        self.normalize_spec = normalize or []
        self.keys = set()
        self.raw_count = 0
        self.failed = None       # None = fine, string = why it failed
        self.duration = 0.0

    def run(self, timeout=60):
        t0 = time.time()
        try:
            rc, out, err = run_command(self.command, timeout)
        except CommandTimeout as e:
            self.failed = str(e)
            return self
        except OSError as e:
            self.failed = f"{type(e).__name__}: {e}"
            return self
        finally:
            self.duration = round(time.time() - t0, 2)

        if rc != 0:
            self.failed = describe_exit(rc, err)
            return self

        lines = [l.strip() for l in decode_lines(out)]
        lines = [l for l in lines if l]
        self.raw_count = len(lines)
        self.keys = {apply_normalize(l, self.normalize_spec) for l in lines}
        return self

    def as_dict(self):
        return {"name": self.name, "command": self.command,
                "lines": self.raw_count, "keys": len(self.keys),
                "failed": self.failed, "seconds": self.duration}


def apply_normalize(value, spec):
    """Normalisation rules, applied in order.

    These are COMPARISON rules: they hold for every source at once, never for
    one alone. They are declared in the configuration and printed in the
    report, because an undeclared normalisation changes the result silently.
    """
    v = value
    for rule in spec:
        kind = rule.get("type")
        if kind == "lowercase":
            v = v.lower()
        elif kind == "strip-prefix":
            p = rule["value"]
            if v.startswith(p):
                v = v[len(p):]
        elif kind == "strip-suffix":
            s = rule["value"]
            if v.endswith(s):
                v = v[:-len(s)]
        elif kind == "regex":
            v = re.sub(rule["find"], rule.get("replace", ""), v)
        elif kind == "trim":
            v = v.strip()
    return v


NORMALIZE_RULES = {
    "lowercase": (),
    "trim": (),
    "strip-prefix": ("value",),
    "strip-suffix": ("value",),
    "regex": ("find",),
}


class ConfigError(Exception):
    """The configuration does not say what it seems to say."""


def validate_config(cfg):
    """Check the configuration before anything runs.

    A rule with a misspelt type used to be skipped while the report said
    normalisation was applied; a claimed number written as a string was never
    compared; two sources with the same name overwrote each other's count.
    Each of these ran and gave a verdict. A configuration that does not mean
    what it says is refused here instead, with the reason.
    """
    if not isinstance(cfg, dict) or not isinstance(cfg.get("subjects"), list):
        raise ConfigError('the top level must be an object with a "subjects" '
                          'list')
    for i, subj in enumerate(cfg["subjects"]):
        where = f"subjects[{i}]"
        if not isinstance(subj, dict):
            raise ConfigError(f"{where}: must be an object")
        if not isinstance(subj.get("name"), str):
            raise ConfigError(f'{where}: "name" must be a string')
        where = f"subject {subj['name']!r}"

        sources = subj.get("sources")
        if not isinstance(sources, list):
            raise ConfigError(f'{where}: "sources" must be a list')
        seen = set()
        for j, so in enumerate(sources):
            if not isinstance(so, dict):
                raise ConfigError(f"{where}: sources[{j}] must be an object")
            for field in ("name", "command"):
                if not isinstance(so.get(field), str) or not so[field]:
                    raise ConfigError(f'{where}: sources[{j}] needs a '
                                      f'non-empty "{field}" string')
            if so["name"] in seen:
                raise ConfigError(f"{where}: two sources are named "
                                  f"{so['name']!r}; counts are reported by "
                                  f"name, so one would hide the other")
            seen.add(so["name"])

        c = subj.get("claimed")
        if c is not None and (isinstance(c, bool) or not isinstance(c, int)):
            raise ConfigError(f'{where}: "claimed" must be an integer or null, '
                              f'got {c!r}')

        norm = subj.get("normalize", [])
        if not isinstance(norm, list):
            raise ConfigError(f'{where}: "normalize" must be a list')
        for k, rule in enumerate(norm):
            kind = rule.get("type") if isinstance(rule, dict) else None
            if kind not in NORMALIZE_RULES:
                raise ConfigError(f"{where}: normalize[{k}] has unknown type "
                                  f"{kind!r}; known: "
                                  f"{', '.join(sorted(NORMALIZE_RULES))}")
            for field in NORMALIZE_RULES[kind]:
                if not isinstance(rule.get(field), str):
                    raise ConfigError(f'{where}: normalize[{k}] ({kind}) needs '
                                      f'a "{field}" string')
            if kind == "regex":
                if not isinstance(rule.get("replace", ""), str):
                    raise ConfigError(f'{where}: normalize[{k}] (regex) '
                                      f'"replace" must be a string')
                try:
                    re.compile(rule["find"])
                except re.error as e:
                    raise ConfigError(f"{where}: normalize[{k}] (regex) does "
                                      f"not compile: {e}")

        fr = subj.get("freshness")
        if fr is not None:
            if not isinstance(fr, dict):
                raise ConfigError(f'{where}: "freshness" must be an object')
            for field in ("name", "command"):
                if not isinstance(fr.get(field), str) or not fr[field]:
                    raise ConfigError(f'{where}: freshness needs a non-empty '
                                      f'"{field}" string')
            d = fr.get("days", 30)
            if isinstance(d, bool) or not isinstance(d, int) or d < 0:
                raise ConfigError(f'{where}: freshness "days" must be a '
                                  f'non-negative integer, got {d!r}')
    return cfg


# --------------------------------------------------------------------------
# comparison
# --------------------------------------------------------------------------

def compare(subject, timeout=60):
    """Run a subject's sources and compare them pairwise."""
    sources = [Source(s["name"], s["command"],
                      subject.get("normalize", [])).run(timeout)
               for s in subject["sources"]]

    ok_sources = [s for s in sources if s.failed is None]
    failed = [s for s in sources if s.failed is not None]

    result = {
        "subject": subject["name"],
        "claimed": subject.get("claimed"),
        "normalize": subject.get("normalize", []),
        "sources": [s.as_dict() for s in sources],
        "coverage": {
            "sources_declared": len(sources),
            "sources_answered": len(ok_sources),
            "sources_failed": len(failed),
            "not_measured": [{"source": s.name, "reason": s.failed} for s in failed],
        },
        "comparisons": [],
        "verdict": UNMEASURED,
    }

    # Fewer than two sources answered: we CANNOT say they agree.
    # This is the direction where the tool must stay quiet instead of
    # reporting a pass.
    if len(ok_sources) < 2:
        result["note"] = ("fewer than two sources answered: no comparison was "
                          "made")
        return result

    diverging = 0
    for i in range(len(ok_sources)):
        for j in range(i + 1, len(ok_sources)):
            a, b = ok_sources[i], ok_sources[j]
            only_a = sorted(a.keys - b.keys)
            only_b = sorted(b.keys - a.keys)
            both = len(a.keys & b.keys)
            if only_a or only_b:
                diverging += 1
            result["comparisons"].append({
                "a": a.name, "b": b.name,
                "in_both": both,
                "only_in_a": only_a, "only_in_b": only_b,
                "verdict": DIVERGE if (only_a or only_b) else AGREE,
            })

    result["verdict"] = DIVERGE if diverging else AGREE

    # The hand-written number against the measured ones.
    c = subject.get("claimed")
    if isinstance(c, int):
        measured = {s.name: len(s.keys) for s in ok_sources}
        result["claimed_vs_measured"] = {
            "claimed": c, "measured": measured,
            "agrees": all(v == c for v in measured.values()),
        }
        if not result["claimed_vs_measured"]["agrees"]:
            result["verdict"] = DIVERGE
    return result


# --------------------------------------------------------------------------
# freshness
# --------------------------------------------------------------------------

_TS = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}:\d{2})(?:\.\d+)?)?"
                 r"\s*(Z|[+-]\d{2}:?\d{2})?$")


def parse_timestamp(raw):
    """Seconds since the epoch, or None if `raw` is not a date.

    Accepted: YYYY-MM-DD, with an optional time after "T" or a space,
    optional fractional seconds, and an optional "Z" or +HH:MM offset. A date
    with no zone is read in local time, as before. Before, a "Z", an offset
    or a fraction made the key undated, and a key years old was not stale.
    """
    m = _TS.match(raw)
    if not m:
        return None
    date, clock, zone = m.groups()
    try:
        t = time.strptime(f"{date} {clock or '00:00:00'}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    if not zone:
        return time.mktime(t)
    offset = 0
    if zone != "Z":
        z = zone.replace(":", "")
        offset = (int(z[1:3]) * 3600 + int(z[3:5]) * 60) * (1 if z[0] == "+"
                                                             else -1)
    return calendar.timegm(t) - offset


def check_freshness(subject, timeout=60):
    """Last activity against a declared threshold.

    The command prints `key<TAB>ISO-date`. A key with no date is NOT an old
    key: it is an unmeasured key, and it goes in a list of its own.
    """
    spec = subject.get("freshness")
    if not spec:
        return None
    s = Source(spec["name"], spec["command"], subject.get("normalize", []))
    try:
        rc, out, err = run_command(s.command, timeout)
    except CommandTimeout as e:
        return {"source": s.name, "command": s.command, "failed": str(e)}
    except OSError as e:
        return {"source": s.name, "command": s.command,
                "failed": f"{type(e).__name__}: {e}"}
    if rc != 0:
        return {"source": s.name, "command": s.command,
                "failed": describe_exit(rc, err)}

    max_days = int(spec.get("days", 30))
    now = time.time()
    stale, fresh, undated = [], 0, []
    for line in decode_lines(out):
        if not line.strip():
            continue
        parts = line.split("\t")
        key = apply_normalize(parts[0].strip(), subject.get("normalize", []))
        raw = parts[1].strip() if len(parts) > 1 else ""
        ts = parse_timestamp(raw)
        if ts is None:
            undated.append(key)
            continue
        age = (now - ts) / 86400
        if age > max_days:
            stale.append({"key": key, "days": round(age, 1)})
        else:
            fresh += 1
    return {"source": s.name, "command": s.command,
            "threshold_days": max_days, "recent": fresh,
            "stale": sorted(stale, key=lambda x: -x["days"]),
            "undated": sorted(undated), "failed": None}


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def subject_state(res):
    """What one subject's result says, for the exit code.

    DIVERGE if any comparison, the claimed number or freshness disagrees.
    UNMEASURED if nothing disagrees but something declared was not measured:
    no comparison was possible, or the freshness command failed.
    AGREE otherwise.
    """
    fr = res.get("freshness")
    if res["verdict"] == DIVERGE or (fr and not fr.get("failed")
                                     and fr["stale"]):
        return DIVERGE
    if res["verdict"] == UNMEASURED or (fr and fr.get("failed")):
        return UNMEASURED
    return AGREE


def exit_code(results):
    """0 everything measured agrees, 1 divergence, 2 something not measured.

    One function for the text report and for --json, so that the two cannot
    give different answers about the same run. Divergence wins over
    not-measured: it is a finding, and it must not be hidden by a gap.
    """
    states = [subject_state(r) for r in results]
    if DIVERGE in states:
        return 1
    if not states or UNMEASURED in states:
        return 2
    return 0


def report(results, stream=sys.stdout):
    compared = 0
    for res in results:
        c = res["coverage"]
        stream.write(f"\n{res['subject']}\n")
        for f in res["sources"]:
            if f["failed"]:
                stream.write(f"  ! {f['name']:<28} NOT MEASURED — {f['failed']}\n")
            else:
                stream.write(f"    {f['name']:<28} {f['keys']} keys "
                             f"({f['lines']} lines, {f['seconds']}s)\n")
            stream.write(f"      from: {f['command']}\n")

        if res["verdict"] == UNMEASURED:
            stream.write(f"  {res.get('note','')}\n")
        else:
            compared += 1

        for cmp_ in res["comparisons"]:
            if cmp_["verdict"] == AGREE:
                stream.write(f"    {cmp_['a']} = {cmp_['b']}: "
                             f"{cmp_['in_both']} keys, they agree\n")
                continue
            stream.write(f"  ! {cmp_['a']} against {cmp_['b']}: "
                         f"{cmp_['in_both']} in both, "
                         f"{len(cmp_['only_in_a'])} only in {cmp_['a']}, "
                         f"{len(cmp_['only_in_b'])} only in {cmp_['b']}\n")
            for k in cmp_["only_in_a"][:5]:
                stream.write(f"      only {cmp_['a']}: {k}\n")
            for k in cmp_["only_in_b"][:5]:
                stream.write(f"      only {cmp_['b']}: {k}\n")

        cvm = res.get("claimed_vs_measured")
        if cvm and not cvm["agrees"]:
            stream.write(f"  ! CLAIMED {cvm['claimed']}, measured "
                         f"{', '.join(f'{k}={v}' for k, v in cvm['measured'].items())}\n")
            stream.write("    The claimed number does not identify the set. "
                         "Whoever uses it is counting something else.\n")
            for f in res["sources"]:
                if not f["failed"]:
                    stream.write(f"      {f['name']}={f['keys']} from: "
                                 f"{f['command']}\n")

        fr = res.get("freshness")
        if fr:
            stream.write(f"    freshness {fr['source']} from: "
                         f"{fr.get('command')}\n")
        if fr and not fr.get("failed"):
            if fr["stale"]:
                stream.write(f"  ! {len(fr['stale'])} past {fr['threshold_days']} "
                             f"days, {fr['recent']} recent\n")
                for v in fr["stale"][:5]:
                    stream.write(f"      {v['key']} — {v['days']} days\n")
            if fr["undated"]:
                stream.write(f"    {len(fr['undated'])} with no date: they are "
                             f"not stale, they are NOT MEASURED\n")
        elif fr:
            stream.write(f"  ! freshness NOT MEASURED — {fr['failed']}\n")

        stream.write(f"  coverage: {c['sources_answered']}/{c['sources_declared']} "
                     f"sources answered")
        if res["normalize"]:
            stream.write(f", normalisation applied to ALL of them: "
                         f"{[r.get('type') for r in res['normalize']]}")
        stream.write("\n")
        for nm in c["not_measured"]:
            stream.write(f"    not measured: {nm['source']} — {nm['reason']}\n")

    stream.write("\nIt does not say which source is right: it shows where they "
                 "disagree. Choosing is a decision.\n")
    if compared == 0:
        stream.write("NO COMPARISON WAS MADE. This is not a pass.\n")
    else:
        unmeasured = [r["subject"] for r in results
                      if subject_state(r) == UNMEASURED]
        if unmeasured:
            stream.write(f"{len(unmeasured)} of {len(results)} subjects NOT "
                         f"MEASURED in full: {', '.join(unmeasured)}. "
                         f"This is not a pass.\n")
    return exit_code(results)


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def selftest(stream=sys.stdout):
    failures = []

    def subj(name, sources, **kw):
        d = {"name": name, "sources": sources}
        d.update(kw)
        return d

    # ---- direction 1: must fire on two sources that disagree
    r = compare(subj("they-disagree", [
        {"name": "A", "command": "printf 'one\\ntwo\\nthree\\n'"},
        {"name": "B", "command": "printf 'one\\ntwo\\nfour\\n'"},
    ]))
    stream.write("direction 1 - two sources that disagree: must fire\n")
    stream.write(f"  verdict {r['verdict']}, "
                 f"only in A {r['comparisons'][0]['only_in_a']}, "
                 f"only in B {r['comparisons'][0]['only_in_b']}\n")
    if r["verdict"] != DIVERGE:
        failures.append("two diverging sources were not reported")

    # ---- direction 2: must stay silent on two sources that agree
    r = compare(subj("they-agree", [
        {"name": "A", "command": "printf 'one\\ntwo\\n'"},
        {"name": "B", "command": "printf 'two\\none\\n'"},
    ]))
    stream.write("direction 2 - two sources that agree: must stay silent\n")
    stream.write(f"  verdict {r['verdict']}\n")
    if r["verdict"] != AGREE:
        failures.append("two identical sources were reported as diverging")

    # ---- direction 3: a FAILED source is not an empty source
    r = compare(subj("one-failed", [
        {"name": "A", "command": "printf 'one\\ntwo\\n'"},
        {"name": "broken", "command": "exit 3"},
    ]))
    stream.write("direction 3 - a failed source is not an empty source\n")
    stream.write(f"  verdict {r['verdict']}, failed "
                 f"{r['coverage']['sources_failed']}\n")
    if r["verdict"] != UNMEASURED:
        failures.append("a failed source was treated as an empty set: this is "
                        "the defect the tool exists to avoid")
    if r["coverage"]["sources_failed"] != 1:
        failures.append("the failed source was not counted")

    # ---- direction 4: normalisation holds for EVERY source
    norm = [{"type": "strip-prefix", "value": "www."}]
    r = compare(subj("normalised", [
        {"name": "server", "command": "printf 'www.one.example\\nwww.two.example\\n'"},
        {"name": "table", "command": "printf 'one.example\\ntwo.example\\n'"},
    ], normalize=norm))
    stream.write("direction 4 - normalisation applied to every source\n")
    stream.write(f"  verdict {r['verdict']}\n")
    if r["verdict"] != AGREE:
        failures.append("normalisation was not applied to every source: this "
                        "reproduces the defect of 27 August 2026")

    # ---- direction 4b: every count carries its own provenance.
    # A source name is a label chosen by whoever writes the configuration: it
    # can say "table" and query a different set. That is what produced the
    # wrong number on 27 August 2026.
    r = compare(subj("provenance", [
        {"name": "lying-label", "command": "printf 'a\\nb\\n'"},
        {"name": "other", "command": "printf 'a\\n'"},
    ]))
    stream.write("direction 4b - every count carries the command that produced it\n")
    cmds = [f.get("command") for f in r["sources"]]
    stream.write(f"  commands reported: {sum(1 for c in cmds if c)}/{len(cmds)}\n")
    if any(not c for c in cmds):
        failures.append("a source does not report the command behind its count: "
                        "a number without provenance is not comparable")

    # ---- direction 5: claimed against measured
    r = compare(subj("claimed", [
        {"name": "measure", "command": "printf 'a\\nb\\nc\\n'"},
        {"name": "measure2", "command": "printf 'a\\nb\\nc\\n'"},
    ], claimed=5))
    stream.write("direction 5 - a claimed number that does not hold\n")
    stream.write(f"  verdict {r['verdict']}, claimed 5, measured "
                 f"{r['claimed_vs_measured']['measured']}\n")
    if r["verdict"] != DIVERGE:
        failures.append("a false claim was not reported")

    # ---- direction 6: a run with no comparison is not a pass
    import io
    r = compare(subj("single-source", [
        {"name": "only", "command": "printf 'a\\n'"},
    ]))
    rc = report([r], io.StringIO())
    stream.write("direction 6 - a single source: no comparison, not a pass\n")
    stream.write(f"  exit code {rc}\n")
    if rc != 2:
        failures.append("a run with no comparison exited as a pass")

    # ---- direction 7: freshness — undated is not stale
    fr = check_freshness({"name": "f", "sources": [], "freshness": {
        "name": "dates", "days": 30,
        "command": "printf 'a\\t2020-01-01\\nb\\t%s\\nc\\n'"
                   " \"$(date +%Y-%m-%d)\""}})
    stream.write("direction 7 - a key with no date is not a stale key\n")
    stream.write(f"  stale {len(fr['stale'])}, recent {fr['recent']}, "
                 f"undated {len(fr['undated'])}\n")
    if len(fr["stale"]) != 1 or fr["recent"] != 1 or len(fr["undated"]) != 1:
        failures.append("freshness does not separate stale, recent and undated")

    if failures:
        stream.write("\nSELF-TEST FAILED\n")
        for f in failures:
            stream.write(f"  {f}\n")
        return 1
    stream.write("\nself-test passed: it fires on divergence, stays silent on "
                 "agreement, and never calls a pass what it did not compare\n")
    return 0


# --------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(
        prog="provenreal",
        description="Compare what a system claims with what can be measured, "
                    "from independent sources. It does not decide who is right.")
    p.add_argument("-c", "--config", help="JSON file with the subjects")
    p.add_argument("--json", action="store_true")
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--version", action="version", version=__version__)
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.config:
        p.error("--config is required (or use --selftest)")

    try:
        with open(args.config, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except OSError as e:
        p.error(f"cannot read {args.config}: {e.strerror or e}")
    except ValueError as e:
        p.error(f"{args.config} is not valid JSON: {e}")
    try:
        validate_config(cfg)
    except ConfigError as e:
        p.error(f"{args.config}: {e}")

    results = []
    for subject in cfg["subjects"]:
        res = compare(subject, timeout=args.timeout)
        fr = check_freshness(subject, timeout=args.timeout)
        if fr:
            res["freshness"] = fr
        results.append(res)

    if args.json:
        json.dump({"version": __version__, "subjects": results},
                  sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return exit_code(results)
    return report(results)


if __name__ == "__main__":
    sys.exit(main())
