# H1 selector stage mathematics and saved-record replay

R3 DRAFT_NONAUTHORITATIVE. This successor consumes detached H1 physical frames
and candidate lane history. It has no native executor, persistent owner,
common-prefix publication or business/physical transaction.

Reference uses `P_ref` in `[0,B]`, then minimizes `(B-P_ref, L1 deviation from N,
generation by sorted UID)`. Actual uses the prescribed exact power and minimizes
`(L1 deviation from N, generation by sorted UID)`. All generator UIDs participate,
including fixed/curtailable/disabled units. Reference and actual lanes cannot
be interchanged. The reference request is `Q(str(B))-Q(str(P_ref))`.

The old ReferenceSelectorSpec/ActualDispatchSpec are reused only as parameter
grammars. New policy identity binds the H1 information/physical/selector code,
old mathematical sources, replay dependencies, solver options/version/spec,
lane and explicit replay limits. Policy must remain constant along its candidate
trajectory. Full-scale resource admission is separate from these local caps.

Every canonical record has an exact stage envelope: input/policy/implementation,
lane/power, solver specification, limits, model structure, index/label/purpose,
prior locks and their binary64 hex values, raw evidence and claimed canonical
objective hex. External SHA pins are required. The internal builder reconstructs
every stage; callers cannot supply a builder or executor. The existing
`grid_evidence_replay._replay` rechecks native-shaped metadata, full assignment,
runtime/options, model structure, objective and residuals. This establishes
consistency only, not historical native execution or source authenticity.

Each stage also repeats the selector's rational deviation/lock and fixed-power
physical audit, and preserves the old gap gate: finite nonnegative LB/UB/objective,
LB <= UB and LB <= objective; absolute UB/objective difference at most
min(feasibility tolerance, 1e-9); absolute and relative gaps within selector
parameters. The relative denominator remains max(abs(UB),1e-12). Lock tolerance
must not exceed absolute gap <= 1e-6. Reference L1 auxiliary tightness is required
from its L1 stage; actual requires it from its first stage. Values are not rounded.

The next frozen RHS and returned canonical hex come exclusively from the replay
diagnostic's recomputed objective. Original raw fields remain in the caller's
immutable records. A complete successful chain requires n+2 reference or n+1
actual stages, with final generation identical to the physical carry. Prefixes,
timeouts, infeasible/feasible-only statuses, changed contexts, failed audits or
gap gates yield no candidate. No retry or suffix execution occurs. A rejected
record is not a mathematical infeasibility certificate.

The output is a nonpublished numerical candidate with source/native/normal
authentication, detached-consumer authentication, common publication,
reference_or_actual_ready, formal_result and security_certified all false.
Exact lexicographic, causal and infeasibility certificates are absent. Replay
invokes zero solvers; recorded calls describe supplied historical records only.
The synthetic fake-solver tests manufacture internally consistent records and
do not demonstrate an optimum or any actual native execution.

The existing analytic zero-face optimization remains a later H1 adaptation,
requiring an authenticated accepted prefix and exact zero L1 before applying
its model-algebra proof. This full-stage replay does not replace that proof or
provide the eventual raw ingress, Job/timing, conflict registry, lane persistence,
publication or atomic business commit. Repeated source/closure checks are not
claimed to meet the study's runtime budget.
