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

*(in progress — the tool has been in use since 28 August 2026)*

---

## Limits, stated

- It compares **sets of textual keys**. It knows nothing about what those keys
  mean, and two sources can agree perfectly while both describing the wrong
  thing.
- A source is a shell command: it **inherits the permissions of whoever runs
  it**, and whatever it cannot read comes back as absent. Coverage states this,
  but reading it is the responsibility of whoever looks.
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
