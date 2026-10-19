# Public phase dependency successor cut

Status: DRAFT_NONAUTHORITATIVE. Root is the sole writer. This design has no seal,
official review, execution lease, resource admission or formal-run authority.

The target includes Bootstrap create/reopen and downstream Common/Genesis/
Handoff. The independent static audit therefore favors the direct successor
route `phase-binding3 -> Bootstrap5 -> Owned5 -> Roster4`. A separate read-only
observer would preserve the expensive old public lifecycle and require the same
successors later. The older reader-cut design remains historical design evidence.

## Evidence supporting the cut

- The empty Bootstrap4/Roster3 header attempt95 hit its fixed300s limit before
  Roster reopen and final cleanup. It is not a completed lifecycle baseline.
- Canonical profiling96 located repeated physical reads and identity observations.
- Targeted followup105 closed the declared source/ABI, file-cap, GC/orphan cleanup
  and resource-bound findings. No official gate was opened.
- Matched unprofiled comparison106 measured6 requests at4.370s canonical versus
  3.091s for a complete window, and16 at11.949s versus6.956s. Acquisition, exit and
  cleanup are included. These are local observations, not a whole-chain estimate.

## Stable data and execution

`phase-binding3` should retain group-v1 science, the exact existing immutable
Manifest/config/archive types, and a stable new binding identity. Durable headers
store stable projection and binding data. They do not store per-session receipts.
The diagnostic phase window is constructed internally; caller-supplied bytes are
never accepted as a live credential. Its `consumer_bound=false` and
`canonical_equivalence_verified=false` remain kernel facts. The new outer owner
must bind its own exact route, source identities, declaration, guards and lifetime.

The new phase observation contract states physical entry/recheck/exit, internal
held-byte projections, no per-call physical freshness and no unobserved ABA claim.
Current group outputs must agree with independent canonical oracles. New execution
facts must not be inserted into a predecessor report as if the old verifier ran.

## Segment boundaries

Internal `_check`, `_phase_candidate` and replay borrow an already active phase
window in a fixed callback-free segment. They do not each open a full window.
Before any segment spans journal writes, prove that every held phase input is
disjoint from all dynamic journal/root paths and test actual Windows write behavior.
Constructor failure and journal-write failure must close or retain every resource
for bounded cleanup without replacing the primary error.

Do not span Owned execution/Job, external retain callbacks or arbitrary callbacks
with that window. Close before each such boundary and acquire a new checked window
after it. Same-thread reentry and foreign-thread calls are refused. No input may
remain accepted after a failed exit or an unresolved close.

## Downstream graph

- New Bootstrap5 identity binds Owned5 and phase-binding3; Owned5 and Roster4
  require exact Bootstrap5. Old Bootstrap4/Owned4/Roster3 remain unchanged.
- Genesis uses Roster4-specific witness/source/Common9, routes3 and GenesisOp3.
  Gen2/Snapshot2 can remain only if a cold-import adapter proves both new upstream
  lineage and the retained old storage protocol. Otherwise use new Gen/Snapshot.
- Handoff uses Common10, CommonValidation5, Handoff7, ParentValidation5 and the
  corresponding PostNegative/helper/E2E/entry successors. Parent4 itself can remain.
- Registry numerical replay must also remove the independently identified foreign
  N0 multiplier. Do not borrow producer nonce or cache dynamic registry rows.

New implementations and header identities require fresh roots. They cannot take
over old header/genesis/claim/release/terminal bytes. Saved old science is an oracle;
old credentials and terminal receipts are not new graph evidence.

## Next acceptance sequence

1. Phase-binding3 stable projection and observation semantics, canonical science
   differential, exact-type rejection and callback/write/failure boundary tests.
2. Bootstrap5/Owned5 one-arm bounded synthetic N0 terminal, independent numerical
   oracle and complete close/reopen; Roster4 create/reopen/type/header rejection.
3. Three fresh synthetic N0 terminals and genuine Roster4 attachment.
4. Common9/10 own reports plus shared science -> Genesis -> Parent4 -> Handoff7 ->
   paired commit -> all close -> saved reopen and independent postcheck.

Each experiment needs its own section9 call-count/DAG/resource plan. The new N0
producer and all current-graph consumer positives remain open. Legacy chain07 and
supplement04 stay closed and are not rerun. All formal/native/resource flags remain
false.
