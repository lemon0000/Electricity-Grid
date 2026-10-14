# Selector worker input reconstruction: design review

2026-10-11. DRAFT_NONAUTHORITATIVE. Root-recorded read-only design advice from
`/root/selector_owner_design_review`; reading_stopped=true. No new implementation,
tests, native calls or Jobs. This is not an official review or run authority.

## First implementation boundary

Build a selector-specific, solver-free input reconstruction interface before a
worker/controller. Restrict the first version to hour 0 and retained empty common
owner genesis. The existing common owner cannot represent later phase states.
Hour 1+ needs independently pinned phase-prefix replay and remains open.

The parent prepares a fixed-schema receipt under the original CommonOwnerGenesis
guards, using its retained Manifest, SourceBinding, holder/owner genesis receipts,
binder head and SelectorRunConfiguration. Use explicit canonical encoders and
decoders; never serialize executable objects, class names or SelectionCandidate.
The returned diagnostic receipt alone is not a live execution capability.

The child reconstructs typed declarations, then calls phase._fresh(binding, 0,
binding.genesis_terminal_sha256), phase._initial(manifest, current) and
phase._request(manifest, state, current). It checks complete manifest/configuration,
source audit, exogenous identity, lane, before-state identity, selector input
identity and initial stage request against the retained receipt. Inputs come from
fresh source/prefix replay, not receipt-supplied frame/disclosure/carry fields.

Rref uses state.reference. Each Actual lane uses its own state.lanes entry. Actual
power must be derived from a complete Rref sequence whose owned Job receipt was
retained after whole-Job quiescence and fresh parent inspection. Rebuild the same
source/state, inspect the Rref archive, recover candidate_request_exact, then use
business.current and business.prepare_development to derive exact rational
actual_power_mw. The request has no caller-supplied Actual power field. Unresolved
business input/candidate, mismatched context or incomplete Rref stays unresolved.

## Subsequent execution boundary

One complete selector chain per independent Windows Job. The controller uses the
role-specific SelectorRunConfiguration budget and the existing TaskProcessBudget
ceiling (3600 seconds), not the N-only controller's 300-second short ceiling.
Account for the exact selector stage/file caps and controller records separately
from scratch, filesystem allocation, memory and host reserve. No resource
admission claim follows from logical payload arithmetic.

Before child release retain request, launch, initial observation, child identity,
release intent and an independently acknowledged release receipt. The worker
checks exact argv/cwd/environment/PID/creation/budget/host/request/release and
persists consumed.json before source reconstruction or selector execution.
After OwnedSelectorSequence.run, validate the original live completion, freshly
inspect the sequence and recheck input before publishing worker_result.json.

The parent must observe exit0 and whole_job_quiescent before reading/adopting
worker output. Then independently rebuild input, inspect the saved sequence and
recheck common correspondence before retaining a Job receipt. Callback
acknowledgement is a trust boundary, not a crash-durability certificate. Any
unknown release/return/retention outcome remains unresolved; preserve all bytes
and prohibit automatic retry. Future metadata reconciliation must be solver-free.

## Reuse boundaries and verification

Use the handshake order in h1_timed_job_controller._job and
h1_timed_released_worker_development_v2.released_input as examples. Their N
request schemas, pending_input, SourceParent packet/projection logic, OwnedWorkerHour,
232-stage bound and N request key cannot certify selector work. Do not reopen a
live phase owner's write lease/SQLite connection in the child. Its current
_connect uses mode=rw; a new read interface needs independent review.

Tests must cover two-pass reconstruction; every source/configuration/owner-head/
lane/Rref dependency drift; exact rational Rref-to-business-to-Actual mapping;
cross-lane rejection; missing/extra input fields; consumed-before-source ordering;
request/release/child/argv/environment mutation; release-retention failure;
post-terminal failure; timeout/nonzero/nonquiescent rejection before result read;
role-specific budget selection; parent input/output bookends. Fabricated adapters
and solver-forbidden replay establish development behavior only.

formal_result=false; formal_execution_ready=false; resource_admission=false;
native_execution_authorized=false; owner_consumption_authorized=false;
selector_producer_connected=false; full_192_hour_execution_verified=false.

## Scope refinement from the same reviewer

Start with `h1_selector_input_snapshot_development_v1.py`, not a general codec.
Provide separate capture_reference/rebuild_reference and
capture_actual/rebuild_actual paths, each fixed to hour 0. Actual snapshot creation
requires the complete Rref archive to already exist and both capture/rebuild must
freshly inspect it. The pure snapshot proves saved numerical correspondence only;
the later controller must additionally supply owned Job/quiescence evidence before
it may release or consume Actual work. The snapshot cannot manufacture that evidence.

Keep dependencies one-way: snapshot imports common owner, phase and sequence;
sequence never imports snapshot; worker imports snapshot and sequence; controller
imports snapshot and worker. Reference and Actual snapshots are produced in that
order, not jointly before Rref completion. The first unit has zero producer/Job
entrypoints and rejects any non-genesis owner/holder heads.
