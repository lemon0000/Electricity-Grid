# H1 optimize-call timing boundary development v1

Status: DRAFT_NONAUTHORITATIVE. This is the exact-call prerequisite for timed
collector/worker integration; it is not integrated into existing owned hour or
native capture. Calling Measurement.apply with a real adapter requires separate
explicit authorization and Job supervision. No CLI or run authority is supplied.

The installed Pyomo 6.10.1 _apply_solver includes option/log setup before optimize
and bookkeeping afterwards. Its whole interval is not native optimize time.
Also, existing durable Journal.span samples begin before fsync/readback, so its
native span includes journal persistence. Both would undercount non-solver work
if used as the amount subtracted from worker wall.

The new versioned apply copy preserves native model identity and pins the
installed module bytes, version, original apply source and _set_options source.
Before invocation it also checks relevant runtime function identities. An AST
comparison removes the single measurement.invoke insertion and requires exact
equality with the installed apply body, including stale marking, log setup,
environment-option filtering, suffix handling, optimize, _needs_updated and log
reset order. There is exactly one optimize call. Current protocol rejects
non-None callbacks before apply; no model facade or C-object method replacement
is used. This is a trusted Python boundary, not security against arbitrary module
or object mutation.

Ordering is binding → apply start tick → option/setup work → durable optimize
intent (write/fsync/fresh readback) → native start tick → optimize(None) once →
native end tick → linked completion write/fsync/readback → apply bookkeeping →
apply end tick → terminal → independent fresh inspection. Thus intent and
completion persistence are outside native duration and inside the measured apply
window. Clock reads, validation and Python dispatch at the immediate call edges
are part of this measurement boundary; it is not Gurobi Runtime or a pure C-only
algorithm time. Runtime is not substituted for the externally sampled interval.

Any escaping error after guard acquisition poisons the owner and returns no
successful timing receipt. A failed guard acquisition rejects without poisoning
an active owner. Optimize exceptions, clock reversal, begin/end/terminal write or
confirmation errors and apply tail failures preserve partial records. Missing or
unacknowledged terminal means unknown, never zero time; complete-looking files
left after confirmation failure cannot supply an owned successful return.

The writer checks canonical root and plain directory identity before native
invocation. The reader needs independent binding/terminal/implementation pins and
rechecks the directory identity; noncanonical aliases and directory replacement
reject. This does not assert protection against hostile concurrent filesystem
mutation between individual checks. The reader also checks
exact records, source pins, clock owner/domain, linked hashes, finite bounded
integer ticks and native interval containment in apply window; full file views
are reread before returning conditional durations. It cannot infer a live call
returned, unique native execution, whole Job quiescence or directory-entry power
loss durability. Four metadata files have an 8192-byte total content cap; this
excludes all other worker/resource costs.

Tests use fake models with installed apply-body semantics, delay intent and
completion persistence, and prove only optimize's simulated 73 ns enters the
native interval. They cover preserved branches, exactly-one call, exceptions,
clock/owner/callback/source drift, publication failures and fresh-reader
corruption. Three independent synthetic intervals are not full-hour evidence.
Actual Gurobi/symbol-map, timed successor capture/science/hour integration,
complete phase/observer accounting, crash supervision and resource admission
remain open. The apply window excludes binding construction and terminal/review
work; an outer worker/Job observer must include these in non-solver time. No
2440-second component-budget conclusion follows; coverage/resource/formal flags
remain false.
