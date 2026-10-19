# Consumer registry read scope development design

Status: DRAFT_NONAUTHORITATIVE; implementation and acceptance remain open.

The current saved-data chain is `152 persisted external heads -> 153 original
numerical oracle -> 154 current Bootstrap5 read-only reopen/inspect/close`.
152's original public `bootstrap` return and graceful cleanup remain unverified.
No new Job is needed to study the remaining reader cost.

## Evidence and target

154 completed in 176.594 s outer / 172.09 s pytest. Its staged body took
122.276 s, including 12.801 s declaration/resolver preparation, 67.978 s owner
construction, 41.496 s public inspection and 0.001 s owner close. Two phase
segments closed, 1512 pins stayed unchanged and the 143 saved input files had
the same names and bytes. This is one diagnostic observation, not a full-chain
budget or repeated benchmark.

Source call accounting is:

| Stage | `_replay` | `_registry` | N0 prepares | Full hour replays | Within-prefix revalidations | Contexts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Read-only constructor | 1 | 2 | 2 | 8 | 8 | 32 |
| Public `BootstrapOwner.inspect` | 1 | 2 | 2 | 8 | 8 | 32 |
| Total | 2 | 4 | 4 | 16 | 16 | 64 |

These are static counts, not measured execution counters. `_replay` checks the
registry once before dispatch and again in its `finish` closure. The current
read path has no registration scope, so each N0 prepare uses the original
full-only fallback. The existing producer registration scope already performs
4 full / 28 fresh / 64 contexts across its four builds; that is a different
lifetime.

146 separately measured the original verifier on saved data: first build
29.823 s and reused builds 20.471/20.599/20.688 s with cProfile. 148's existing
path lease composition reduced that diagnostic's outer time from 153.984 to
134.75 s with equal decision/audit hashes. 145's fixture metadata expansion
showed no benefit and is retired with its findings preserved.

## Intended first change

Use a new versioned graph so Bootstrap5/Owned5/Verifier4/Roster4 and saved152
can retain their exact source lineage:

| Current | Planned successor |
| --- | --- |
| Bootstrap5 | Bootstrap6 |
| Owned5 | Owned6 |
| Historical N0 verifier4 | Historical N0 verifier5 |
| Roster4 | Roster5, after the read scope is validated |

Inside one genuine constructor or one public inspection, open a fresh private
consumer validation scope around that method's original `_replay`. Both
registry calls keep their complete original byte/context observations. The
first complete build produces a proof; only the second build in that same
method may consume it. Close and clear the scope before returning to the caller.

This first step would have the following *planned* count model: 8 full hour
replays, 24 byte revalidations and the same 64 contexts across the two methods.
It does not justify cross-method, cross-callback or whole-Handoff reuse.

Reuse the existing N0 operation algorithm, source/runtime checks, exact-root
binding, build confirmation and failure poisoning. Give the consumer an
original guard and a fresh nonce from the actual consumer lifecycle. Do not
borrow a producer nonce or interpret detached reports as live credentials.

The producer's existing strict completion rule remains separate. An empty
metadata-only registry needs an honest empty read observation; it must not
be presented as a completed numerical registration proof. Consumer execution
metadata must be separate from the unchanged predecessor scientific payload.

## Required verification before a new integration launch

1. Compare the successor verifier against saved152 candidate data and the
   original numerical oracle, with no public owner and no new Job. Preserve the
   exact scientific audit/decision bytes and all 64 context observations.
2. Cover changed bytes, heads, dispatch/source bindings, root/slot aliases,
   foreign threads, guard/nonce replacement, nested/reentrant entry, incomplete
   builds and errors at proof publication and cleanup. Prove that the second
   build cannot consume a proof until the first genuine build is confirmed.
3. Test genuine current constructor/inspect guard ownership and an empty
   registry, then inspect the actual Roster shadow/borrow route before wiring
   Roster5. Reuse of a session outside its original synchronous method is a
   separate design question.
4. Record actual operation counters and a fixed-order same-program comparison
   including scope creation, full initial work, reuse, receipt and cleanup.
   Complete the required independent PRE_SEAL audit of the exact candidate.
5. Only after the successor passes these checks, complete one current public N0
   registration lifecycle. Preserve external callback heads before acknowledgement
   and perform saved-data postchecks without repeating its Job. Three arms and
   genuine Common/Genesis/Parent/Handoff/paired/Post/reopen still need their own
   connected acceptance and complete call/resource budget.

No formal execution, native calibration, production seal, review receipt,
resource admission or engineering conclusion is issued by this design.
