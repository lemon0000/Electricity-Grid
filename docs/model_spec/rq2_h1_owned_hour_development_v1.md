# H1 sequential owned hour development v1

Status: DRAFT_NONAUTHORITATIVE. This unit composes the owned stage producer and
science completion API across the entire canonical stage_order (1..232). It
has no CLI, Job supervision, native authority, resume or partial-hour result.
run() can execute native when supplied the real adapter; invocation therefore
requires separate explicit authorization and resource/Job supervision.

The hour binding records input/source audit/hour, specification/limits/order
hashes and implementation identities. OwnedHour internally creates each
OwnedStage with the current complete lock prefix. It requires exact live
Completion, checks its root/request/implementation/flags, invokes the stage fresh
reader and writes a create-once commit before advancing the lock prefix. Commits
bind prior head, index, child relative path, stage request/implementation, entry
lock hash, both completion pins, inspected lock/stage and numerical result pins.
Only fresh-inspected locks advance the chain; a commit confirmation failure
stops before the next stage even when commit bytes exist.

Before writing a projection, full-hour replay starts from empty locks, checks
every commit and stage subtree, reruns stage science and recomputes the final
boundary with the existing approved replay_feasible_boundary transition using
the last stage's mapped assignment. The new projection schema binds before/after
boundary values, locks, generation rule, full stage-pin/commit vector and new
implementation. It does not construct or publish an old v3 replay type. Core
boundary values can be compared with the old scientific oracle, while evidence
schema and identity are new. Projection cap is 256 KiB; metadata cap is 2048 bytes.

Projection and terminal are written only after the complete prepublication
replay. A second fresh full-hour inspection verifies the terminal before the
owner returns an immutable HourCompletion. The reader requires independent
terminal and reader-implementation pins, checks exact directory/file topology,
and brackets all bounded files (SHA256 plus identity) and directory identities/
listings across the complete replay. It checks source audit/context/dependency
identity before returning. It returns conditional evidence only, with
owned_run_return_observed=false and whole_job_quiescence_checked=false.

Exceptions after guard acquisition poison the hour. Failed acquisition rejects
without altering the active owner. A partial hour retains its artifacts and has
no projection; a failed projection/terminal confirmation may leave those bytes
but returns no HourCompletion. Neither reader nor filesystem content supplies
resume authority. The typed receipt is a trusted Python API distinction, not a
security boundary against arbitrary object/module mutation. Hashes do not prove
a unique native execution or directory-entry durability through power loss.

For S stages the completed tree has 18*S+3 files and 4*S+3 directories including
the root. Readers retain bounded file digests/identities, current scientific
result, lock vector and pin vector, not all raw bytes/assignments simultaneously.
Repeated stage/hour replay, serialization, clones, contents and filesystem
allocation still require successor memory/time/storage admission. File caps
alone are not a resource certificate; prior native/report budgets cannot be
reused for these additional science copies and work.

Tests use three-stage synthetic adapter execution with installed DirectSolver
driver and derived saved assignments. They compare boundary values with old v3
science and cover stage/fresh-reader/commit failures, publication failures before
and after writes, commit/lock/pin/context/topology faults, full-view mutations,
typed result/owner/reentry and dependency boundaries. Pinned RTS construction
checks the declared 232-stage order only; no full 232-stage producer execution is
claimed. Actual Gurobi/symbol-map postsolve, all-hour carry coverage, durable full
segmented timing/observer, whole-Job quiet, actual task DAG/manifest/certificates,
resources and official review remain open. All native authentication, collector,
resource and formal flags remain false.
