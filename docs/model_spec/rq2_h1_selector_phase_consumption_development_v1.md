# H1 selector phase consumption development

Status: DRAFT_NONAUTHORITATIVE. This file describes the implemented pure preview
and the still-unimplemented live consumption boundary. No formal gate is opened.

## Implemented preview

`_planned_bootstrap` reproduces the existing hour-0 phase intent and outcome
`AppendTicket` objects using the full manifest lane roster and saved selector
record bytes. It preserves the existing three-event bootstrap branch reservation
(intent, outcome, future episode terminal). It returns immutable canonical
projection/after bytes, both complete holder record bytes, and both exact
prospective retention tuples. The raw records remain inside the intent; no
truncation or replacement by hashes is allowed. The function performs numerical
replay only and does not touch the owner, holder, external journal or a solver.

`_BootstrapPlan` is constructible data, not a completion or execution credential.
Its structural checks bind tickets, holder bytes, retained hashes and projection.
They do not authenticate the source, parent execution, external retention or
scientific acceptance. Numerical `actual_unresolved` remains visible when a
saved prefix is incomplete. Such a preview does not establish why that prefix
is absent and must not authorize a live transition.

`_observe_bootstrap` compares supplied exact prefixes against this plan:

| Externally retained heads | Holder rows | DB rows | Observation |
|---|---|---|---|
| 0 | 0 | 0 | planned_only |
| 1 | 0 | 0 | holder_retention_pending |
| 1 | 1 | 0 | phase_commit_pending |
| 1 | 1 | 1 | outcome_pending |
| 2 | 1 | 1 | holder_retention_pending |
| 2 | 2 | 1 | phase_commit_pending |
| 2 | 2 | 2 | bootstrap_rows_present |

Unknown suffixes, differing bytes and impossible write orders reject. Knowing a
future planned hash does not advance external retention. The observer does not
read live storage or recover any operation. Even `bootstrap_rows_present` is
not a verified controller terminal, a parent-authenticated paired commit, or an
episode terminal. Every authority/result/resource flag returned remains false.

Tests compare the preview with actual legacy holder and SQLite persistence using
fabricated solver reports and an explicit synthetic source seam. They inject
failure after external retention, before/after each holder file write, and
before/after each DB commit. Failed stores are read for evidence only, with no
retry. These tests do not exercise real native solvers or Windows Jobs.

## Required live successor integration

The consumer must hold exact original Parent guards (Actuals in canonical lane
order, then Rref) across source/record replay, handoff and final readback. It must
bind the original issued completions, obtain records by fresh timed/scientific
archive replay, and retain the common/roster guards while closing the genesis
handles and opening the same holder/phase roots. Existing header bytes and
external genesis heads must match. The empty-only CommonOwnerGenesis contract
is preserved; a public close/open gap is insufficient.

A separately retained controller journal must persist the complete takeover
intent and, inside each holder callback, `holder_head_prepared_1/2` before
acknowledging the prospective head. Whole-branch byte/count capacity must be
checked before closing the genesis. A retained callback event with no holder
file is pending. A prepared ticket without its DB row remains pending unless a
separately specified exact-tail recovery is invoked. Intent without outcome
cannot be retried. Outcome without the controller terminal requires explicit
metadata reconciliation, not another scientific transition.

Each direct lane requires a typed disposition: an exact live successful Actual
completion, or an internally recomputed business-unresolved-before-Actual
branch. Missing/failed started Actual work has no typed failure completion in
the current parent and must remain pending. Proof terminals and joint-B6
separate planning obligations remain in the complete group audit.

Live binding, handoff journal, typed failure completion, actual paired
consumption, hour-1+/192-hour coverage, full resource admission, successor seal,
fresh official review and specific new native authority remain open.
