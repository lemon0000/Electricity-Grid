# Selector released worker and parent Job integration boundary

2026-10-11. Root-recorded independent read-only design findings from
`/root/selector_owner_design_review`; reading_stopped=true. No implementation,
native or Job execution. Not official review, resource admission or run authority.

Build two successive units: selector released worker transport, then its parent
Windows Job controller. The worker reconstructing and running a chain does not
establish parent Job success or persistent phase consumption.

Worker request uses a new exact schema binding the bounded external snapshot
filename/size/SHA and implementation; role/lane; complete SelectorRunConfiguration
bytes/hash; separate science/timing archive caps; exact selected role budget and
non-solver allowance; expected timed-sequence configuration/request; new worker
and timed-sequence implementations; fixed route and all false authority flags.
RebuiltInput must independently match each redundant declaration. Actual power
is derived only from the snapshot's Rref/business dependency.

Validate request, launch, initial observation, child and release records against
current PID/creation time, argv, cwd, environment and task_process_identity. Keep
stable bounded views. Persist and read back consumed.json before any source
rebuild or sequence allocation. Both before/after consume write failures forbid
source work and retries. Use normal_task_process/resources generic primitives;
do not import the N-specific worker input, source-parent or owned-hour protocol.

Execute: rebuild-before; construct/run/validate OwnedTimedSelectorSequence;
fresh detached timed inspection; rebuild-after; exact declaration/scientific
projection/arguments/configuration/request comparison; result publication.
Bookend transport records, snapshot and both output archives around untrusted
calls. Result binds request/snapshot/consume, PID/creation, both roots/terminals,
sequence request, issued archive-view pin, record hashes and implementations.

Use default QPC at execute entry (Python import/startup excluded). Persist an
ordered phase vector covering handshake through consumed readback, source
rebuild-before, sequence preparation, run, validation/fresh inspection, source
rebuild-after and result publication. Keep run and inspection separately visible
when implementing detailed phase diagnostics. Publish/read back result first;
the final worker_timing_terminal.json then pins that result and the complete
phase vector. Result must not back-reference a not-yet-created timing terminal.
Timing terminal publication and child exit remain outside the child persisted
window. Its write failure makes child nonzero; an existing result cannot be adopted.

Parent selects exact role budget/allowance and registers snapshot, all transport
records, both archive envelopes and scratch in HostResourceBudget. Logical caps
are not filesystem/RAM admission. Persist all pre-release records with bookends.
After release/wait, require matching process identity/PID/creation, exit0,
reason=child_exited, whole_job_quiescent, configured limits and acceptable budget
observations before the first stat/read of consumed/result/timing/archives.
Parent timing must cover startup, child publication and exit/quiescence overhead;
clock conversion/roundoff bounds and native subtraction still require their own
proof. Do not mark non_solver_allowance_verified from phase diagnostics alone.

Actual snapshots may be captured only after a successful quiescent Rref Job and
fresh timed inspection. Their scientific dependency keeps the legacy-compatible
science terminal. A separate parent DAG binds Rref timing/Job provenance, without
adding execution labels to decision identity or requiring child access to a live
parent owner.

Validation: fabricated adapters for both roles and all UIDs; source drift;
request/snapshot/config/cap/budget/allowance mismatch; consume, sequence, result
and timing publication failures; callback/reader mutation; unknown suffixes.
Later short real Windows Job synthetic tests cover suspension before release,
PID/creation identity, quiescence-before-read, nonzero exit, timeout, descendants
and tampering. The synthetic argv/implementation is test-only and cannot be
selected by a production request or credited as production selector execution.

Native authorization, official verdict, resource admission, formal readiness,
formal results, verified non-solver allowance and phase consumption remain false.
