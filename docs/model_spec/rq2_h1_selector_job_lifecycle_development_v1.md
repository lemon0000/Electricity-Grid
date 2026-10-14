# Selector owned Job lifecycle development

DRAFT_NONAUTHORITATIVE; root-only writes and independent R3 PRE_SEAL review.

`run_job` owns one generic `normal_task_child` context. It fixes argv, explicit
environment, role-selected TaskProcessBudget and HostResourceBudget, recomputes
the process/host identities and validates suspended-child initial headroom.
Only then does it call the trusted controller's before_release callback.
After callback identity/request/owner checks, it releases and waits exactly once.
It validates the exact live observation before the on_quiescent output-reader
callback: PID/creation/identity, exit0, natural child exit, whole-Job quiescence,
configured limits, error-free samples, exact success markers, finite elapsed,
positive bounded peaks and matching minimum commit/disk reserve observations.
The Job context closes before this output-reader callback. Callback or cleanup
failure yields no successful lifecycle return. No retry is performed internally.
An active process identity cannot reenter; durable attempt ownership remains the
enclosing controller's responsibility.

Closed primitive functions/classes and their methods are captured at module
import, including the lower-level Job/resource/store helpers. Preinstalled
acquire/release/wait/validator replacements are rejected before child acquisition;
the same identities are bookended throughout the invocation. This is drift
detection in a trusted Python process, not isolation against arbitrary Python
memory modification. Authority flags are immutable and retain exact all-false
scope checks in implementation identity and each runtime bookend.

Input callback arguments and output diagnostics are ordinary constructible data.
The inspection callback must return exactly `{schema, data}` with schema
`h1_selector_job_inspection_diagnostic_v1`. Strict finite canonical JSON encoding
is bounded to 1 MiB and decoded to detach callback-owned containers. Non-JSON,
cyclic and oversized values are rejected without a successful lifecycle return.
Schema and byte cap are checked against fixed literals in implementation identity
and runtime scope checks, including after the inspection callback returns.
They are not live completion credentials, selector result authentication or phase
consumption authority. A caller-supplied TaskProcessObservation cannot bypass the
owned acquisition/wait path. The private value validator by itself proves no
historical execution. Default QPC endpoints describe only this parent invocation;
they are not combined with child endpoints and prove no non-solver allowance.

The generic primitive's exceptional close path closes the Job and requests member
termination but does not confirm active count zero. Only a successful wait with
validated observation establishes quiescence for the subsequent callback.

The next selector controller must fix the worker argv, create immutable request,
launch and release records, freshly rebuild input and inspect all worker/science/
timing output, persist its own terminal and bind persistent phase consumption.
Actual must be blocked before release unless an exact live Rref parent completion
is freshly validated against the snapshot's Rref root/terminal/request/cap and
associated Job evidence. A scientific archive alone cannot authorize that release.
Both roles' real native execution requires a concrete admitted package and new
explicit authorization. This unit neither launches real native tests nor changes
formal/resource/selector integration gates.
