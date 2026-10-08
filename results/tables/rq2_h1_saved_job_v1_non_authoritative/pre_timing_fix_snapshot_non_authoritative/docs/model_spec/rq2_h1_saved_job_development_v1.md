# H1 saved-only independent Job development v1

Status: DRAFT_NONAUTHORITATIVE. Root-only development of the cross-process saved
worker path. This does not enable native execution, production collection,
producer coverage, whole-task resources, formal readiness or formal results.

The creating controller holds an outer lease plus the existing parent leases.
The parent is under `source_parent_non_authoritative`; each create-once hour Job
is a sibling `job_NNN_non_authoritative`. Existing parent topology and science
remain unchanged. No reopen constructor or continuation/repair route exists.

Under controller and parent guards: ready/source/clock/carry -> parent intent and
anchor -> absent-child snapshot and typed input -> request and launch records ->
Windows suspended child already assigned to its owned Job -> pinned initial
headroom observation and PID/creation record -> parent/pins revalidation ->
release intent -> release/wait -> full Job quiescence and exact successful
observation -> worker result pins -> source raw revalidation -> fresh scientific
child replay -> current source revalidation -> parent outcome and anchor.

`release_intent.json` proves only a recorded intention to release. The child
checks exact record schemas, canonical request/declaration/input pins, argv,
cwd, allowlisted environment, reconstructed process identity and actual PID and
creation time. It writes `consumed.json` using xb/fsync/stable readback before
snapshot reconstruction or child creation. A second invocation fails at this
record. It reconstructs its own typed input and compares exact receipt bytes/SHA;
it never accepts a deserialized owned carry. The entire worker forbids solvers.
The fixed attested child preserves raw before grammar/scientific audit. The
worker publishes bounded pins, and the controller obtains owned projection and
carry only by independent fresh replay after exit0 and whole-Job quiescence.

Both controller and worker revalidate the initial observation's finite ordered
clock, exact commit/disk types, current directory/volume bindings and per-volume
demand/reserve aggregation. Sufficient headroom must recompute as true; reservation,
hard-resource enforcement and all formal authority claims must remain false.

Every exception poisons the live parent; partial files, unanchored tails and
completed children remain in place. A stored release intent does not establish
that a worker started, consumption does not establish completion, and a worker
result does not establish parent acceptance. `job_checks.json` only records the
completed Job checks; later controller raw/source/replay/outcome checks may fail.
Crash handling relies on the existing non-inherited Windows kill-on-close Job
ownership. No recovery or retry rights can be reconstructed from disk records.
fsync plus stable readback is not a guarantee of directory survival after power
loss. This is an application-level create-once protocol, not adversarial security.

The saved-only process uses the existing short TaskProcessBudget, additionally
capped at 300 seconds, a license-free environment allowlist and an isolated
`-I -B` entry. It records initial headroom, commit limits and runtime observations;
it does not enforce a filesystem quota. Its explicit archive/scratch reserve
checks are development bounds, not complete research resource admission.

Saved source files are external to the new controller root. Each ordered entry
binds an absolute path, exact byte count and SHA, capped at 16 MiB. The worker
uses stable capped reads; the controller compares file identities and hashes
before/after the Job. No extra raw copy is made in the Job directory; the normal
child copy is already included in the parent/child content bound. Original raw
sources remain separate evidence obligations in any full-task storage budget.

Per Job: four JSON records <=262144 bytes (request, launch, initial observation,
process observation); five <=2048 bytes (child, release intent, consumed, worker
result, Job checks); one <=4096-byte worker error; one 1-byte lease. The conditional
file-content ceiling is 1062913 bytes, 11 files and 2 directories. It excludes
parent/child storage, the controller's outer lease/directory, other hour Jobs,
source reports, arbitrary scratch/third-party writes, filesystem metadata and
allocation. The scratch reserve is a separate declaration, not a proved bound.
New worker startup/snapshot/replay/controller time remains unmeasured by the full
segmented journal; the 2440-second non-solver budget is not proved.

Tests use real short Windows Jobs. A test-only `-c` launcher installs the existing
synthetic three-stage source fixtures in the child without changing source bytes.
It explicitly adds the located pytest dependency directory for pygments/colorama;
the default entry does not import pytest or extend this path. Two completed hour
Jobs reconstruct carry from scientific replay. Failure tests distinguish actual
injected windows from test-launch failures. A separate default-entry test rebuilds
the real pinned RTS origin and 232-stage inventory, then deliberately supplies
invalid saved raw. It must preserve that raw and fail with no hour outcome; this
is input/guard coverage, not 232 executed stages or a successful RTS hour.

Remaining: native export and raw-before-audit producer wiring, complete worker
segment/observer accounting, all 192 hours and source/carry cases, typed missing
tails, full-task resources and legal reuse DAG/manifest, common Rref/A and complete
LB/UB, seal and fresh official independent review. Every new native run still
requires a concrete ready package and fresh explicit authorization.
