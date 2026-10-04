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
