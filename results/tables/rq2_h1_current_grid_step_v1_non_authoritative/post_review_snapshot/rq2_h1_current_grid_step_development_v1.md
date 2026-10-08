# H1 physical candidate kernel

R3 DRAFT_NONAUTHORITATIVE. This is detached development mathematics, with no
persistent owner or accepted state. It ports the fixed-power DC equations and
1e-6 assignment gate from `current_grid_step.py` to the rolling H1 information
contract. It does not construct old fixed-plan information/carry types.

The preserved equations cover generator bounds, prescribed DC load and nodal
balance, AC/DC flows, branch outage zero flow, response about current N output,
committable own-history ramp, planned startup/shutdown allowances, forced-trip
down-ramp exemption, and explicitly reported generator repair return caps.
Realtime reserve is not registered in this physical kernel. N continues to
carry its separate reserve and dwell obligations. No tolerance is relaxed.

A complete N boundary identity binds all UIDs, commitment, generation, age,
network, completed hour and evidence role. Each candidate physical transition
binds both normal boundaries to the frame's source-network identity and
requires its incoming normal identity to equal the frame's normal-before and
records normal-after. Current decision identity changes across hours. The
physical lane retains its own generation, disclosure and predecessor identity;
it never updates N. Reference lane has no arm field value; actual lane uses only
one of the four declared public arm names. Cross-lane use is rejected.

Relative hour h is 0..191. The reused pure disclosure state machine internally
uses boundary hour 0 and current report h+1. Real source timestamps are absent.
Origin requires explicit incoming disclosure. Available units inherit the
approved N initial generation and unavailable units start at zero, with static
bounds checked. No user-chosen replacement origin is provided.

`_frame` is a private synthetic or already-validated-packet seam. It does not
verify normal optimality, stage locks, native evidence or publication. The
development model/auditor also accepts detached candidate carry: their exact
types are not authentication credentials. Output authority flags remain false:
detached_consumer_authenticated, normal_selection_authenticated,
common_publication_verified, reference_or_actual_ready, formal_result and
security_certified. A successful witness only satisfies this fixed-power
linear model's assignment gate. It does not select g or prove infeasibility.

Expected input identities require exact built-in lowercase SHA256 strings.
Tests compare the entire mathematical build-body AST and exact-residual AST,
complete variable domains/bounds/fixed values, every linear
constraint's coefficients/bounds and objective with the old model, plus audit
residuals and carry numerical values. Private parity fixtures model only
algebra, not reachable H1 origins. Separate H1 synthetic chains test declared
origin, own-history ramp, trip/continuation/repair, planned shutdown, N boundary
splices, neutral clocks, lanes and audit failure. These use no solver.

The next operational owner must rebuild N and lane state from its own
persistent history and external pins, consume fresh current information within
the same owned operation, then reverify before returning. It cannot accept this
detached carry as authenticated history. Reference needs its numerical selector
and same-key conflict/publication gate before g can reach business policies;
actual advancement needs published reference, policy action and atomic paired
business/physical commit. This module supplies none of those permissions.
