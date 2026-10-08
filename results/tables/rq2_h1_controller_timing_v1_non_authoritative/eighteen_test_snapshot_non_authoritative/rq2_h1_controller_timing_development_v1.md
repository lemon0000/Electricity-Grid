# H1 saved controller transaction timing

Status: DRAFT_NONAUTHORITATIVE. The new `TimedSavedController` subclasses the
existing saved-only controller and calls its unmodified transaction and cleanup
methods. It creates no native route. Scientific carry, worker execution, Job
validation and parent publication continue through the existing implementation.

Three separate windows are observed by the creating controller thread's clock:
constructor entry through initialized controller, each `step_saved_job` entry
through parent outcome publication and fresh restoration, and final controller
close. Each has a transaction end tick followed by durable timing-record writes,
fresh inspection and a live confirmation tick. The live `Observation` separates
transaction wall, confirmation tail and their sum. The last tick is not persisted;
its subsequent object construction/return remains outside the reported interval.
Caller setup, idle time between calls and arbitrary work outside these entrypoints
are outside these windows. They are not a complete-program wall measurement.

Each hour intent precedes the base transaction. Its start includes wrapper checks,
intent writes, source/carry preparation, request/launch creation, suspended Job
creation and initial headroom checks, release, worker startup/work/exit, whole-Job
quiescence, controller result checks and parent outcome. The end follows the base
method's final fresh restoration and wrapper checks. Terminal publication and
fresh timing/Job reference verification are charged to confirmation tail. The
existing Job elapsed remains diagnostic and is neither added nor subtracted.

Binding records schema/implementation closure, controller PID/thread, a unique
clock-domain label and constructor start. Live ownership uses one nonblocking
guard, monotonic ticks across calls, exact fixed byte/identity views, bounded
directory listings, create-once per-hour paths, sequential indices and previous
terminal pins. The terminal binds the accepted parent head, hour count/status and
request/child/observation/Job-check byte hashes. Existing implementation pins are
unchanged. Directory fsync/power-loss durability is not claimed.

The conditional reader requires external binding, intent, terminal and
implementation pins, rechecks current-hour file topology, full byte/identity
views and basic successful quiescent Job identity. It does not rerun scientific
parent replay, validate the full timing prefix, or recover the live confirmation
tick. Its `scientific_replay_verified`, `prefix_verified` and `live_return_observed`
are false; `confirmation_tail_ns` is unknown. It cannot grant continuation.

Any exception after entering the timing guard poisons the wrapper and parent.
Reentrant guard rejection leaves the active owner unchanged. No retry/resume is
available. An outer terminal publication/confirmation failure can occur after a
valid parent outcome is already durable: that outcome is preserved, but the
wrapper raises and produces no new live observation. Cleanup remains available
after poison and does not manufacture successful timing evidence. A stored
terminal alone does not establish successful return. Trusted Python method
ownership is an application contract, not protection against arbitrary monkey
patching, direct base-method calls or object mutation.

Tests first use a deterministic clock and stubbed base controller to isolate
timing failures. Real short Windows Jobs then cover a successful synthetic saved
hour, nonzero worker exit and outer terminal confirmation failure after durable
parent outcome. All worker routes forbid solver calls. A delayed 7 ns intent,
100 ns transaction, 1000 ns terminal write and 2000 ns fresh inspection produce
107 ns transaction and 3000 ns confirmation tail; these are synthetic values.

The added controlled-content ceiling for H<=192 is `(3+2H)*2048` bytes, `3+2H`
files and `1+H` directories: binding, initialization, close and per-hour
intent/terminal. For H=192: 792576 bytes, 387 files, 193 directories. This excludes
the unchanged underlying controller/Job/parent/child files, filesystem allocation,
memory, external input, scratch and native logging. Partial failures create a
subset of these controlled files. The ceiling is not total resource admission.

Open work: connect the timed native hour to a successor worker/controller;
establish common clock rate/units and native interval owner/Job containment;
instrument worker phases and overlapping independent observer calls; budget the
final unpersisted confirmation/return tail and caller lifecycle; validate all-hour
coverage, full resources and scientific task obligations. No cross-domain native
subtraction is performed. Instrumentation, observer separation, 2440 s component
budget, resource and formal gates remain false. New native execution still needs
a concrete ready package, fresh official review and explicit authorization.
