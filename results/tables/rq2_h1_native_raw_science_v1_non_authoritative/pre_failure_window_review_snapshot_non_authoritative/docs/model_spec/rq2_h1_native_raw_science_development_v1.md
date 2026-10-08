# H1 retained native capsule science consumer development v1

Status: DRAFT_NONAUTHORITATIVE. This unit connects the new raw format to the
existing numerical predicate and approved generation projection. It supplies
create-once science artifacts and independent zero-solver replay. It supplies
no source-parent/Job completion, native authentication or formal authority.

## Original values and existing science

`decode_native` requires exact schema/false flags, external binding/export pins,
all native attributes, complete unique canonical names and consecutive native
indices. Numeric atoms must have canonical finite hex matching their exact
binary64 bits. It checks variable domains, bounds, fixed values, objective terms
and constants against a fresh canonical model. Duplicate/foreign terms, missing
required channels, NaN/infinity or differing bits reject. Optional unavailable
MIPGap is retained; the unchanged predicate computes gap from ObjVal/ObjBound.

`capture_postsolve` requires typed single-record SolverResults. It uses the
existing `_native_values` for **reported** labeled rows and the unchanged
`_canonical_completions` for fixed constants or unused/unbounded/continuous +0.0.
These groups and completion reasons, status/termination/solution status, counts,
problem sense and bounds are retained in a bounded sidecar. No solution loading
or residual/predicate/projection occurs during extraction. Extraction can reject
before a complete sidecar exists; the native capsule is already retained.

Fresh replay recomputes completion eligibility and demands exact binary64
agreement between every original native X and the reported/completed assignment.
It never substitutes native X to widen completion eligibility or repair missing
decisions. +0.0 and -0.0 differ at this correspondence gate. Fixed constants also
match exactly. This versioned evidence restriction may reject a case accepted
by an older path; it does not widen scientific tolerances.

The numerical document has a new outer schema and identity and is explicitly
marked `derived_legacy_predicate_view`. Its internal provenance representation
is only a compatibility view for existing arithmetic. It carries new consumer
implementation/collector pins and `solver_calls_by_consumer=0`, never a claim
that the producer used zero solver calls. The old v3 reader rejects the new
document. Referenced variables are independently reconstructed from canonical
objective/constraint repn, not equated with reported Pyomo rows.

Science order is unchanged: canonical assignment/residual/objective reconstruction
→ independent `verify_numerical` → unchanged `predicate.evaluate` must pass →
v3 `_project_and_audit_built` on a fresh audit model → commitment rounding under
the original 1e-9 gate. The approved generation rule alone maps [-1e-9,0) to zero
and rechecks all constraints, power balance, chronology, locks and objective.
Original assignments and the full mapping are retained; rejected projection
receipts are saved when supplied by the existing projection exception.

## Durable callback and independent replay

`consume` is usable as the StageCapture callback. The caller supplies the native
file and independent pins. Science checks the producer binding, specification,
export receipt and raw ingress binding/intent/receipt/outcome. The producer's
request must equal the scientific packet/spec/limits/stage/lock/dependency key;
identical algebra alone cannot substitute another request. These source records
are jointly hashed and bracketed by complete stable readback.

The new science root is created exclusively. Order is intent → postsolve sidecar
write/fsync/stable readback → sidecar receipt → audit → numerical/mapping/result
artifacts → terminal → independent fresh replay. Caps are 256 KiB for sidecar,
mapping and result, 16 MiB for derived numerical bytes, and 2048 bytes per metadata
record. These are rejection caps, not a proven conditional grammar or resource
admission. No second call can overwrite/retry the same root. Failed writes/audits
retain partial evidence; no missing result is inferred as scientific success.

`inspect` requires an externally retained science-terminal hash. It checks exact
topology, source request chain, sidecar receipt and all output hashes, rebuilds
the stage from inputs, reruns the full numerical predicate and projection, and
compares outputs byte-for-byte. It then rereads complete files and identities,
including the external native source, to reject mutation during replay even when
mtime is restored. It never solves, repairs or resumes.

The science terminal is **not** StageCapture completion: producer close/finish
can still fail after this callback returns. Every output explicitly retains
`stage_capture_completion_checked=false` and the existing false coverage/resource/
formal flags. Parent acceptance still needs the independently pinned producer
completion, fresh producer reader, Job quiescence, source/carry gates and resource
admission. A terminal file written before a failed confirmation is not itself an
externally acknowledged completion signal. Fsync/readback do not promise
directory-entry durability across power loss.

## Development evidence scope

Tests compare three synthetic-grid stages with saved v3 scientific replay, and
selected pinned RTS origin stages 0/1/231 with their saved v3 counterparts.
Native capsules are **derived test views** of old reported assignments, not
recovered historical native full-X captures. A synthetic tiny-negative mutation
tests preservation and the approved mapping, not a new native witness. Completion
eligibility, signed zero, fixed mismatch, malformed bits/schema/algebra/status,
sidecar-first ordering, write failures, request substitution, mutation and fresh
replay are tested. Three-stage composition uses StageCapture with the actual
DirectSolver.solve driver and a synthetic adapter/_save_results=False; locks come
from preceding new science results.

Actual Gurobi, its symbol-map postsolve branch, all-hour coverage and complete
worker/Job/timing integration remain unverified. Added sidecar/science artifacts,
clones, repeated reads/replay, memory and filesystem allocation require successor
resource accounting. All producer/native-export/collector/resource/formal gates
remain false; new native execution still needs the ready package and explicit
authorization.
