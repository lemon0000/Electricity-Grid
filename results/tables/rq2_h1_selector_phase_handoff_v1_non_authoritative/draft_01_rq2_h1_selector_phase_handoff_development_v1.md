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

Journal order is `takeover_intent`, `handoff_opened`,
`holder_head_prepared_1`, `holder_head_prepared_2`,
`bootstrap_consumed_terminal`. Each event requires external retention of its
exact prospective journal head. Each holder callback verifies the complete
preplanned retention tuple and persists its prepared event before returning the
holder head. Thus stored planned hashes do not stand in for runtime retention.

The old empty-only genesis wrapper is closed under its held common and roster
guards. Original holder and phase roots reopen using exact retained genesis
heads, headers and holder binding. Closed common correspondence is then checked
through the fixed roster projection, not by calling the closed wrapper. Parent
guards remain held through phase advance, exact holder/DB/head readback, source
replay and the final journal terminal. External callbacks are checked before and
after; callback reentry is rejected.

Every failure is single-attempt and preserves bytes. New handles are closed;
predecessor handles stay live if takeover has not started, and remain closed if
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
