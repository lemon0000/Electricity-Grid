# RQ2 Temporal H2 Successor Preregistration

## 1. Research Question and Scientific Value

This successor tests whether the out-of-sample service disadvantage of B6
double commitment survives a chronological envelope, network-derived
`grid_need`, alternative training sources, two network-demand definitions and
training-only threshold choices.

The evidence remains mechanism evidence. The Google trace supplies a stress
shape, not outage timing; the Alibaba trace is an independent workload
marginal; recovery parameters are synthetic. No empirical outage probability,
contract capability, engineering feasibility or security certification will
be claimed.

The parent v3 mechanism result at threshold `1.0` is already observed and
negative for cross-source H2. It is retained only as a descriptive boundary
replication. It is excluded from confirmatory claims.

## 2. Research Design and Causal Logic

The Google trace is split at 50%. Only the first 372 hours determine the
normalization peak and q80/q90/q95/q99 thresholds. Temporal H2 holdout outcomes
do not determine the threshold grid.

Each job freezes one threshold and one seed. Within a job:

- manual/generated/reduced differ only in training source;
- all three arms execute against one SHA-bound holdout draw;
- correct and B6 policies are frozen before holdout network derivation;
- both `minimum_curtailment` and `overload_sensitivity` are reported;
- no failed, unresolved or negative-result cell may be omitted.

The core window is fixed at 8 hours and the synthetic recovery tail at 4 hours.
Changing horizon is excluded because it also changes exposure duration and
would confound the source comparison. A later horizon study requires a
separate exposure-normalized preregistration.

## 3. Methodology and Statistical Inference

Frozen formal scale:

- `n_train=200`, `n_holdout=60`;
- seeds `20260822`, `20260823`, `20260824`;
- threshold grid q80/q90/q95/q99;
- primary threshold q90;
- descriptive prior boundary `1.0`;
- reduction target 50, with sensitivity targets 25 and 100;
- three training-source arms and two network definitions;
- HiGHS, `beta=0.9`, `lambda_risk=0.1`.

The 17-job matrix contains 12 confirmatory threshold-seed jobs, 3 descriptive
boundary jobs and 2 additional reduction-resolution jobs. Seeds assess
algorithmic window-sampling robustness; they are not independent populations.
Overlapping windows and synthetic event mapping preclude IID confidence
intervals or population-level p-values. Results are reported as complete
cell-level effect magnitudes and deterministic preregistered logical tests.

## 4. Result Interpretation and Extrapolation Boundaries

The primary H2 claim is supported only if all six q90 cells
(`3 seeds x 2 network methods`) are evaluable and cross-source positive.

Broad threshold generalization requires all 24 confirmatory cells
(`4 thresholds x 3 seeds x 2 network methods`) to be evaluable and positive.
Any missing, unresolved or non-positive cell rejects that broad claim.

Reduction-resolution robustness requires all six cells at q90,
seed `20260822`, targets 25/50/100 and both network methods to be positive.

Threshold `1.0` results are descriptive regardless of their sign. Negative and
mixed regions remain part of the reported result.

## 5. Academic Writing and Narrative Structure

The paper may state that the successor evaluates sensitivity to a
training-derived stress threshold. It may not describe the threshold as an
outage model or the resulting frequency as an empirical failure probability.

`gate_passed=true` means only that the computation, solver interpretation and
artifacts passed correctness gates. It does not establish H2, security or
engineering validity.

## 6. Review Risk and Failure Modes

The main residual risks are:

- threshold activation has no observed outage semantics;
- Google and Alibaba traces are not synchronized;
- windows have zero carry-in and no cross-window linking;
- recovery headroom and envelope limits are synthetic;
- selected N-1 DC analysis is not full N-1 or AC security;
- repeated overlapping windows are not independent samples.

These are structural evidence limits. More solver time does not remove them.

## 7. Improvement and Execution Path

Frozen artifacts:

- `configs/rq2_h2_temporal_successor_preregistration_v1.yaml`
- `configs/rq2_h2_temporal_successor_formal_v1.yaml`
- `configs/rq2_h2_temporal_successor_batch_v1.yaml`
- `configs/rq2_h2_temporal_successor_preregistration_v1.SHA256SUMS.json`

Before execution:

1. The static validator and relevant tests must pass.
2. An independent R4 `sol_reviewer` must return `PASS`.
3. The user must explicitly authorize formal execution.
4. A new immutable `run-*` tag must point to the reviewed commit.

This preregistration task does not modify `configs/experiment.yaml`, create a
tag, invoke the formal runner or call a solver.

## Code and Validation Contract

The batch driver may override only the frozen numeric threshold, seed and
reduction target fields used by this matrix. It rewrites
`output.directory` into an isolated job directory and carries temporal
robustness, arm results and holdout/draw hashes into `batch_manifest.json`.
The execution entrypoint recursively copies every job's effective config,
summary, arm table, leaf table and nested SHA manifest into `batch_results`;
the upload manifest recursively hashes those files.

The validator recomputes training-only thresholds, all frozen file hashes and
the exact 17-job matrix without importing an experiment runner. Any drift fails
closed.

## Concrete Recommendation

Run no successor job until the R4 review and a separate execution
authorization are recorded. After execution, analyze the complete 17-job
matrix before changing any threshold, seed, horizon, recovery or reduction
parameter.
