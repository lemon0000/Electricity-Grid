# H1 selector parent controller development

This R3 draft connects the fixed selector launch declaration, owned Job
lifecycle and fresh worker output inspector. It is development plumbing;
phase consumption, resource admission and formal execution remain unresolved.
Real `Parent.run()` reaches a native worker and requires separate specific
authority. The development tests substitute an explicitly synthetic lifecycle
and fabricated adapters in distinct alias modules.

## Ownership and persistence

Construction validates source, role budgets, fixed argv/environment and bounded
parent metadata before creating the parent directory. An exclusive live lease
owns that directory. Create-once `binding.json` precedes every worker directory
and transport file. Snapshot, request and launch are each persisted and read
back. A failed construction leaves its partial directory intact and closes its
lease; the same root cannot be retried.

The parent is bound to its exact module, object, creating PID/thread, registry
entry and filesystem identities. Retained metadata includes bytes and file
stamps, so replacement with equal bytes is rejected. Parent and completion
objects cannot be copied or serialized. This is an integrity boundary inside a
trusted Python process, not a sandbox against arbitrary private-state mutation.
Public owner entry wrappers capture the original checker and exact owner type;
foreign objects and subclasses fail before side effects. Registry reservations
reject nonce collisions and removal applies only to the same owner object.
Failure cleanup captures the original lease close, PID/thread functions and
registry/lock. Context exit calls that captured cleanup even if callback code
replaced the public close methods or module registry names. Cleanup remains
available after scope validation fails.

`run()` is single-attempt. The suspended-child callback persists and reads back
initial observation, child identity and release intent, in that order. It then
rechecks all six inputs, source, launch identity and any reference dependency.
The output inspector is invoked only from the lifecycle's successful
post-quiescence callback. Callback order is exact and callback payloads are
retained as immutable canonical bytes. The lifecycle return must match those
payloads. The parent terminal jointly binds the declaration, live observation,
full output diagnostic and reference dependency. It is written and read back,
then all retained science/timing/transport evidence is freshly replayed before
issuing a completion. Any attempted-run failure invalidates the attempt, even
if a terminal was already written; retained files are preserved.

## Reference-to-Actual correspondence

Actual requires the exact original completion from a still-open Rref parent
of the same module and creating process/thread. It holds that parent's
operation lock throughout its run and subsequent completion validation.
Closing Rref invalidates dependent Actual validation. An archive, copied
completion, detached JSON or another module's object cannot substitute.

The reference root and terminal map to the scientific sequence. Scientific
request and timed-sequence request hashes are distinct: Actual consumes the
scientific configuration hash; the timing request remains bound independently
by the worker/inspector diagnostic. Parent terminal hashes remain distinct from
both scientific and timing terminal hashes. The scientific request hash is
derived from the fresh checked request's `scientific_configuration`.

The common hour, manifest, source binding, run configuration and entire source
provenance must match. Common phase request, state, source audit, observation
and exogenous projection must match too. Role-specific before-state, selector
and dependency fields are not compared across roles. Provenance comparison is
deliberately conservative: it requires the exact same global journal head,
rather than proving an ancestor relation. A legitimate intervening append may
therefore be rejected. This restriction does not reduce any formal obligation.

## Validation scope and open boundaries

Tests exercise real local journals, immutable record I/O, scientific and timing
replay over fabricated results. The lifecycle proxy runs the fabricated worker
in-process and declares synthetic observations; it never creates a Windows Job.
It is an independent module, not a replacement of the shared canonical
lifecycle. Alias implementation identities differ from canonical identities.
These cases test controller state transitions and correspondence, not a
canonical released worker or authenticated real Job/native execution.

Required development cases include Rref/Actual success, foreign or changed
completion rejection, lifetime/thread restrictions, duplicate callbacks,
return-payload mismatch, input/output replacement, and failures before/after
each owned write. Tests must preserve failed attempts. Closed predecessor pins
and both historical outer/run inventories must remain unchanged.

Declared byte/commit envelopes are not allocation quotas or resource admission.
Parent clock endpoints are diagnostic and are not joined to worker clocks to
prove the full non-solver allowance. Persistent paired phase commits, hours
1 through 191, legal reuse DAG, common-contract bounds, full resource admission,
successor sealing and fresh official review remain open. All inherited authority
flags plus `owner_consumption_authorized`, `parent_phase_commit_verified` and
`live_parent_completion_detached_replay` remain false. PRE_SEAL findings are not
an official verdict or run authority.
