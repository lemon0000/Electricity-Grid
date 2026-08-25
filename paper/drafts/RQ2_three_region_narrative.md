# RQ2 Three-Region Paper Narrative

> Status note (2026-08-25): this document records the completed 70-cell
> predecessor and its negative result. The v6 public-marginal successor uses
> `normalized minimum flexibility underprovisioning`, not interconnection
> capacity X; preserves E0 grid-infeasibility mass separately; conditions
> contract-risk transport on finite-grid blocks; and requires one common
> coupling for region compatibility. No v6 formal result exists yet.

## 1. Research Question and Scientific Value

Data centers may contract network-contingent curtailment and hourly
carbon-free-energy shifting as separate services even though both rely on the
same deferrable workload. The relevant planning question is therefore not
whether double commitment is always harmful, but under which combinations of
network stress, CFE scarcity and recovery capability it becomes binding.

The paper tests whether the frozen benchmark spans three proposed operating
regions:

1. **No-conflict region**: separate accounting and a shared physical envelope
   produce equivalent commitments and delivery.
2. **Double-commitment-risk region**: separate accounting understates required
   flexibility or increases out-of-sample service loss.
3. **Common-insufficiency region**: both formulations fail because aggregate
   CFE scarcity or recovery limits dominate the accounting distinction.

The intended contribution was identification of these regions and their
boundaries, rather than the isolated inequality
`c_grid + c_green <= D_flex`. The completed benchmark did not identify that
boundary: it occupied almost entirely the common-insufficiency region.

## 2. Research Design and Causal Logic

The correct formulation uses one chronological envelope for network and CFE
calls. B6 gives each service a separate copy of the same envelope during
planning. Both planned capacities are then frozen and replayed against the
same holdout chronology using the correct shared physical envelope.

Hourly CFE calls are derived from RTS-GMLC renewable availability and system
load. The data-center allocation is a transparent proportional-system-mix
benchmark. Google power traces determine only a training-quantile network
stress indicator. The two sources are sampled as independent marginals and
are not represented as synchronized observations.

Recovery remains inside the hourly CFE boundary. Recovery power is limited by
the smaller of business recovery headroom and clean-attribution surplus above
the hourly target. This prevents deferred energy from being moved into an
unaccounted recovery tail.

## 3. Methodology and Statistical Inference

The phase diagram varies:

- hourly CFE target;
- training-derived network activation threshold;
- business recovery headroom;
- flexibility budget;
- random window seed;
- POI;
- network-need definition.

The primary surface uses Bus 8 and the minimum-curtailment network definition.
Separate registered subsets assess seed, budget, POI and network-definition
robustness. Training and holdout windows are disjoint by construction.

The analysis reports complete cell-level outcomes. Random seeds measure
sampling robustness rather than independent populations, so no IID confidence
interval or population p-value is claimed.

## 4. Result Interpretation and Extrapolation Boundaries

The registered 70-cell local benchmark did not recover a three-region
boundary. Sixty-nine cells were classified as common insufficiency, one cell
was directionally mixed, and no cell was classified as no conflict or
double-commitment risk.

Fifty cells made both training formulations provably infeasible. In another
19 cells, both policies produced equivalent positive holdout failure or
shortfall. The only mixed cell occurred at Bus 8, `alpha_hr=0.50`, q99 network
activation and 20 MW business recovery headroom. B6 committed 14.02 MW versus
12.00 MW for the correct formulation and reduced expected shortfall by
1.01 MWh while both policies failed all holdout leaves. This direction is
incompatible with the proposed double-commitment mechanism and must not be
presented as support for H2.

The network layer itself varied substantially: the selected-N-1 need was
118.66 MW at Bus 3, 36.80 MW at Bus 8 and zero at Buses 14 and 18 under both
registered network definitions. Nevertheless, this variation did not move any
cell into a no-conflict or double-commitment-risk region. The result is
consistent with CFE scarcity and recovery closure overwhelming the accounting
distinction, but the 50 training-infeasible cells have not been decomposed by
binding-constraint cause. This interpretation is descriptive rather than
causal.

Unresolved solver outcomes and directionally inconsistent metrics remain
separate diagnostic states. Cell frequencies are properties of the frozen
benchmark grid, not estimates of real-world event probabilities.

The CFE allocation does not establish procurement ownership, physical electron
tracing or network deliverability. Selected-N-1 DC results do not constitute
full-N1 or AC security certification.

## 5. Academic Writing and Narrative Structure

### Introduction

1. Motivate separate network and CFE contracts drawing on one workload.
2. Explain why unified-dispatch studies avoid double counting by construction
   but do not evaluate independently committed services.
3. State the boundary-identification question.
4. Present the shared chronological envelope, B6 counterfactual and fixed-policy
   holdout design.

### Results

1. Validate the network and CFE input construction.
2. Present the degenerate primary phase surface.
3. Decompose the 50 jointly infeasible and 19 equivalent-failure cells.
4. Report seed and budget sensitivity without claiming a boundary.
5. Report POI and network-definition invariance of the negative result.
6. Analyze the single mixed cell and retain all failure regions.

### Discussion

Distinguish structural conclusions from benchmark-specific boundaries. Discuss
contract coordination, recovery-aware qualification and why high CFE targets
can move both formulations into common insufficiency.

## 6. Review Risk and Failure-Mode Prediction

The largest review risks are:

1. synthetic recovery capability;
2. independent rather than joint network/CFE chronology;
3. proportional-system-mix CFE attribution;
4. selected-N-1 DC scope;
5. limited POI coverage;
6. possible dominance of the common-insufficiency region.

Items 1-4 limit external validity and cannot be removed by parameter tuning.
Items 5-6 can be addressed by the registered sensitivity analysis and honest
scope restrictions.

## 7. Improvement Pathway and Submission Decision

The current result is not sufficient for a TSG submission centered on
double-commitment risk. The registered map provides strong negative evidence
against broad H2 under the present benchmark, rather than a publishable
three-region boundary.

A future successor can become a credible TSG candidate only if it is motivated
independently of these outcomes and adds external information rather than
searching the existing parameter space for favorable cells:

- the phase map contains interpretable boundaries rather than one degenerate
  region;
- boundary directions survive the registered seed and network-definition
  checks;
- representative trajectories explain the mechanism;
- all negative and mixed cells are retained;
- claims remain at the derived-benchmark level.

The defensible present conclusion is that CFE scarcity overwhelms
contract-accounting differences under the frozen design. Further in-grid
parameter tuning would be outcome-driven and is prohibited. Progress now
requires external recovery/contract evidence, a separately motivated
alternative estimand, or reframing the paper around the common-insufficiency
boundary.
