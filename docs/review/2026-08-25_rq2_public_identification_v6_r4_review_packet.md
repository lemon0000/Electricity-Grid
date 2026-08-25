# RQ2 Public Identification v6 R4 Review Packet

## Review Decision

Return exactly one leading decision: `PASS`, `REWORK`, or `ESCALATE`.
Review is read-only. A `PASS` approves the development-machine implementation
and executor handoff only; it does not authorize the cross-solver pilot or any
formal grid, pairwise, or identification run.

## Original Request

The development machine must implement the approved RQ2 improvement path while
leaving large-scale solver validation to the execution machine. Existing 202
HiGHS checkpoints must be preserved and must not be mixed with the Gurobi
successor.

## 1. Research Question And Scientific Value

The primary estimand is
`correct_minimum_flexibility - B6_minimum_flexibility`, reported as normalized
minimum-flexibility underprovisioning. The current public-data model has no
explicit interconnection-capacity decision or validated mapping to `X`;
therefore no `X`-overestimation claim is permitted.

Authority:

- `agent.md`
- `docs/plan/RQ2_公开数据鲁棒识别路线图_v6.md`
- `configs/rq2_public_data_robust_identification_preregistration_v6.yaml`

## 2. Research Design And Causal Logic

The implementation must preserve the unpaired RTS-GMLC and Alibaba empirical
marginals. It must not construct an empirical cross-source joint distribution.
Training freezes correct/B6 policies; holdout performs fixed-policy Cartesian
replay. Representative policies must pass the complete finite-grid training
support before entering holdout.

`exogenous_grid_infeasibility` (E0) requires both the original corrective LP and
the rebuilt `D_DC=0` endpoint to be solver-proven infeasible. Timeout, missing
incumbent, ambiguous termination, or failed solution audit remain unresolved.
E0 mass is unconditional, E0 rows remain in the Cartesian output with null
contract metrics, and contract-risk transport conditions only on finite-grid
power blocks.

## 3. Methodology And Statistical Inference

Review these implementation surfaces:

- `src/solvers/rq2_solver_adapter.py`
- `src/grid/rts_gmlc_grid_need_successor.py`
- `src/grid/rts_gmlc_scuc_solver_successor.py`
- `src/models/temporal_flexibility_capacity_successor.py`
- `src/scenarios/rq2_public_replay_successor.py`
- `src/evaluation/rq2_joint_identification.py`
- `experiments/run_rts_gmlc_public_grid_need_dispatch_v4.py`
- `experiments/run_rq2_public_pairwise_replay_v4.py`
- `experiments/run_rq2_public_identification_grid_v4.py`

Required invariants:

1. Resolved solver records include actual model scale, incumbent, bound, gap,
   and original-unit residual.
2. Partial-region compatibility uses one common transport coupling for all
   metric conditions.
3. The fixed-seed bootstrap resamples the two empirical marginals independently
   and is not labeled population identification.
4. No unresolved state is converted to infeasibility or a finite grid need.

## 4. Result Interpretation And Extrapolation

Permitted future claims are limited to E0 empirical block mass and
finite-grid-conditional sharp bounds for the public benchmark. The successor
does not certify empirical outage probabilities, real contract failure
probabilities, Alibaba absolute MW, PPA/REC delivery, full N-1, AC security,
engineering capacity, or `X`.

No formal v6 numerical result exists. The four-block solver pilot has not run.

## 5. Academic Writing And Narrative

The v6 route orders the argument as separated contracts, shared temporal
resource, B6 double commitment, unknown cross-source dependence, E0 separation,
sharp bounds, common-coupling regions, and sampling variability. Negative,
partially identified, E0, and training-coverage outcomes remain reportable.

## 6. Review Risks And Failure Modes

- The Gurobi package, license, Pyomo interface, and real model behavior are not
  available on the development machine.
- The frozen pilot must compare HiGHS and Gurobi twice on ordinary, congested,
  generator-E0, and branch-E0 blocks. Runtime cannot override a scientific or
  certificate mismatch.
- The historical v5 manifest still records old `formulation.md` bytes that are
  unavailable in the worktree or reachable Git history. v5 artifacts were not
  rewritten. The 202 checkpoints are now explicitly nonformal diagnostic
  evidence, cannot be resumed formally, and are not v6 executor dependencies.

## 7. Improvement And Execution Path

Development-machine completion target:

1. Freeze and verify the executor bundle.
2. Complete independent R4 review.
3. Keep pilot and formal activation closed.

Execution-machine sequence after handoff:

`verify -> preflight -> pilot -> return pilot package -> review -> activation ->
grid -> pairwise -> identification`.

## Code And Execution Controls

Execution files:

