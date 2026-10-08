# H1 native-timed capture/science/hour successor development v1

Status: DRAFT_NONAUTHORITATIVE. Four new versioned modules preserve the existing
capture/science/stage/hour snapshots. Science-core functions remain AST-identical
to the previous consumer; only new schema/dependency identities and timing
binding paths differ. All approved numerical predicates and generation projection
rules remain unchanged. Tests compare each stage assignment/mapping/lock and the
hour's boundary values with the frozen scientific oracle.

Each capture owns one Measurement with the same request and absolute stage index.
Its raw producer invokes the pinned timed apply body once. It records any apply
exception, then attempts native-channel capture and durable raw ingress before
propagating that exception. Failed apply raw contains apply_error and cannot enter
science. Timing's known binding/terminal and completion pins are checked after
the owned call returns; four immutable byte/identity views are fixed and checked
through postsolve, science and close. Rehashing cannot adopt a changed file.

Timing persistence and its local fresh inspection occur between optimize and raw
capture. Thus interruption or raw-capture failure can leave a timing terminal
without raw. This is unknown witness state, not a completed stage. A raw write,
receipt or outcome failure likewise leaves timing evidence without science or
capture completion. No retry or native reexecution is allowed.

The science consumer requires timing binding/terminal pins from the live capture,
checks timing request/index and chain after raw receipt/outcome exist, and binds
both pins into its intent and terminal. The stage reader checks 21 exact files,
the capture/science reference equality, timing intervals and all full views.
Capture complete binds timing, raw and ingress terminal. Old readers reject the
new topology/schema. Disk readers still return conditional evidence and cannot
recover a live successful return after a publication error.

Hour commits bind timing pins and independently reconstructed native duration.
Full replay checks the complete canonical stage sequence, entry locks, unique
request/index pairs and each interval before computing timing-vector SHA and
native_total_ns. Hour projection and terminal bind both the scientific stage
vector and timing vector/total. Native totals are sums of complete elapsed
intervals, each computed inside its own clock domain; no timestamp subtraction
across clock domains occurs. No whole-worker wall/non-solver value is inferred.
native_intervals_complete=true is conditional on complete replay. Coverage,
observer separation, component budget, native authentication, resources and
formal flags remain false.

Compared with the previous owned-hour content caps, each stage adds four 2048-byte
metadata files and one directory. For S stages there are 22*S+3 files and 5*S+3
directories including root. At S=232 the controlled content cap is 7,975,424,000
bytes, 5,107 files and 1,163 directories. These reject caps and counts exclude
native scratch/logs, external data, filesystem allocation, temporary memory,
other phase journals, worker/controller/parent artifacts and full Job costs.

Tests use installed DirectSolver.solve plus the pinned timed apply body, a
synthetic native model and injected deterministic clock. A three-stage hour has
exactly three optimize calls, three complete 73 ns intervals and 219 ns total;
these values are test fixtures, not measured native performance. Failure cases
cover timing intent/completion/terminal before/after writes, optimize exception,
timing-before-raw interruption, raw write/receipt/outcome, science timing drift,
live pin mismatch, close, raw/capture terminal and hour commit/terminal failures.
No actual Gurobi or 232-stage native run occurs.

This successor integrates exact native-call intervals into the scientific hour
chain. Full phase instrumentation, worker lifecycle wall, independent observer,
whole-Job quiescence, all-hour source/carry integration, conditional storage
grammar, actual reuse DAG/manifest, full LB/UB and official resource review remain
open. No 2440-second non-solver budget or new native execution permission follows.
