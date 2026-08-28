# provenreal

Compare what a system **claims** with what can be **measured**, from
independent sources. It does not say which source is right: it says where they
disagree.

And it answers **two** questions, not one: **how many**, and **of what**.

---

## The defect it was born from

**27 August 2026.** In a single day, on the same estate:

**Six different numbers for the same question.** «How many services are we» had
five answers across five public pages — 25, 22, 12, 16 — plus one derived from
a catalogue that said 26, and one agreed verbally. None of them was wrong *as a
count*. All of them were wrong as an answer, because none said **which set** it
had been taken from.

**Three sets mixed in one table.** An inventory table held the systems of two
different servers with no column telling them apart. Queried with
`status = active` it answered `47`, and the `47` was true: it was the count of a
set nobody had asked for.

**The real perimeter found only by looking at the server.** While measuring the
coverage of our own Shield service — a post-quantum key agreement running on the
client sites of our LINK network — we counted the hosts served by the web server
instead of the rows in the table. The systems with the component installed were **41** — against the `47` from the table and a `16`
estimated by hand. Three numbers, one measured.

The common shape is always the same: **a full field saying something other than
what is there.** No completeness check sees it, because nothing is missing.

---

## Three rules, and they are three things that went wrong that day

**1. A source that failed is not an empty source.**
A command that does not run returns zero lines, exactly like a command that runs
and finds nothing. Confusing the two is the fastest way to declare «they agree»
about a comparison that never happened. With fewer than two sources answering,
the verdict is `unmeasured`, never `agree`.

**2. Normalisation applies to every side or to none, and it is declared.**
That day a comparison stripped the `www.` prefix from one side only: the pairs
did not match and the result said «no correspondence». The command was right
about the wrong comparison. Here normalisation lives in the **subject**
configuration, not in the individual source — applying it to one side only is
not possible — and it is printed in the report.

**3. Every count carries its own provenance.**
A source name is a label chosen by whoever writes the configuration: it can say
`table` and query something else entirely. The report prints the **command that
ran** under every number. A number without provenance cannot be compared with
another number.

---

## What it does

- runs the declared sources, each a command printing **one key per line**
- compares the sets pairwise: in both, only in A, only in B
- compares a **hand-written claimed number** against the measured ones
- compares **last activity** against a freshness threshold, keeping *stale*
  keys apart from *undated* ones — which are not stale, they are unmeasured
- **declares its coverage**: how many sources answered out of how many were
  declared, and which did not and why

Exit codes: `0` everything agrees · `1` divergence · `2` no comparison was made.

---

## Prove it before you trust it

```
python3 provenreal.py --selftest
```

Eight directions, all asserted, any one failing fails the test:

| | |
|---|---|
| 1 | two sources that disagree → **must fire** |
| 2 | same keys in a different order → **must stay silent** |
| 3 | a source exiting with an error → **`unmeasured`**, never `agree` |
| 4 | `www.one.example` against `one.example` with normalisation → agree |
| 4b | every count reports the command that produced it |
| 5 | claimed `5`, measured `3` → must fire |
| 6 | a single source → exit `2`, not `0` |
| 7 | a key with no date → *undated*, not *stale* |

Direction 3 is the one that costs most when it is missing, which is why it is a
distinct verdict and not a footnote.

---

## Use

```
python3 provenreal.py -c subjects.json
python3 provenreal.py -c subjects.json --json
```

See `example.json`. Each subject declares its own sources, the shared
normalisation, and optionally a claimed number and a freshness threshold.

Standard library only. No dependencies.

---

## What it has found

This list is the record of what the tool found running on our own systems, not
a collection of made-up examples. It grows as we use it.

<!-- RECORD — one line per subject exercised, with the date and what it found -->

**2026-08-28 — an inventory table against the hosts a web server actually serves.**
*The clearest case so far.*
93 hostnames served, 47 rows marked active, 46 in both. One row was declared active
with no virtual host anywhere on that machine: the domain is real and answers, but it
is hosted elsewhere entirely — a different provider, a different IP. Nobody was
looking for it, and no status check would have found it: the site is up.

**2026-08-28 — a service's own records against the machines that actually run it.**
41 installations with the component on disk, 47 live records, 39 in both. The
interesting part was not the gap: it was that the two sources do not speak the same
language. One is keyed by domain, the other by filesystem path, and a path is not a
domain — an installation living in a subdirectory has no domain in its key at all.
The counts had been compared for weeks without anyone noticing they were counting in
two different key spaces.

**2026-08-28 — a register against the page that reads it. They agreed.**
Two entries declared live, two rendered, no difference. Worth recording precisely
because it found nothing: a register and its consumer had been wired together the
same day, and this is the check that says the wiring holds. An agreement measured is
not the same as an agreement assumed, and only one of the two can be shown to anyone.

**2026-08-28 — a number we publish, against the catalogue it is supposed to come from.**
One page claims 25, a function derives 26, and a third figure — 16 — was in use on two
other public pages and in an organisation profile. All three are true as counts. None
of them says which set it counted, which is why they could sit next to each other for
months without anyone noticing. The tool does not pick a winner: it prints the command
behind each number, and the disagreement becomes a decision instead of a mystery.

*(in progress — the tool has been in use since 28 August 2026)*

---

## Limits, stated

- It compares **sets of textual keys**. It knows nothing about what those keys
  mean, and two sources can agree perfectly while both describing the wrong
  thing.
- A source is a shell command: it **inherits the permissions of whoever runs
  it**, and whatever it cannot read comes back as absent. Coverage states this,
  but reading it is the responsibility of whoever looks.
- **Sources often live on different machines.** That is the normal case, not the
  exception: an inventory usually lives where the application is, and the truth
  usually lives where the traffic is. A source is a shell command, so reaching the
  other machine is the caller's problem. A source that cannot reach its machine is
  reported as `unmeasured`: correct, but not useful.
- **Noise comes back as keys.** A web server's catch-all name, a placeholder row, a
  blank entry: they are real output and the tool counts them. Read the "only in"
  lists before believing a divergence.
- It does not decide, and it must not. Choosing which source is right is a
  decision, and a decision made silently by a program always picks the most
  convenient source, not the truest one.

---


## Where this comes from

LANGA runs 16 digital services across 5 networks on its own infrastructure. This
tool came out of a defect we hit while running them. See
[How we work](https://about.langa.tv/come-lavoriamo/).

---

## License

MIT. See `LICENSE`.

---

Built and maintained by LANGA.
