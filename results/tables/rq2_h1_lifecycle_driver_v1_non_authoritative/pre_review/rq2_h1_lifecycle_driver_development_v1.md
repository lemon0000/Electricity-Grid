# H1 fixed lifecycle driver development v1

Status: DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT; R3. Root is the only writer.
No native authority, official verdict, threshold change or resource admission.

`run` composes the existing Job clock bridge controller. It has no callback,
resume or CLI. A fixed external tuple of H source identities declares exactly
H hours (1..192), and the controller receives that same H. It uses the original
source/carry protocol and raw/science/native timing implementation unchanged.
Calling it with a real adapter requires a newly authorized concrete package.
The inherited short development Job ceiling remains 300 seconds per hour.

The first QPC tick precedes root acquisition, binding, controller construction,
initial source replay, the fixed hour loop, accounting reads, final complete
parent/source replay and controller close. Each next head is the previous live
parent outcome. Each step must supply the exact private bridge Observation;
its hour/head/native totals must agree with the fresh overshoot reader using
that hour's reconstructed pinned source/carry packet, spec and limits.
The driver records initialization, preparation, step, accounting-reader,
final replay and close intervals. Per-hour bridge windows must be contained in
the sequential driver step windows. The original bridge proves native
containment within each of those windows, including actual worker/Job identity.

Only the single continuous `end - start` is the driver wall. Diagnostic call
intervals are already included and are neither added nor deducted. Work not
assigned to a detailed worker phase remains in the enclosing wall. The
candidate charge is

`wall - sum(actual_native_i) + sum(max(0, actual_native_i - reserved_i))`.

Reservations and overshoot use the prior exact Fraction accounting; unused
per-call reservations never offset another call's overshoot. There is no 2440
second comparison. Worker granular phase integration is still outstanding;
it is attribution, not permission to remove unknown work from this charge.

After successful complete-prefix replay and controller close, the driver
takes the main end tick. Terminal encoding, create-once write/fsync/readback,
metadata inspection, final checks and driver lease release follow. A final
live tick measures this accounting-persistence tail. It is returned only in a
private Completion; it is not recursively persisted. Driver lease ownership
is detached before close. The receipt's own construction, return, caller,
module imports and process exit remain outside this declared window.

On any exception, no Completion is returned, no retry is offered, and all
partial records and parent outcomes remain. A terminal file may exist even
when terminal confirmation, lease close or the final tick failed. Stored
terminal existence is therefore never live successful-return evidence.

The fresh driver reader checks bounded exact root/clock topology, externally
pinned record bytes, request/parent linkage, the H-hour metadata chain,
source/head/bridge pins, ordered intervals and conditional arithmetic. It
does not perform full science replay or reconstruct live process authority.
The live writer separately requires complete parent/source replay before
close. `declared_driver_call_window_complete` is true only on the private
live Completion; stored/read flags remain false. Full program lifecycle,
observer overhead separation, component budget and formal gates stay false.

Additional logical content is `(2H + 3) * 524288 + 1` bytes, `2H + 4` files,
one root directory, including the one-byte lease. This excludes the complete
controller subtree, scratch, filesystem allocation and memory. H=192 gives
202899457 bytes and 388 files. Before each hour, same-volume live headroom
combines this conservative whole metadata bound with the current Job,
parent update, remaining bridge records and scratch. This is an observation,
not a reservation or full-task admission. Bounded records retained in memory
and the underlying source/replay implementation need separate memory bounds.

Validation uses exact arithmetic and invalid-input cases, create-once failure
paths, a real short Windows Job with a synthetic three-stage adapter, stored
metadata drift and failures after a committed parent outcome. H=192 is only
a content declaration test, not an executed chain or producer coverage proof.
