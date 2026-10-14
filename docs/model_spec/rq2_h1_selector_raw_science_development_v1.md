# H1 Rref/A raw capture bridge (development)

This unsealed module composes the closed StageCapture with the closed origin selector
replay. It is a private future producer primitive, not a runnable experiment, Job,
execution authority, persistent lane owner or formal result. Only fake direct-adapter
tests are currently permitted. Real execution requires a concrete owned Job package,
resource gates and separately retained native authority.

The stage key binds the current lane/input/policy, exact saved prefix, stage context
and implementation. The prefix must be an accepted incomplete chain. Prior locks
come exclusively from canonical replay. The builder and capture consumer are owned
inside the primitive; callers supply neither a builder nor a consumer.

Order: build and check fixed export caps; allocate an exclusive root; capture exact
native channels before Pyomo postsolve; retain postsolve sidecar; close adapter;
require completed StageCapture and fresh complete ingress chain; decode and audit;
persist observed metadata; persist derived selector record; persist bridge terminal.
Close failure retains raw/sidecar but produces no selector record. Later persistence
failure is indeterminate; retained files do not authorize retry. A saved selector
record alone is not a completed bridge. Future owners must bind the bridge terminal
to the exact saved record and freshly check retained evidence.

Rref/A uses no N generation projection and no N MIP-only acceptance predicate.
Every negative generation value is rejected exactly, retaining binary64 witness.
Native/Pyomo optimal statuses and ObjVal/ObjBound correspondence must agree;
ObjBoundC must equal ObjBound for this continuous LP bridge. Generic raw decoding
checks model counts/sense, complete variable/bound inventory and exact objective
algebra. The unchanged selector replay independently checks physical feasibility,
gap limits, rational selector semantics and strict previous locks. No threshold is
changed. Only its recomputed objective becomes the next stage lock.

Legacy-shaped GridSolveEvidence is explicitly reconstructed_selector_view. Initial,
consumer and post-close model observations are recorded; package versions are read
before and after; options are declarations backed by the completed StageCapture's
pre-apply check; calls=1 is backed by that capture's one intercepted apply, not by a
caller claim. Original native/postsolve bytes and completion hashes remain linked
in the bridge terminal. This is conditional numerical evidence, not native execution
authentication. Manually assembled records, paths or return dictionaries are not
capabilities. All formal/resource/authority flags stay false in an immutable complete
scope map, checked at entry, persistence bookends and audit return. Schema or scope
rebinding is rejected. `selector_chain_complete` means only numerical replay chain
completion; `completion_scope=selector_replay_chain_only` states that boundary in
the machine-readable terminal.

Only Gurobi direct is supported. Existing fixed export caps remain unchanged and
are checked before adapter allocation, together with caller ReplayLimits and the
continuous-only invariant. The same model admission repeats in numerical audit.
The return is fresh-at-return only: this unit provides no independent cross-process
inspect/reopen/reconcile API. Even a retained terminal after return failure needs
future fresh verification; it does not authorize retry or consumption by itself.
Full source/stage profile coverage, producer
archive bounds, Job/clock, owner tickets, common Rref to A release, paired commit and
192-hour integration remain separate open work. Synthetic fixtures do not fix a
scientific selector configuration or certify resource admission.
