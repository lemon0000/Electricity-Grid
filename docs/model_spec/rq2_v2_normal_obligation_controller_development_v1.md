# Obligation gate on the live normal controller

R3 DRAFT_NONAUTHORITATIVE. The successor fixes a training-UB obligation and a
168-hour enrollment declaration and exact Job budget at construction. It inherits the existing
timed controller's source/carry replay, suspended Job release, whole-Job exit
check and parent outcome. Actual native use still requires an admitted package
and new explicit authorization.

The outer obligation guard precedes the clock, controller and parent guards.
Whole enrollment prevalidation executes in the clock headroom hook, before
either clock or source intent. Binding occurs in the existing live pending
scope with the controller and source writer leases held. The binder's evidence
and false authority flags are preserved.

Before calling the old Job writer, the controller computes the exact canonical
worker request SHA and records it alongside the obligation binding. The old
writer's dynamic `_check()` call, while the child is suspended and before
`release()`, checks this actual request SHA and all retained obligation bytes.
A changed request, changed binding, missing file or incompatible parent aborts
the transaction. The old worker schema and numerical input are unchanged.
`worker_obligation_authenticated=false`: the obligation is a controller claim,
while the worker authenticates the same exact numerical request SHA.

The independent obligation directory contains a header and binding/job-link/
terminal records for each accepted hour. Each terminal links its predecessor,
the Job link, old clock terminal and parent outcome/anchor. Failure before
release retains intent; failure publishing a Job link retains exited Job
evidence without parent acceptance; failure publishing the terminal can leave
an accepted parent outcome but returns no successor completion. All such
failures poison the live controller and forbid retry.
Only final terminal confirmation mints `last_obligation_observation`, an owned
frozen return containing hour, header/terminal pins and outcome head. Entry or
failure clears it; copying, replacement and serialization cannot mint it.

The historical reader follows externally pinned terminal/header identities.
It obtains each packet from a full source-parent prefix replay, reconstructs
the historical obligation record, verifies the old Job and clock evidence, and
checks the complete terminal chain. It does not invoke a pending-only binder
after that pending state has been consumed. Historical verification does not
recreate live release authority.
The one-byte Windows lease is observed by file identity and size, without
reading a byte held under an active writer lock.

Tests distinguish two evidence scopes. Real pinned RTS/marginal inputs exercise
the inherited release path using a test-only suspended-child interception;
this launches no process and produces no solver result. Separate synthetic
source/catalog seams and saved reports exercise actual short Windows Jobs,
continuous synthetic carry and publication failure windows. These cannot prove
real RTS later-hour feasibility or a complete 168-hour scientific witness.

Additional logical content is at most `(3H+1)*128KiB+1` bytes in `3H+2` files,
including the header and one-byte lease. The combined headroom observation
adds remaining obligation records to the old Job, parent, clock and scratch
demands. This is not filesystem allocation, memory, wall-time or whole-study
admission. Repeated full enrollment and dependency verification is currently
expensive; validated reuse and complete lifecycle accounting remain open.
The successor terminal publication occurs outside the old bridge interval.

This unit does not supply common Rref/A, legal cross-task solver reuse, the
complete executable task inventory, LB/UB certificates, full producer/export
coverage, a 2440-second component proof, official review or formal-run authority.
Independent R3 pre-seal review and terminal test evidence are required before
calling this development unit closed.
