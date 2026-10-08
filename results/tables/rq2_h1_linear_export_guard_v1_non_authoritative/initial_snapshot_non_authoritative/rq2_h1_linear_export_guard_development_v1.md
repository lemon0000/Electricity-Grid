# H1 complete linear export correspondence development v1

Status: DRAFT_NONAUTHORITATIVE. This successor predicate adds complete linear
row and variable-bound/domain checks to the earlier objective-only guard. It
does not change that guard, any saved report schema, or the sealed src closure.

`experiments/h1_linear_export_guard_development_v1.py::check` accepts a canonical
Pyomo model and an already updated native model plus complete forward/reverse
variable and constraint maps. It never creates a solver or calls optimize.
The future caller must pin the exact adapter, own the model, update it before
checking, and prevent subsequent mutation before optimize. These lifecycle
requirements are not established by this predicate.

The complete native inventories must have consecutive, unique indices and exact
counts. Map values and expression handles are matched using reciprocal native
`sameAs`, allowing distinct Python wrappers for the same native object; canonical
Pyomo objects still require exact object identity. Names alone are insufficient.
Both map directions must be bijections. A test double that lies about native
identity is outside this protocol; native API authentication remains required.

Checks include all variables, fixed-variable bounds, binary/integer/continuous
domains, finite bounds below native infinity, minimization, one objective,
objective constant and coefficients, and every active linear constraint's
coefficients, sense and RHS. Native quadratic, SOS, general, scenario and PWL
objective structures are rejected, as are lazy rows and nonzero row constants.
No auxiliary variables, skipped rows, duplicate expression terms, ranges or
unmapped handles are accepted. Bounds missing canonically require the pinned
native infinity value of ±1e100.

Coefficients and constants are compared as exact rational values of binary64
numbers. Constraint normalization requires exact `native_rhs = bound - constant`.
Even a mathematically expected floating-point rounding discrepancy is unresolved;
there is no tolerance expansion or coefficient repair. Ranged constraints would
need a separately proved auxiliary-variable protocol. The installed pinned
Pyomo direct adapter uses `addRange` for that branch; this predicate refuses it.

Tests use synthetic native handles, including equal native identities with
different Python wrappers. They test matrix/RHS/domain/bound corruption, hidden
structure, bijections and rounding rejection. A zero-solver check builds the
pinned RTS origin (980 rows) and the existing synthetic future carry plus all
locks (1272 rows): neither contains range rows, and normalized RHS values fit
binary64 exactly. The future carry is a shape counterexample, not a reachable or
feasible schedule. These two models do not establish all-hour producer coverage.

This predicate is not connected to the worker. Actual native export coverage,
native execution authentication, resource admission, formal execution readiness
and formal result remain false. A successful call proves correspondence of the
supplied views only, not feasibility, optimality, stable ownership, raw capture,
or permission to execute. Failures must retain available raw evidence and stop
as unresolved in the eventual producer; this module performs no file writes.
