# v2 obligation to pending normal input binding

R3 DRAFT_NONAUTHORITATIVE / PRE_SEAL. Zero solver/native calls and no writes in
the binder. The public interface joins a source-bound obligation to the
existing pending H1 input; it does not generate a solver task or launch request.

The existing v3 `request_key(packet, specification, limits)` remains the
normal numerical request identity. `PendingWorkerInput` and the timed parent
snapshot independently rebuild source, before-state, clock, intent and anchor.
This layer reuses those interfaces without modifying src or sealed runners.

## Scope and static precheck

`open_manifest()` freshly inspects the exact final obligation manifest.
`precheck()` requires that immutable snapshot and accepts only unresolved
training-UB obligations. All four arms are supported; an already excluded
CFE/joint/B6 planning cell is rejected. LB, conditional actual and holdout are
not accepted. B6's role is explicitly a normal environment prerequisite for
its planning tracks, not an actual shared execution result.

The current phase is enrollment, relative hours 0 through 167. Follow-up
168 through 191 requires a later phase/causal-need binding and is explicitly
rejected here. The existing source parent still supports its declared horizon;
this binder makes no full 192-hour coverage claim.

The complete catalog coordinates remain in the binding. Parent origin must
match split, both raw window starts, outage seed and source config. Before
writing an intent, the enclosing controller should call static precheck and
whole-enrollment prevalidation. The latter uses both full pinned 168-hour
windows, checks their catalog chain IDs, the CFE source domain and every
250 MW / 12-place workload projection. Future rows/error positions remain in
controller audit logic and are not supplied to normal or business policy.

## Fresh join and identities

`bind()` repeats prevalidation, checks the pinned baseline development closure
and v3 outer members, then opens a read-only pinned parent snapshot. It obtains
the current pending input and validates its externally supplied receipt pin.
A separately loaded current source declaration must match its lineage; raw
hours are window start plus relative hour. Display/source hours use raw+1,
while the numerical model retains its neutral relative timestamp.

The record distinguishes:

- `normal_input_identity` and existing `normal_request_key`;
- `source_parent_lineage`, including full parent declaration, anchor, head,
  source, before, packet audit and pending receipt pins;
- versioned `obligation_binding_id`, including the manifest/node/obligation,
  full coordinates, relative hour, specification/limits, proposed Job budget
  and implementation/evidence identities.

Changing theta, alpha, arm or D can change the obligation binding while leaving
the normal request unchanged. A proposed process budget changes its resource
identity; it is not host, disk, whole-study or launch admission. Binding a
request does not prove that a policy achieves a UB or that its normal model is
feasible. No source label or obligation metadata enters the numerical input.

The pending input is rebuilt again before return, and captured evidence files
are checked for drift. The reader neither authenticates the parent's held
writer lease nor returns a durable live handoff. Therefore
`live_parent_state_at_use_verified=false`: a future controller must recheck
head/anchor/input under its own live guard and lease immediately before use.
JSON inspection rebuilds the same join; JSON cannot restore executable carry.

`runtime_task_id`, `launch_request` and `host_resource_admission` remain null.
Solver reuse, full task inventory, resource admission, training UB, native
authorization, formal readiness and formal result all remain false. A 128 KiB
binding-record cap is only a local metadata limit, not a resource certificate.

## Verification

Tests use the actual pinned RTS and marginal windows at starts 192 and 408,
seed 20260822, a system-tmp pending parent, and enrollment hour zero. No reports
are solved and no Job is launched. They check raw/display/relative clock
separation, fresh reconstruction, changed cell/D/arm/budget identities,
incompatible families and proven exclusions, source/receipt/head/anchor/before/
spec/limits mismatch, detached output and late implementation drift.
Previous snapshot tests cover future carry reconstruction; this new join has
not yet demonstrated an actual later-hour accepted scientific carry.

Independent read-only R3 pre-seal review is required. This is not official
review or permission to consume any prior calibration authorization. Next work
must connect binding to an admitted runtime request and common Rref/A with
their separate state chains, rather than treating equal N keys as reuse rights.
