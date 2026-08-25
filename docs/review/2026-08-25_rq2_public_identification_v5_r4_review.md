# RQ2 public identification v5 R4 review

## Decision

Return exactly one verdict: `PASS`, `REWORK`, or `ESCALATE`.

This is a new user-authorized `sol_modeler` successor after the v4
checkpoint-inventory completeness escalation. Review is read-only. Do not
start formal computation.

## Scope

The scientific protocol is unchanged from v4. The v5 change is limited to
proving that checkpoint inventories are complete, not merely self-consistent.

## Acceptance criteria

1. Grid expected keys are mechanically derived from every registered block ID.
2. Pairwise expected keys are mechanically derived from every parameter-cell
   policy checkpoint plus every power-by-workload checkpoint for each cell
   whose correct and B6 policies are feasible.
3. Ineligible cells cannot contribute pair checkpoints.
4. Inventory keys must exactly equal the expected set; missing, additional,
   duplicate, or renamed entries fail closed.
5. Every digest must match lowercase hexadecimal `[0-9a-f]{64}`.
6. Inventory file, provenance copy, canonical inventory hash, and summary
   field must agree.
7. Removing an inventory entry and recomputing provenance, summary, and package
   manifest must still be rejected before transport calculation.
8. v4 predecessor artifacts remain unchanged and live.
9. User authorization is recorded, but `independent_R4_review_passed` and
   `formal_execution_ready` remain false pending this review.

## Primary artifacts

- `src/evaluation/rq2_provenance_v2.py`
- `configs/rq2_public_pipeline_provenance_contract_v2.yaml`
- `experiments/run_rts_gmlc_public_grid_need_dispatch_v3.py`
- `experiments/run_rq2_public_pairwise_replay_v3.py`
- `experiments/run_rq2_public_identification_grid_v3.py`
- `configs/rts_gmlc_public_grid_need_dispatch_v3.yaml`
- `configs/rq2_public_pairwise_replay_v3.yaml`
- `configs/rq2_public_identification_grid_v3.yaml`
- `docs/model_spec/rq2_checkpoint_inventory_contract_v5.md`
- `docs/plan/RQ2_公开数据鲁棒识别路线图_v5.md`
- `configs/rq2_public_data_robust_identification_preregistration_v5.yaml`
- `configs/rq2_public_data_robust_identification_preregistration_v5.SHA256SUMS.json`

## Required tests

- `tests/test_rq2_provenance_v2.py`
- `tests/test_rts_gmlc_public_grid_need_dispatch_v3_runner.py`
- `tests/test_rq2_public_pairwise_replay_v3_runner.py`
- `tests/test_rq2_public_identification_grid_v3_runner.py`
- `tests/test_rq2_public_data_preregistration_v5.py`

The identification runner test contains the required adversarial case: one
Cartesian pair checkpoint is removed, then the inventory hash,
`provenance.json`, summary, and package manifest are recomputed. The package
must still fail with `checkpoint inventory keys drifted`.

## Verification

- v5 focused regression: `35 passed`.
- v3-v5 relevant broad regression: `152 passed`.
- scoped Ruff: passed.
- `git diff --check`: passed.
- preregistration: 41 frozen paths, exact outer member set, no inner or outer
  hash drift.
- production validate-only preflights verify the v2 provenance contract and
  report 1071 grid blocks, 15 parameter cells, user authorization true,
  independent review false, and formal readiness false.

## Boundaries

`PASS` closes the software provenance gate only. It does not itself certify
results, full-N1 security, AC feasibility, empirical contract probabilities,
or engineering capacity. Formal stages must still run sequentially and publish
verified upstream packages before downstream readiness can be activated.

## Final verdict

`PASS`

The focused rework replaced ordinary JSON parsing with duplicate-key rejection
for every security-sensitive manifest, summary, provenance, inventory, and
checkpoint read in the v3 chain. Direct and end-to-end adversarial tests prove
that a duplicated inventory key cannot hide an invalid digest even after all
outer hashes are recomputed.

The reviewed evidence was:

- focused regression: `37 passed`;
- related broad regression: `154 passed`;
- scoped Ruff and `git diff --check`: passed;
- v5 preregistration: 41 outer members and 40 frozen inputs, no hash drift;
- three production preflights: passed with formal and independent-review gates
  still closed.

This verdict authorizes mechanical activation of the reviewed v3 software
chain under the user's separate explicit authorization. It does not certify
any result produced by that chain.
