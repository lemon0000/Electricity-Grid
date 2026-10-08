# H1 lifecycle timing coverage audit

Status: DRAFT_NONAUTHORITATIVE. This audit defines the remaining measurement
boundary from current source and a zero-native counterexample. It supplies no
worker integration, budget verdict, or execution authority.

The durable journal takes its terminal tick in `Journal._event` before terminal
metadata persistence. `Journal.finish` then performs full fresh inspection.
Neither operation is inside the returned recorded window. The diagnostic runs
the real journal with a deterministic clock and injects terminal write and fresh
inspection costs. A 100 ns body plus 1000 ns write and 2000 ns inspection returns
100 ns recorded and 3100 ns enclosing elapsed: 3000 ns is outside the journal.
These are synthetic durations; actual disk timing and performance are not measured.

`NormalTaskChild._initialize` starts its monotonic clock before initial headroom
inspection and suspended child creation. `wait` ends its reported elapsed after
whole-Job quiescence, exit-code/peak-memory queries and identity checks. It thus
encloses worker startup/imports, execution, worker final writes and exit, and the
controller observation work occurring concurrently in that interval. It excludes
the caller's request/launch preparation before `_initialize`, context-manager
close after `wait`, observation persistence, subsequent fresh result inspection,
and parent outcome publication. Its elapsed is a Job supervision window, not a
whole parent transaction measurement. The saved controller currently invokes
saved reports only, not the timed native hour successor.

Required successor accounting boundary:

1. Start a controller-owned monotonic envelope before transaction preparation;
   retain process creation identity, request identity and controller owner.
2. Worker phase records provide attribution. Unknown/unclassified intervals are
   charged to non-solver; journal end writes and inspection stay inside the outer
   envelope. Worker startup and shutdown cannot rely on a worker-only journal.
3. Observe whole-Job quiescence before external inspection; finish the envelope
   after result inspection and parent outcome publication. Report the final
   accounting record's own persistence separately as a declared observer tail.
   A receipt cannot include the cost of writing itself in its already fixed tick.
4. Retain independent observer call intervals and overlapping worker intervals.
   Their elapsed times must not be added as if sequential, nor subtracted from
   non-solver to improve admission. Concurrent observer wall is diagnostic; it
   does not establish counterfactual worker time without observer interference.
5. Subtract native elapsed from an enclosing wall only after proving complete
   stage coverage, sequential disjoint calls, common clock rate/units and actual
   containment/owner/Job identity. Existing per-stage random clock-domain labels
   and aggregate native_total alone do not prove this bridge. Do not subtract
   timestamps across domains or infer containment from total <= wall.
6. Persist failures as incomplete/unknown; absence of an end/receipt is never
   zero cost. Include new accounting files and observer tail in the successor
   resource specification before any component-budget verdict.

The next implementation should wrap the complete controller transaction and
bridge the worker's native intervals to it, then add phase attribution within
that envelope. Reusing the journal terminal or current Job elapsed alone would
leave measured costs outside the proposed budget. All existing frozen sources
remain unchanged. Full worker/Job integration, resource admission, the 2440 s
non-solver budget, official independent review and new native authorization remain
unresolved.
