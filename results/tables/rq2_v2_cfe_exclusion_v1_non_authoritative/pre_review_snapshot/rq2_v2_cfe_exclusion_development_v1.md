# v2 source-bound CFE cell exclusion development

Status: DRAFT_NONAUTHORITATIVE / PRE_SEAL development. R3. Zero solver calls.
This overlay supplies analytic proof dependencies for the existing factorized
obligation catalog; it is not a complete executable task manifest or reuse DAG.

## Contract and witness

The approved v2 contract, complete 168/24 coverage and current four-family
catalog are exact SHA256 inputs. The existing v3 outer's 1695 members close
the source/mapping code dependencies. The outer and all source members are
freshly checked, with stable identity/bytes checks again before return.
Frozen src, config, protocols and results remain unchanged.

The named training pair uses power start 192, outage seed 20260822, workload
start 408 and relative offset 162: raw source hours 354 and 570. Both complete
168-hour enrollment windows pass the existing pinned source loader; every
workload row passes the approved 250 MW / 12-decimal projection. Full window
receipts, selected raw rows, projections and exact rational arithmetic are
retained. Package integrity verification reads all pinned package members,
including holdout files, but only training rows enter this proof. No holdout
outcomes select or support the witness.

## Necessary-condition proof

Suppose a policy in the named contract successfully completes all training
support for one cell. It must then complete this pair and meet the CFE service
obligation at offset 162. If its earlier normal/reference/state trajectory
fails or is unresolved, it is already not a full-support successful UB.
This implication does not claim the current runner reaches the selected hour.

Use the existing exact Scheme A allocation and activity rule, with
`tau = 1/1000000`. Store two separate predicates:

- Approved contract predicate: `q_eff > tau && q_eff > f*w`.
- Stronger sufficient contradiction: `q_eff > f*w + 2*tau`.

For the second predicate, relax the local service constraints to
`served_C <= f*w + tau` and `q_eff - served_C <= tau`. They imply
`q_eff <= f*w + 2*tau`; a strictly positive rational gap proves the relaxed
set empty. This relaxation does not change the approved service rule. Its
absence proves neither feasibility nor service success. Canonical Fraction
strings retain exact numerator and denominator, including all margins.

Drop D, network, temporal and causal constraints in this relaxation. The
implication holds for CFE-only, joint-correct (shared additive availability
and nonnegative grid component), and the B6 CFE planning track. It gives no
network-only conclusion. It does not certify the existing operational float
adapter or exact-to-runtime projection bridge.

## Factorized coverage

Retain all 1900 full theta/alpha cell bindings and all 300 distinct `(alpha,f)`
arithmetic groups, including unknown groups. Proof references apply across
all registered D without adding a D axis to training LB or conditional tasks.
The direct witness pair is distinguished from other pairs whose planning
obligations are not scheduled due to the parent cell proof. The latter are
not individual pair failures. B6 actual and holdout identities retain only
`prerequisite_false_no_training_UB / not_executed`; they are not infeasible
or observed failures. Every original identity remains in the catalog.

The fixed witness is expected to contradict 1856 cells and leave 44 unknown.
The affected identity counts are evidence bookkeeping, not solver counts,
measured time savings or permission to discount an admitted resource budget.
No policy UB, common N/Rref/A trajectory, full offline LB/DAG, capacity
certificate, official result, resource admission or execution authority is
created. All corresponding flags remain false.

## Acceptance

Tests use an independent Fraction expression for all 1900 cells, strict
threshold/equality boundaries, distinct theta identities sharing arithmetic,
four-family conservation, fresh report reconstruction and rejection of
contract/source/code/threshold/hour or report drift. Independent R3 read-only
pre-seal review is required; it cannot issue an official verdict. Report
inspection is read-only and recreates the complete source-bound audit.
The 16 MiB report cap and 32 MiB per-input cap are local development limits,
not process-memory, storage, full-study resource or production admission.
