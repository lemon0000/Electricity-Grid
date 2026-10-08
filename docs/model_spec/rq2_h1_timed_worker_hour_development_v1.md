# H1 owned timed worker-hour envelope

Status: DRAFT_NONAUTHORITATIVE. `OwnedWorkerHour` internally constructs the
existing timed `OwnedHour`, requires its exact live completion and successful
owner state, and performs fresh scientific replay before worker publication.
There is no CLI or Job launcher. A real call remains native-capable and requires
separate explicit run authority and resource/Job supervision. Tests use synthetic
adapters and saved scientific assignments only.

The wrapper checks actual Windows PID and process creation FILETIME against the
caller's expected identity, retains its creating thread, and binds an external
controller request SHA. That SHA is a link supplied by the caller; the wrapper
does not independently verify controller release or Job membership. A create-once
NTFS lease protects the worker root until all publication/fresh checks finish.

Local clock contract: Windows CPython, the retained built-in `perf_counter_ns`,
monotonic/non-adjustable `QueryPerformanceCounter()` profile, unchanged timing
`Measurement.__init__` function and its exact default clock. The existing timed
capture constructs Measurement without a custom clock. These checks bracket the
owned hour; the serialized profile records Python version and clock resolution.
This is a trusted Python execution contract, not a security boundary against
arbitrary monkeypatching/object mutation or proof of the C/native solver's origin.
Per-stage UUID labels remain identifiers rather than independent clock evidence.

After full-hour replay, all native timing bindings must name the worker PID and
thread; all stage indices are contiguous and all clock labels distinct. The
whole apply intervals must be ordered, nonoverlapping and contained within the
worker constructor-entry/end-tick window, with native start/end contained in each
apply interval. Exact integer arithmetic computes:

`worker_window_non_native_ns = (end_ns - start_ns) - sum(native_end - native_start)`.

This subtraction is conditional on the live local default-clock contract and
complete owned stage chain. A small native sum alone does not prove containment.
All rows are bound by an interval-vector SHA, the hour terminal and worker terminal;
their full bytes/identities are reread. Worker confirmation also reruns complete
hour science. Complete hour snapshots (all science/commit/projection/timing bytes
and identities) bracket both conditional reader inspection and owned worker
confirmation before lease release; timing-only rechecks are insufficient.
Original numerical predicates, approved generation mapping and
scientific projection remain in their existing versioned modules.

The end tick precedes final arithmetic, terminal publication and worker fresh
confirmation. Those operations and the lease release are included in a separately
returned live `confirmation_tail_ns`. The final tick is not persisted; receipt
construction, guard release, subsequent caller work and process exit remain
outside this interval. Constructor-to-run idle time is conservatively inside it.
Worker module imports/process startup are outside it. No complete-worker-lifetime
or cross-process controller subtraction follows from this local envelope.

Only an owned successful run returns the token-protected Completion with
`local_clock_binding_checked=true`. The read-only inspector takes external worker
binding/terminal/implementation pins and replays the full hour plus containment
arithmetic. Its clock-source authentication and owned-return flags remain false,
and its confirmation tail is unknown. It does not recover a live receipt or Job
membership from stored bytes. It checks the current environment profile, not
historical clock authenticity. All scientific/formal/resource authority flags
remain false in both interfaces.

Publication, fresh-inspection, owner/clock/interval mismatch or cleanup failure
poisons the worker and cannot yield a Completion. The hour may already have a
valid terminal when outer worker publication fails; all evidence remains in place.
There is no retry/resume. Lease references detach before fixed close, preserving
the existing finally-release semantics and avoiding duplicate old-owner cleanup.

Tests run the real DirectSolver orchestration and timed apply body with a
three-stage synthetic native adapter, retaining actual Windows process identity
and the real default QPC clock. They compare the final scientific projection to
the prior saved-report oracle, exercise publication before/after effects, clock
and owner mismatches, overlap despite small totals, and final-reader failure.
The durations are synthetic-work timings, not real native performance. No actual
Gurobi optimization or full 232-stage hour is performed.
Additional failures mutate early science/commit bytes after outer inspection
returns, preserving length/mtime, and inject fixed lease unlock before/after its
effect or register a new owner after release before reporting an error. No case
may yield worker Completion, and old cleanup must not remove the new registry.

Added controlled file content is two metadata files capped at 2048 bytes each
plus the one-byte execution.lock: 4097 bytes, three files and one wrapper directory.
The existing hour subtree is additional. Memory for interval vectors, replay,
filesystem allocation, external inputs, native scratch/logs, process lifecycle
and controller/observer output are excluded. Full resource admission is open.

Next: wire this owned worker into a versioned independent Job/controller; verify
request/release/consume, PID/creation and Job membership; establish the cross-process
clock/containment bridge; add complete phase/observer attribution and lifecycle
tails. Whole producer coverage, resources, actual task DAG/manifest and scientific
certificate obligations, sealing and a fresh official independent review remain
open. The 2440-second non-solver budget and new native-run authority are unresolved.
