# v2 proof-aware obligation manifest development

R3 DRAFT_NONAUTHORITATIVE / PRE_SEAL. Zero solver/native calls. This connects
the exact source-bound exclusion proof to individual obligations in the
existing four-family catalog. It does not admit an executable task inventory.

## Construction and identity

`build()` checks the fixed catalog and final exclusion report SHA256, invokes
the existing exclusion fresh inspector, and brackets compilation with stable
views of every report source pin. The implementation itself is bound and
rechecked. `inspect(path, expected_sha256=...)` requires an external pin and
byte-for-byte fresh reconstruction. The report limit is 16 MiB; the existing
source reader has a separate 32 MiB per-input limit. Neither is a full-study
storage, memory or time admission.

A Resolver keeps only immutable bytes/tuples. Returned dictionaries are
detached copies. Its queries project the checked snapshot; they do not
recheck live source freshness or provide execution authority.

For each family, the original `axis_order` and complete axes define mixed
radix ordinals. `resolve(family, ordinal)` rejects bool, float, negative and
out-of-range values. `encode_coordinate` requires the exact family axes and
canonical JSON equality, preserving bool/int and string/rational distinctions.
The two directions are inverses. Obligation identity includes the versioned
schema, exact catalog pin, family, ordinal, axis order and complete coordinate.
No D axis is added to training LB, B6 actual or holdout.

Each query recomputes the cell identity from the complete theta and alpha.
The named witness pair is recognized by complete canonical power/workload
window equality, not by positional indices alone. D remains in training UB
identity even when an analytic proof independent of D is shared.

## Logical proof dependencies

The fixed, topologically ordered DAG has 8019 nodes:

- contract, catalog and training-source witness roots;
- 300 exact arithmetic groups, including groups without a contradiction;
- 292 positive local contradiction groups;
- 1856 complete cell bindings;
- 5568 arm/cell implications for CFE-only, joint-correct and joint-B6 planning.

An obligation terminal node is generated on demand rather than storing
billions of records. Each node ID hashes its full record. Parent edges are
`proof_reference` or `logical_implication`, always `solver_reuse_edge=false`.
Every node has null solver task ID, causal key and runtime request. Logical
proof sharing does not establish reuse of N/Rref/A, policies or native work.

The terminal disposition is exactly one of:

- `direct_analytic_witness`: relevant planning cell/arm and the named pair;
- `not_scheduled_due_to_parent_cell_proof`: another planning pair in that cell;
- `conditional_prerequisite_false_not_executed`: affected B6 actual or holdout;
- `unresolved_no_certificate`: all remaining obligations, including every
  network-only obligation and the 44 cells not excluded by this witness.

The first two dispositions are cell-level no-full-support-UB implications;
they do not claim an individual pair dispatch or offline LB was executed.
Conditional evaluation has no native status, failure outcome or fallback D.
Unknown dependencies are explicitly named by family: missing same-contract
offline relaxation; missing causal policy/full training witness; missing B6
planning UB/shared policy; missing holdout training UB/named policy.

All original identities remain queryable. Ordinal, pair, split, proof status
and graph labels are controller/audit bookkeeping, never policy inputs.
`bookkeeping_labels_are_policy_inputs`, `causal_request_keys_materialized`,
`complete_executable_task_inventory`, solver reuse, resource discounts,
resource admission, formal result and execution authority stay false.

## Acceptance and remaining work

Tests cover actual mixed-radix boundaries and independent catalog roundtrip,
all 1900 cell/arm truth tables, direct/other/conditional distinctions, UB D=0/1,
canonical type rejection, mutation isolation, full graph topology/hashes,
source/report/code drift and post-compilation source drift. Fresh inspection
rejects modified axes/graph despite a matching hash of the modified bytes.
Independent read-only R3 pre-seal review is required; it is not official review.

Next work must bind actual causal keys and runtime requests, using the existing
complete source/carry and role/resource identities. Common Rref/A, missing
offline LB and complete policy UB, resource admission and fresh sealed review
remain open. No scheduler, solver call discount or generic graph store is
introduced by this resolver.
