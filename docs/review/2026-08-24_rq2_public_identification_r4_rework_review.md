# RQ2 public identification v3 R4 re-review packet

## Decision requested

Return exactly one verdict: `PASS`, `REWORK`, or `ESCALATE`.

This is the single allowed re-review after the first `REWORK`. Review is
read-only. A second failure of the same acceptance item must be `ESCALATE`,
not another repair loop.

## Scope

The reviewed successor configures, but does not execute, the formal chain:

1. 1071 RTS-GMLC 24-hour grid-need blocks;
2. training-only correct/B6 minimum-capacity planning;
3. causal fixed-policy holdout replay over each eligible 530 x 34 Cartesian
   product;
4. sharp transport bounds, optimizing couplings, identification classes, and
   OAT ambiguity-reduction.

All formal execution and user-authorization gates remain false. No long
solver run is authorized by this review.

## First-review findings and repairs

1. Arbitrary zero shortfall weight: training now uses `kappa_access=1.0`;
   minimum-capacity planning still fixes shortfall to zero.
2. Perfect-foresight holdout MIP: replaced by
   `causal_myopic_grid_first_then_CFE_with_current_state_only`; each action
   uses current state only.
3. Weak checkpoint identity: pair checkpoints bind capacities, policy
   checkpoint hash, solver versions, and all policy/model modules.
4. OAT missing levels: any missing registered level makes that dimension
   `unresolved`; no selective subrange calculation.
5. Weak package contract: exact downstream member/schema/inventory checks and
   policy/status/pair logical consistency checks now fail closed.
6. Recovery debt omitted from classification: peak and terminal debt
   differences now enter identified and compatible-region logic.
7. Missing grid-runner R4 gate: grid, replay, and identification runners all
   require independent review, formal readiness, and user authorization.

Additional corrections:

- CFE service request is clipped to paired available business flexibility;
  physical grid need remains untruncated.
- R1/R3 compatibility requires every difference interval to contain zero.
- R2 compatibility requires every difference to be possibly nonnegative and
  at least one to be possibly strictly positive.
- The v3 preregistration outer manifest exactly covers every frozen input and
  source-package manifest.

## Acceptance criteria

- No future information is used in holdout actions.
- Mandatory grid calls cannot be hidden by clipping or CFE shortfall.
- Terminal recovery, event, energy, ramp, capacity, and debt constraints fail
  closed.
- Training infeasibility, solver unresolved, and holdout failure remain
  distinct.
- Sharp bounds require a complete resolved Cartesian product.
- Checkpoints cannot mix capacities, policies, implementations, solvers, or
  source packages.
- R1/R2/R3 and compatible-region labels match the registered nine metrics.
- Preregistration and manifests are live and complete.
- Formal long-run gates remain closed.

## Primary files

- `src/scenarios/rq2_public_replay.py`
- `src/evaluation/rq2_identification_bounds.py`
- `experiments/run_rq2_public_pairwise_replay.py`
- `experiments/run_rq2_public_identification_grid.py`
- `experiments/run_rts_gmlc_public_grid_need_dispatch.py`
- `configs/rq2_public_pairwise_replay_v1.yaml`
- `configs/rq2_public_identification_grid_v1.yaml`
- `configs/rts_gmlc_public_grid_need_dispatch_v1.yaml`
- `configs/rq2_public_data_ambiguity_set_v3.yaml`
- `configs/rq2_public_data_robust_identification_preregistration_v3.yaml`
- `docs/plan/RQ2_公开数据鲁棒识别路线图_v3.md`

## Verification evidence

- Focused behavior and runner regression: `33 passed`.
- Frozen dependency and runner regression: `58 passed`.
- Broad successor regression: `94 passed`.
- Scoped Python Ruff: passed after an equivalent cleanup of the frozen
  flexibility-envelope dependency.
- Production read-only preflights:
  - grid: 1071 blocks, 541 training, 530 holdout, all formal gates false;
  - replay: 15 cells and 34/34 workload blocks, grid package gate false;
  - identification: pairwise package gate false.
- No formal grid dispatch, Cartesian replay, or identification run was
  started.

## Required review references

- `agent.md` sections 4, 7, 8, 9, 10, and 14
- `docs/model_spec/formulation.md` public-marginal transport section
- `docs/model_spec/blocker_register.md` RQ2 public successor gate
- tests frozen by preregistration v3

## Final verdict

`ESCALATE`

The reviewer confirmed the causal replay, failure separation, Cartesian
sharpness, classification, and closed formal gates, but found that the first
review's provenance acceptance item remains incomplete:

- grid checkpoints do not bind the actual grid-need/SCUC modules and solver
  versions used to produce them;
- publication can therefore attach current module provenance to an older
  checkpoint;
- identification validates the pairwise package contents but does not verify
  the complete upstream config/module/solver/source/checkpoint identity
  promised by the preregistration.

Under `agent.md` section 7, this repeated acceptance-item failure cannot enter
another ordinary repair loop. Formal execution remains prohibited pending
`sol_modeler` or explicit user-directed successor work.
