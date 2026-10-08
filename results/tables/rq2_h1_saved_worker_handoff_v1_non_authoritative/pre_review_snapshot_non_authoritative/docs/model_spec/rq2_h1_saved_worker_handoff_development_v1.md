# H1 synchronous saved worker handoff development v1

Status: DRAFT_NONAUTHORITATIVE. This integrates the existing typed snapshot into
a fixed saved-report worker. It is not an independent hour Job or native route.

`LiveSavedController` constructs its own exact bounded parent with `create=True`.
It accepts neither an existing owner nor a reopen/continuation token. The parent
guard and all three writer leases remain held across this synchronous sequence:

1. Restore the ready prefix; check the external predecessor and source pin.
2. Rebuild source/clock/carry, append intent, and confirm its independent anchor.
3. Open the pinned read-only snapshot while the current child is absent; rebuild
   `PendingWorkerInput` from the saved prefix and current pinned source.
4. Consume one in-memory transfer before any child creation. Validate the typed
   input against a separately retained receipt SHA and parent, intent, source,
   request, packet audit, anchor and live journal context.
5. Create the fixed attested child with that input. Store all supplied raw reports
   before guard/scientific audit, require the complete stage count, and finish.
6. Close and independently reopen the complete child; compare its typed result.
   Revalidate the source, append/anchor the outcome, and restore the accepted state.

The entire step uses `solver_calls_forbidden`. There is no arbitrary worker
callback. The supplied saved-report iterable is consumed once. Reentrant public
operations fail at the parent guard. Any failure poisons the live parent; a used
transfer cannot be consumed again. Partial evidence and unanchored tails remain
in place. No cleanup, retry, resume, synthetic outcome or repair is performed.
An anchor may already have advanced when a later confirmation fails; this does
not restore the poisoned controller's execution rights. Close remains teardown.

`last_input_receipt` is only the most recent successful input's in-memory bytes;
it is not a journal or a continuation token. The snapshot receipt still reports
writer-lock authentication, quiescence, native execution, independent Job,
resource admission and formal readiness/result as false. The live owner provides
only synchronous in-process saved handoff; its pins are not independently issued
run authority. A crash loses this handoff state. A future process/Job boundary
requires a new durable one-shot protocol and explicit native run authorization.

The underlying bounded parent declaration, archive topology and scientific
replay are unchanged. This controller implementation is checked during each live
step, but old disk archives alone do not attest that this controller produced
them. No handoff files or extra raw copies are added; the prior conditional
file-content bound still applies to this saved path. Handoff memory, replay time,
Job/scratch, filesystem allocation and complete research resources remain unproved.

Tests use synthetic three-stage saved witnesses, including a second hour built
from actual prior carry. They cover absent-child snapshot order, one consumption,
reentrancy, fresh reopen, snapshot/receipt/constructor failures, partial iterator,
finish/source failure and both sides of outcome anchor advancement. All are
zero-solver development tests, not 192-hour producer coverage or official gates.
