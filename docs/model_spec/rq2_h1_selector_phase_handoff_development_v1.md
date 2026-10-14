# H1 live selector phase handoff draft

Status: DRAFT_NONAUTHORITATIVE, implementation and verification in progress.

The hour-0 handoff consumes existing live `Parent` owners and their exact issued
completions. It has no selector/native launch entrypoint. All existing formal,
resource and execution flags remain false. Its returned dictionary is a fresh
diagnostic, not a detached execution or continuation credential.

The private adapter acquires Actual guards in canonical lane order, then the
single Rref guard, then the common genesis/roster guards. It validates original
completion identity and fresh scientific/timing archives under those guards.
The full manifest lane dictionary is required. A `None` Actual entry is accepted
only when internal current-source/business replay establishes business-input or
business-candidate unresolved before Actual. A missing completion for required
Actual work remains pending. An incomplete Actual is not silently converted to
an authenticated failure. Existing group audit retains proof and separate
joint-B6 obligations.

The create-once handoff root has its own lease. A complete packet stores raw
record-bearing tickets, holder record bytes/heads, predecessor receipts, parent
identities, exact source/group audit and the previewed projection. The packet is
written and stably read before its immutable binding, which includes its file
stamp. A bounded five-event child journal then binds that packet and binding.
No external callback or predecessor close occurs before the packet and binding
exist and are checked. Partial pre-intent roots are unauthoritative orphans.
Header, binding, packet and whole five-event branch capacity are checked before
any predecessor close, including a conservative bound on file-stamp integers.
`max_archive_bytes` covers only these handoff JSON bytes. It excludes the two
lease markers, directory metadata, predecessor holder/SQLite bytes and physical
disk overhead; it is neither a full phase archive cap nor resource admission.
The binding retains the canonical outer root and exact directory/lock-file
identities, in addition to the packet file stamp.

Journal order is `takeover_intent`, `handoff_opened`,
`holder_head_prepared_1`, `holder_head_prepared_2`,
`bootstrap_consumed_terminal`. Each event requires external retention of its
exact prospective journal head. Each holder callback verifies the complete
preplanned retention tuple and persists its prepared event before returning the
holder head. Thus stored planned hashes do not stand in for runtime retention.

The old empty-only genesis wrapper is closed under its held common and roster
guards. Original holder and phase roots reopen using exact retained genesis
heads, headers and holder binding.
The packet also retains the original phase database, directory and lock-file
identities; reopening and later correspondence require those exact objects.
The immutable binding must match its intended raw bytes at its first readback.
Closed common correspondence is checked
through the fixed roster projection, not by calling the closed wrapper. Parent
guards remain held through phase advance, exact holder/DB/head readback, source
replay and the final journal terminal. External callbacks are checked before and
after; the first post-callback check uses the original captured checker. Project
callables and protocol constants are pinned in process. Prepared transaction
bytes, original handles and file views are retained outside mutable instance
fields; cleanup closes those originals. External-active state and retention
counts reside in the closure-owned registry. A per-call token held in the
retention invocation is required to leave the external callback and advance
its journal count. Callback reentry is rejected, including flag mutation and
direct calls to the module's state-transition helpers.

Closure-owned resource capsules retain each original lease, open stream, registry
key, directory/lock identities, child aliases and operation guards. Cleanup closes
the captured file descriptor directly and releases only guards recorded as held
by this call; it does not invoke child close methods through mutable fields.
Common/roster/owner guards are captured at acquisition and released directly.
Before takeover, callback field replacement causes permanent handoff failure.
Borrowed references are restored and revalidated under those guards against the
original durable common view; the predecessor is returned live only if this fresh
validation succeeds. Failed revalidation poisons the borrowed capability and
requires caller disposition. It does not close or reconstruct that capability.
Actively closing an original external stream, releasing/reacquiring raw locks,
or inspecting Python frames/closure cells is outside the recoverable field-change
boundary. Such capability destruction grants no retry, adoption or science result.
An already closed captured stream never causes cleanup to discard a registry key
that could belong to a subsequent owner.

Parent capture provenance fixes root, binder, holder and phase receipts exactly.
Its captured global head may be a known ancestor of the current held global
chain, allowing unrelated groups to append. The handoff fixes the current group
projection throughout its own operation. The existing Parent restriction that
Rref and Actual use the same capture provenance remains unchanged.

Every failure is single-attempt and preserves bytes. New handles are closed;
predecessor handles remain caller-owned before takeover; integrity loss poisons that borrowed capability. They remain closed if
the handoff has closed them. A retained head without a holder file, a ticket
without a DB row, an intent without outcome, or outcome without controller
terminal is not automatically repaired. This module does not implement recovery
or metadata reconciliation. It does not infer a retained head by scanning.

Even a completed hour-0 handoff is not an `episode_terminal`: all lanes halting
still requires the existing phase terminal action. Hour-1+/192-hour producer
coverage, failed-Actual typed evidence, canonical native/Job success evidence,
full study/reuse/resource admission, successor seal, new official review and
specific new native authorization remain open.

Tests use the existing synthetic Parent alias, source/roster fixtures and
fabricated selector adapters. Such tests can exercise real file/SQLite/lease
ordering, but cannot prove canonical Job/native execution or formal readiness.

Borrowed abort validation is unconditional after any external callback before takeover: unchanged public fields do not establish durable integrity. Captured references and fields are restored inside the same exception boundary as fresh lease and common durable-view checks, including deleted attributes. Integrity loss poisons the borrowed owner and leaves original resources for caller disposition, without automatic close, reconstruction or retry.
