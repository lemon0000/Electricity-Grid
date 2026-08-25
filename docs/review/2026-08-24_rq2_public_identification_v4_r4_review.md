# RQ2 public identification v4 provenance successor R4 review

## Decision requested

Return one verdict: `PASS`, `REWORK`, or `ESCALATE`.

Review is read-only. Do not start a formal grid, Cartesian replay, or
identification run.

## Scope

The v4 successor preserves the v3 scientific protocol and addresses the prior
R4 `ESCALATE`: an old grid checkpoint could previously be reused without
binding the actual grid-need/SCUC modules or solver versions, and downstream
identification did not verify complete upstream provenance.

## Acceptance criteria

1. A grid checkpoint is reusable only under the same config, runner, direct
   model modules, solver package versions, source package, and RTS source.
2. A pairwise policy/pair checkpoint is reusable only under the same config,
   policy/replay modules, solver package versions, workload package, and exact
   upstream grid package provenance.
3. Grid and pairwise publication include exact per-checkpoint SHA-256
   inventories and a canonical `provenance.json`.
4. Pairwise and identification verify exact upstream package member sets,
   package hashes, config SHA, frozen contract, implementation hashes,
   software versions, source/input manifests, provenance hash, and checkpoint
   inventory.
5. Rehashing a tampered package must not permit provenance relabeling.
6. v1/v3 predecessor files remain available; v4 is a successor rather than an
   in-place rewrite.
7. Preregistration v4 and its outer manifest exactly cover every frozen input.
8. All formal readiness, independent-review, and user-authorization gates
   remain false.

## Primary artifacts

- `src/evaluation/rq2_provenance.py`
- `configs/rq2_public_pipeline_provenance_contract_v1.yaml`
- `experiments/run_rts_gmlc_public_grid_need_dispatch_v2.py`
- `experiments/run_rq2_public_pairwise_replay_v2.py`
- `experiments/run_rq2_public_identification_grid_v2.py`
- `configs/rts_gmlc_public_grid_need_dispatch_v2.yaml`
- `configs/rq2_public_pairwise_replay_v2.yaml`
- `configs/rq2_public_identification_grid_v2.yaml`
- `configs/rq2_public_data_robust_identification_preregistration_v4.yaml`
- `configs/rq2_public_data_robust_identification_preregistration_v4.SHA256SUMS.json`
- `docs/plan/RQ2_公开数据鲁棒识别路线图_v4.md`
- `docs/model_spec/formulation.md`

## Required tests

- `tests/test_rq2_provenance.py`
- `tests/test_rts_gmlc_public_grid_need_dispatch_v2_runner.py`
- `tests/test_rq2_public_pairwise_replay_v2_runner.py`
- `tests/test_rq2_public_identification_grid_v2_runner.py`
- `tests/test_rq2_public_data_preregistration_v4.py`

The tests explicitly cover live contract verification, implementation drift,
grid and pairwise checkpoint identity drift, exact package members, upstream
config relabeling after package rehash, atomic publication, unresolved
fail-closed behavior, formal gates, and live preregistration hashes.

## Verification evidence

- v4 focused regression: `26 passed`.
- v3 plus v4 relevant broad regression: `120 passed`.
- scoped Ruff: passed.
- `git diff --check`: passed.
- preregistration v4: 40 frozen paths, no inner hash errors, exact outer member
  set, no outer hash errors.
- production read-only preflight:
  - grid: 1071 blocks; contract verified; all formal gates false;
  - pairwise: 15 cells and 34/34 workload blocks; contract verified; upstream
    grid readiness false;
  - identification: contract verified; pairwise readiness false.
- no formal solver or Cartesian run was started.

## Scientific boundary

This review concerns execution provenance only. It does not authorize formal
compute and does not upgrade the benchmark to empirical contract probability,
full-N1, AC security, or engineering certification.

## Final verdict

`ESCALATE`

The reviewer confirmed stage-base binding for config, implementation, solver,
source, and upstream package identity, but found checkpoint inventory
completeness unproved. The verifier checks that the inventory copy and its
canonical hash agree; it does not derive and compare the required key set from
the grid block IDs or pairwise policy/eligible Cartesian outcome tables.
Consequently, an attacker can remove checkpoint entries and consistently
recompute `provenance.json`, summary, and package manifest without rejection.

The failing acceptance item is the same provenance item escalated from v3.
Under `agent.md` section 7, formal execution remains prohibited and another
ordinary repair loop is not allowed. A user-directed `sol_modeler` successor
must require:

- grid inventory keys equal all registered block IDs;
- pairwise inventory keys equal all policy checkpoints plus every eligible
  Cartesian pair checkpoint;
- every digest is a lowercase hexadecimal SHA-256;
- a negative test that deletes an inventory entry and recomputes every outer
  hash, yet is still rejected.
