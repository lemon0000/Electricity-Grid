# H1 selector execution configuration binding

2026-10-11. DRAFT_NONAUTHORITATIVE. Root is the sole writer.

`SelectorRunConfiguration` declares the common Rref/A solver specification,
the two existing selector specifications, exact replay limits, complete sorted
generation UID inventory and static network hash. Its stage orders are exactly
Rref `(grid_request, l1_normal_deviation, generation:<sorted UID>...)` and
Actual `(l1_normal_deviation, generation:<sorted UID>...)`. The closed selector
configuration checker applies the existing tolerance, gap, lock, threads,
stage-count, call-count and total-solver-seconds limits to the full chains.
The actual raw-capture adapter's pure `validate_spec` additionally requires its
pinned package, single thread, fixed seed/gap/tolerances, positive declared time
and disabled tee before any producer directory can be created. It is the
`rq2_gurobi_declared_normal` adapter, whose TimeLimit is explicit and positive.
The Actual specification is arm independent; the validator uses the existing
valid `joint_correct_shared` lane for that configuration-only check. This is
not a declared lane roster or a claim of all-arm execution coverage.

Each chain has its own typed TaskProcessBudget and explicit positive finite
non-solver allowance in seconds (int or float; bool rejected). Decimal Fraction
arithmetic checks `stages * time_limit + allowance <= job elapsed`. This is a
declared allocation, not a measured or proven non-solver bound. This is a future
selector-chain Job declaration using TaskProcessBudget's 3600-second development
ceiling. The separate N controller's 300-second ceiling remains unchanged and
is not the executor of these selector chains. The full chain must also fit the
conservative replay record envelope `stages * max_record_bytes <= max_total_bytes`.
This does not bound native capsules, filesystem allocation, SQLite, scratch,
RAM, replay execution time, all lanes, all hours or a complete study.

BootstrapDeclaration accepts this configuration optionally. If present, exact
N RunConfiguration is required, with identical network hash and complete
generation UID sequence. Validation occurs before journal creation, on live
owner checks and therefore around retained attempts/claims. The configuration
and derived stage orders enter the study binding, local/global headers and
claim proposals; foreign episode replay uses the same study binding. The live
implementation identity includes this module and the closed raw bridge and
fresh inspector. Nested mutation, changed parameters on reopen and mismatched
N declarations are rejected. After retained claim, the existing static network
load additionally validates actual network hash and complete UID order against
the selector declaration. No source is loaded to construct this configuration.

None preserves N-only development behavior. A bound declaration never permits
post-N consumption. A future paired entry must require the registry binding,
this configuration and a concrete Phase Manifest, then hold the original owner
operation and persistent tickets. Bootstrap seq6 and selector producer calls
remain unimplemented. Returned dictionaries and constructible dataclasses are
not capabilities. No new defaults select scientific thresholds or resources.

The existing unclosed bootstrap draft is extended in place; its previous code
and specification bytes are retained in this unit's non-authoritative evidence
directory. Implementation/header identities change; old roots are not migrated
or adopted. All 994 pinned predecessor files remain unchanged.

Tests cover full-stage and N inventory equality; strict inherited gates;
independent Job boundaries including exact decimal arithmetic; nested mutation;
pre-attempt and retention-callback rejection; changed-config reopen; foreign
replay; post-claim static inventory checking; and fake-numerical N0 protocol
compatibility. The latter isolates journal binding and does not establish native
acceptance. No native solver or research Job is required for this unit.

Open: concrete Phase Manifest, lane policies and capacities, producer archive
and aggregate resource bounds, live owner/holder/controller attachment, common
Rref-to-A release, paired commit, complete192/all-family execution, resource
admission, successor seal, fresh official review and specific native authority.
All formal/resource/native gates remain false. PRE_SEAL review is required;
this draft is not an official verdict or a whole-bootstrap closure.
