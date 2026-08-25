# RQ2 Public Workload Blocks Independent Review

## Scope

- Risk: R3 implementation with R4 preregistration bindings
- Artifact: `alibaba_dimensionless_workload_blocks_v2`
- Reviewer mode: read-only `sol_reviewer`
- Formal experiment authorization: not requested

## First Review

Verdict: `REWORK`

Findings:

1. Hour-disjoint blocks did not guarantee job-disjoint training and holdout
   populations. The source contained 239 jobs contributing to both selected
   block populations.
2. The preregistration did not state whether the training or holdout marginal
   was the transport column marginal.

## Focused Repair

- Added a fail-closed split policy that excludes every job contributing on
  both sides of the split boundary before hourly aggregation.
- Rebuilt the successor package. It excludes 908 jobs and 916 task rows,
  including all 239 jobs identified by the first review.
- Fixed the training marginal role to policy fitting and freezing only.
- Fixed the holdout marginal role to the transport column and fixed-policy
  evaluation.
- Preserved v1 as a rejected predecessor.
- Rebuilt the v2 preregistration and external SHA-256 manifest.

## Re-review

Verdict: `PASS`

Independent evidence:

- Remaining jobs shared by training and holdout populations: 0
- Workload blocks: 68 training and 68 holdout
- Relevant regression: 29 passed
- Ruff: passed
- `pip check`: passed
- `git diff --check`: passed
- Outer manifest entries: 8/8 live
- Preregistration frozen entries: 15/15 live
- Source package manifests: 7/7 live

## Residual Boundaries

- Requested-GPU occupancy is not electrical power, observed flexibility, or
  contract capability.
- Full repository tests were not run.
- The formal R4 gate remains closed pending the outage-to-grid-need package,
  complete Cartesian fixed-policy replay, full-protocol independent review,
  and explicit user authorization.
