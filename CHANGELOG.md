# Changelog

All notable changes to this project are recorded here.
Dates are the date of the commit, not of a release.

## Unreleased

- Exit codes: one rule for the text report and for `--json`. Before, `--json`
  exited 0 when no comparison was made and 0 when keys were stale, while the
  text report exited 2 and 1 for the same runs. **Changed meaning**: a run
  where one subject agrees and another could not be compared, or where a
  freshness command failed, used to exit 0; it now exits 2, because part of
  what was declared was not measured. A subject with no comparison but stale
  keys now exits 1 and its freshness is printed; before it exited 2 and the
  stale keys were not shown.
- The configuration is checked before anything runs, and a configuration
  error exits 2 with one line on stderr instead of a traceback with exit 1,
  which is the code for divergence. Measured before this change: a normalize
  rule with a misspelt type (`lower-case`) was skipped while the report said
  normalisation was applied to every source; `"claimed": "25"` was never
  compared and the subject agreed; `"claimed": true` was compared as 1; two
  sources with the same name overwrote each other's count, and a false claim
  was reported as holding. All four are now refused, with the reason.
- A source or freshness command that times out is killed with its whole
  process group. Measured before: the shell was killed and its child kept
  running after the report had called the source not measured.
- Freshness failures keep the reason (`exit 4: no such table`, `timed out
  after 1s`) instead of the exit code alone or the exception class name.
  Before, a freshness command that timed out was reported as
  `TimeoutExpired`, with no duration.
- The freshness count carries its command: printed in the report, and
  `command` added to the freshness object in `--json`. Every other count
  already did.

- Output that is not valid UTF-8 keeps its bytes as `\xNN` escapes. Before,
  every undecodable byte became U+FFFD, so `caf\xe9` and `caf\xe8` were one
  key: a source with both agreed with a source that had only one.
- Freshness reads ISO dates with a `Z`, a `+HH:MM` offset or fractional
  seconds. Before, `2020-01-01T10:00:00Z` was counted as undated, so a key
  six years old was not reported as stale. Dates with no zone are read in
  local time, as before.

## 2026-09-04

- CITATION.cff: version and date match the release. Zenodo reads this file, so a
  stale version here is a stale version in the archived record. First release
  archived by Zenodo.

## 2026-08-30

- README: remove internal hostnames and client counts
- README: link the Galaxy products the tool was built against
- README: correct a claim that did not match the code, and drop install counts

## 2026-08-28

- README: say where this came from, and name the service it happened on
- record: four subjects exercised, and two limits the real runs revealed
- record: mark the inventory-vs-served-hosts case as the clearest one
- record: subjects five and six, and the limit the fifth revealed
- record: the empty answer is a defect found by using the tool
- README: follow the renamed page
- README: name the domains, with links
- README: the set is four

## 2026-08-27

- provenreal: compare what a system claims with what can be measured
