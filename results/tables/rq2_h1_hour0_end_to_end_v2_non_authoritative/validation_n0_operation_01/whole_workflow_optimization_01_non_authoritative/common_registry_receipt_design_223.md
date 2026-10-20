# Common registry integration: stable science and per-call execution

Status: DRAFT_NONAUTHORITATIVE / PRE_SEAL. Root is the sole writer.
This addendum supersedes only the receipt-placement requirement in design208;
the saved bytes of designs204/208 and evidence through222 remain unchanged.

GenesisBridge3 and HandoffBridge5 compare `validation_report_payload` bytes
across Common calls within a public method. Witness8/9 also binds their hash
as `scientific_payload_sha256`. A unique phase identifier or varying execution
counter in that report would reject scientifically identical calls.

`PreparedCommonInput.validation_report_payload` therefore carries the stable
scientific projection and fixed observation contract:

- `observation_schedule=common_body_entry_exit`;
- `per_call_physical_freshness=false`;
- `between_bookend_ABA_covered=false`;
- `fresh_at_return_only=false`;
- a fixed held-phase `reuse_edge` identifying static dependency reuse only.

`PreparedCommonInput.phase_execution_receipt: bytes` carries the canonical
per-call observation: unique phase identifier, original call ordinal, actual
project/check/cache-hit counts, segment/kernel receipts, source identities and
dynamic-root envelope. It is copied only after all five independent numerical
Roster scopes have retired, final checks and phase exit have completed.
Predecessor compatibility payloads remain explicit historical projections.

Witness execution receipts bind both `scientific_payload_sha256` and
`phase_execution_receipt_sha256`, the original session identity and call ordinal.
The private Bootstrap coordinator owns the original Common body; it accepts no
caller-supplied body. A completed-but-uncommitted row weakly binds the exact
session, ticket, intermediate result and final phase bytes. A source-defined
finalizer reconstructs the typed result and requests its execution receipt
after phase exit. Detached hashes or a valid-looking result do not authorize
that transition.

`_finish_common` claims and commits exactly one such row. Any failure in the
pre-bookend, result validation, either receipt comparison, commit or post-bookend
clears/poisons pending state in `finally`; no reusable numerical proof becomes
available. Phase-exit failure poisons both Bootstrap and Witness and publishes
no completed Common row. The original body exception remains primary over all
cleanup, poison and reporting exceptions.

Definition provenance remains separate from loader activation and per-read
authorization. Genesis and Handoff have separate ordered source factories and
footer slots. Real integration must independently bind project imports and
their reachable functions/defaults/closures; weak foreign identity observations
alone do not establish their initial source authenticity. Stdlib-generated
dataclass methods need an explicit bounded contract. Source2's two public
factory wrappers are outside the Source9/10 `_prepare` route; preserving them
does not establish this route's authenticity.

The preserved chain07 body and postcheck04, Core6 evidence181, Roster scope202,
typed graph207 and helper snapshots221 are reused within their named scopes.
They do not establish numerical Roster/Common execution, full optimized chain
acceptance, a full-workflow performance budget, resource admission or formal
execution authority. All those gates remain false/open as previously recorded.