- `configs/rq2_public_executor_handoff_v1.yaml`
- `configs/rq2_public_solver_pilot_v1.yaml`
- `configs/rq2_public_successor_activation_v1.yaml`
- `environments/rq2_executor_v1.yml`
- `experiments/preflight_rq2_public_executor_v1.py`
- `experiments/run_rq2_public_solver_pilot_v1.py`
- `experiments/activate_rq2_public_successor_v1.py`
- `scripts/rq2_public_executor.py`

Frozen identities:

```text
preregistration:
ef25deabfcd51fbd667e48dcddcfbe4b19a2115c6d4bc40b0fc556b5c1f332f2

preregistration outer manifest:
07bb735df3cc5ad547c7d4741c5f69929b39a37df9b65c3c2ae004e74b08cdcf

provenance contract:
9a890f6cebf6a2b87b6cee97ec9b3a5074bb40892cee917c98fe58644ff178f9

executor bundle manifest:
49613e3e400a31ee4888490c5939c4985efaaed3f13325baa1c4bbc28b319f04
```

The bundle contains the exact union of the 39-file v6 outer manifest, that
outer manifest, and every runner/module named by the provenance contract: 53
files total. Static verification also validates all members of the three nested
input packages. The mutable post-pilot activation record is deliberately
outside the immutable bundle; activation verifies its own authorities and the
hash-bound preflight and pilot receipts.

## Focused Rework

The first independent review returned `REWORK`. This packet now includes the
single permitted focused repair:

1. `_run_block` injects the registered model tolerance into `_normal_baseline`;
   a no-solver regression reproduces the former call path.
2. Pilot eligibility now compares baseline and hourly termination/status,
   incumbent, lower/upper bounds, absolute/relative gap, residuals, primary and
   zero-DC model scale, finite grid need, and E0 classification.
3. Activation now requires a hash-bound successful runtime preflight receipt,
   a pilot result bound to the frozen pilot config SHA, the exact handoff SHA,
   and the exact SHA of each stage template.
4. The unrecoverable v5 formulation dependency is classified explicitly.
   Historical checkpoints remain preserved but are excluded from the v6 outer
   manifest and executor bundle.
5. After the re-review escalated a missing baseline relative gap, a read-only
   `sol_modeler` prescribed a successor-local audit. The shared historical SCUC
   module remains unchanged; the successor now records incumbent-relative gap,
   requires it for accepted baselines, and compares it across all pilot runs.
6. Preflight records the immutable bundle SHA. Pilot re-verifies that bundle,
   records the same SHA and its own frozen runner SHA, and activation requires
   both receipts to agree.
7. A later read-only review found the old v3 formal config still executable.
   Its three execution gates are now false, predecessor checkpoint reuse is
   forbidden, and a no-solver regression proves rejection before grid-data
   loading or solver work.

## Verification Evidence

Observed on development host `GQPD263XH9`:

```text
pytest relevant v6/successor/v3/pilot/activation/SCUC regression: 66 passed
scoped Ruff: All checks passed
py_compile: passed
git diff --check: passed
executor static verify:
  bundle files: 53
  bundle manifest SHA:
    49613e3e400a31ee4888490c5939c4985efaaed3f13325baa1c4bbc28b319f04
  nested package members: workload 4, power blocks 5, RTS-GMLC upstream 25
  formal_execution_started: false
  hostname_allowed: false
  environment_authorized: false
  gurobipy observed: null
pilot validate-only:
  bundle manifest SHA:
    49613e3e400a31ee4888490c5939c4985efaaed3f13325baa1c4bbc28b319f04
  implementation SHA:
    094f93751c92d95f379ee34f7a236bb7a86a8cb3d81f359d96c5590bcb0cf200
  formal_grid_execution_started: false
```

The legacy v5 test module still reports two expected failures because it
requires every v5 frozen path to remain live in the current worktree. The
underlying drifts are the unavailable old `formulation.md` bytes and the
deliberately retired v3 formal config. v6 records both transitions and does not
use the v5 files or checkpoints as formal execution dependencies.

## Required Reviewer Checks

1. Verify the scientific semantics of E0, the estimand, complete-training
   coverage, common-coupling compatibility, and bootstrap interpretation.
2. Verify solver certificate acceptance does not promote timeout, missing
   incumbent, or ambiguous status.
3. Verify development-host and environment gates prevent pilot/formal execution.
4. Verify checkpoint/output isolation and stage-order activation.
5. Verify the 53-file bundle set and nested input verification are adequate.
6. Verify the v5 shared-path drift is fully isolated from v6 execution and no
   v5 checkpoint can be formally resumed.
7. Confirm all activation fields may remain false until executor pilot evidence
   returns.
