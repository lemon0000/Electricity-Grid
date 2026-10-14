# Selector timing prerequisite for released worker transport

2026-10-11. Root-recorded independent read-only design findings from
`/root/selector_owner_design_review`; reading_stopped=true. No implementation,
tests, native or Job execution. Not an official review or execution authority.

Current closed snapshot and sequence support scientific input/output replay but
do not provide native QPC intervals. Stage wall time or Gurobi Runtime subtraction
cannot prove full non-solver allowance: stage internals also include model build,
capture, postsolve and replay, and the clocks differ.

Before the released worker/controller, build a selector-specific timed stage and
sequence successor. Preserve closed predecessor bytes and the raw science archive
layout; place bounded timing sidecars in a separate fixed directory. Continue to
use the closed sequence.inspect for scientific reconstruction. Do not install
runtime replacements of bridge._run_stage, StageCapture or GurobiDirect._apply_solver
as the production timing mechanism. Such hidden seams are not bound by the existing
sequence implementation identity. Tests may still use explicit fabricated adapters.

Use the low-level normal_task_process TaskProcessBudget, task_process_identity,
normal_task_child and TaskProcessObservation, and normal_resources host/directory
budget primitives. Borrow initial/final validation logic, not N-specific saved-job
schemas or source interfaces. Role budgets and non-solver allowances must exactly
match SelectorRunConfiguration; do not inherit the N timed controller's 300-second
ceiling in place of the process primitive's 3600-second ceiling.

The eventual released_input(request_path, request_sha256) validates canonical
request/launch/child/release intent and exact PID, creation time, argv, cwd,
environment and host/budget identities. Persist consumed.json before snapshot
rebuild or selector output allocation. Read only pinned snapshot bytes and rebuild
them; serialized RebuiltInput/frame/disclosure/carry/power are not accepted.

Planned worker records: selector_snapshot, request, launch, initial_observation,
child, release_intent, consumed, worker_clock_binding, worker_result,
worker_timing_terminal, observation and job_checks (each a fixed JSON schema).
Request binds role, snapshot SHA, full declaration SHA, selector configuration SHA,
complete stage order, role process budget, non-solver allowance and implementation.

Use contiguous same-PID/thread QPC phase intervals for released_handshake,
snapshot_rebuild_before, sequence_prepare, sequence_run, sequence_fresh_inspect,
snapshot_rebuild_after and result_publication. Stage native intervals separately
bind index/label/request/sequence commit/stage terminal, PID/thread/clock domain,
apply and native start/end, and timing binding/terminal pins. Require all intervals
to be ordered and included in the corresponding worker/stage windows.

Only after live wait returns exit0, child_exited and whole_job_quiescent may the
parent read or adopt worker evidence. Parent independently rebuilds the snapshot,
replays the closed sequence, validates complete stage/native vectors, role budgets
and stable request/process/timing/output bookends. It computes a conservative
whole-Job non-solver upper bound:

    ceil((observed.elapsed_seconds + parent_clock_roundoff) * 1e9)
    - sum(max(0, native_interval_ns - per_interval_clock_roundoff_ns))

Compare using exact Fraction(str(configured_non_solver_seconds)). The clock
roundoff bounds and inclusions require implementation and tests; the formula is
design guidance, not current evidence. Whole-Job timing covers startup/release,
source reconstruction, all stage non-native work, publication, exit and quiescence.
Phase intervals diagnose components but cannot substitute for the parent bound.

Actual scientific reconstruction of a retained Rref archive does not authenticate
its Job history. The later controller must separately retain and validate that
Rref Job receipt before release/consumption. There is no reuse credit from archive
pins. Missing/incomplete timing, timeout, nonzero exit or unconfirmed quiescence
remains unresolved; preserve evidence and prohibit automatic retry.

All full-resource, producer-consumption, continuation, formal-result and native
authorization gates remain false. The timing successor is a prerequisite within
the still-open worker/controller and paired-transaction work.
