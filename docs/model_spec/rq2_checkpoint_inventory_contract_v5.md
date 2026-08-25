# RQ2 v5 checkpoint inventory contract

This amendment preserves the v4 scientific formulation and strengthens only
the formal execution provenance contract.

## Required key sets

The grid-stage checkpoint inventory keys must equal the complete set of
registered power-system block IDs.

The pairwise-stage checkpoint inventory keys must equal:

1. one policy checkpoint for every registered parameter cell; and
2. one pair checkpoint for every power-holdout by workload-holdout Cartesian
   pair in every cell whose correct and B6 training policies are both feasible.

An ineligible cell must have no pair checkpoints. Missing, additional,
duplicate, or renamed keys close the gate. All provenance, inventory, summary,
and package-manifest JSON is parsed with a loader that rejects duplicate object
keys before ordinary object construction can overwrite them.

## Digest and bundle rules

Every inventory value must match `[0-9a-f]{64}`. The standalone inventory,
the copy embedded in `provenance.json`, its canonical SHA-256, and the summary
field must agree exactly.

Expected keys are derived from registered block IDs or from the marginal,
cell-status, and policy tables before downstream transport calculation. A
package remains invalid if an inventory item is removed and all outer
provenance, summary, and package-manifest hashes are recomputed.
It also remains invalid if an illegal digest is hidden behind a duplicate key
whose final occurrence is valid and all outer hashes are recomputed.

## Scope

This amendment does not alter scenarios, probabilities, policy optimization,
holdout decisions, transport objectives, identification rules, or scientific
claims. It does not authorize formal execution.
