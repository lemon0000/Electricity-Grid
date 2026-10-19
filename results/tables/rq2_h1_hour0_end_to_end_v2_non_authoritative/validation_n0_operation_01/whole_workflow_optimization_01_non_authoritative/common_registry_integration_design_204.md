# Common registry integration draft

Status: DRAFT_NONAUTHORITATIVE. Root is the sole writer. This extends scoped
Roster evidence 199/200/201/202. It supplies no seal, review receipt or run authority.

The complete workflow still needs three independent N0s, Common/Genesis,
four Parents, Handoff, paired commit, Post and exact-head reopen. Old chain07
and its independent postcheck04 are already complete and are reused as historical
synthetic evidence. They are not rerun for this development work.

## Typed graph

Use mechanical successors with explicit source imports and schemas. Keep their
predecessors unchanged. Base Common11 retains Common2's algorithms and binds Roster5;
Gen3 binds Common11; Snapshot3 binds Gen3; Worker3 binds Snapshot3; Preparation3,
Lifecycle3 and Inspection3 bind Worker3; Parent5 binds those three successors and
the existing source-window2. Handoff7 binds Parent5, Gen3, Bridge5 and
ParentValidation5; Post4 binds Parent5 and ParentValidation5. Existing reference
window/route algorithms are parameterized by the actual Parent and stay unchanged.

Genesis family: Bridge3 / Routes3 / Witness8 / ExactSource9 / Common9.
Handoff family: Bridge5 / Witness9 / ExactSource10 / Common10.
Bridge3's canonical consumers are Snapshot3 and Handoff7. Its host is Gen3.
Base Common11 is a compatibility path; the optimized adapters own all genuine
Common preparations. Historical Common2 reports remain explicitly predecessor
science/metadata projections, while current Common9/10 reports and execution
receipts carry their own identity and actual counts.

## Independent provenance and lifetime

Bootstrap7 must pin an explicit exact-path/SHA manifest, compiled source blueprints
and expected source globals before accepting any consumer. Merely reading current
bytes at import as a baseline is insufficient. Include that manifest/helper in
the Bootstrap implementation identity and runtime checks. Bind no caller-supplied
checker or callable body.

Source footer registration records only weak definition identity after each
module's runtime guard is installed, from its exact top-level CALLsite. It grants
no read authorization. Families have separate slots. Canonical loaders then
activate a generation only after their source/spec/loader/graph checks succeed.
Every replay independently authenticates the live private bridge row, original
creator/guards/lease/session/ticket and exact body/caller frame. Failed loader,
scope exit, unload and method cleanup clear activation and all strong module,
function, session and frame references. Permanent Bootstrap state retains pins,
code blueprints and weak definition references only.

## Three entry classes

1. Genesis `begin`: create a cleanup-capable provisional private row and a
   one-shot initial-replay ticket before replay. Check its exact original caller
   and owner frame, three guards, creator, declared Roster and active loader.
   On any failure retire its scope and provisional state while preserving primary.
2. Handoff `attach`: its original private row and lease exist before replay;
   authenticate exact attach frame, acquisition operation, parent/common guards
   and one-shot provisional ticket. Complete canonical route activation before
   replay; creation of the witness session follows replay and arm declarations.
3. Common body: an internal source-defined coordinator invokes the fixed original
   `_prepare_locked` exactly once, binding the actual body frame before the first
   replay. The first direct replay and four nested `check(replay=True)` calls
   have fixed ordinals and parent chains. The two round-final calls additionally
   bind the original round frame and body-to-round CALLsite. Other two calls bind
   the exact body frame and its fixed check CALLsites. Same-code clones, direct
   callers and callback/trace reentry cannot substitute those frames.

Each replay opens and retires its own Roster read scope; its two original views
borrow only that scope. All sixteen original numerical contexts per prepare and
all dynamic journal/registry checks remain. No proof crosses a replay or callback.

## Static phase cost inside Common

A Common body has no external callback, native work, Job or durable publication.
Own one phase window around that fixed body, including its final return bookend.
Use Bootstrap's internal `_phase_prepare` for the two manifest projections and
let its nested Roster phase calls borrow the same immutable phase dependency
window. Original dynamic evidence is still freshly read in every Roster scope.
The phase exit must complete before the prepared result leaves the coordinator.
Failure at its exit poisons the operation and returns no prepared data.

The 201 predecessor/shared-window equality checks support the unchanged static
projection algorithm; new integration still needs route/failure tests and
representative actual timing. This proposes fewer static phase windows, not fewer
numerical contexts or relaxed acceptance limits. Numerical reuse remains scoped
to one Roster replay. Shared Common-wide numerical reuse is a separate unapproved
design and is not implemented here.

## Counts, tests and launch boundary

Current full-chain inventory has 47 Common calls: 235 Common Roster replays,
plus 7 method-initial replays = 242. With three roots and two views, this is
1452 registry prepares / 23232 original contexts. Per-replay proof reuse gives
2904 full numerical hour replays and 8712 fresh context revalidations for these
reads, before counting Bootstrap constructors, inspect and attachment work.
The exact growing-history multiplicities and phase-window totals must be
recomputed from the new connected DAG before a chain launch.

Required negatives: valid-looking unpinned source; footer without activation;
repeated/cross-family registration; failed loader rollback; stale generation;
repeated initial ticket; false lease/session/ticket/creator/guard; direct or
same-code cloned body/round/check; wrong parent/CALLsite; trace or callback
reentry; body primary plus close/receipt/retire/deactivate failures; foreign
aliases preserved on unload; absence of permanent strong consumer references.

Validate mechanical source changes with normalized AST comparison, then bounded
unit/protocol faults, loader integration and existing saved numerical artifacts.
Do not spend a fresh N0 Job while the consumer API and typed graph are unsettled.
Every later genuine diagnostic gets a fresh plan with current scalar metadata,
source pins, fixed attempt count, wall/RAM/storage cap and immutable terminal.
The optimized chain and formal experiment remain unaccepted.
