# Deliverability of AI Data Center Workload Flexibility for Grid Response and Carbon-Free Energy Matching

Updated: 2026-10-20. This introduction describes the current design and available evidence; Section 5 gives a dated progress snapshot.

## 1 Abstract

Network-contingent service and hourly carbon-free-energy (CFE) matching may call on the same deferrable and recoverable computing workload. This project asks how stricter hourly-CFE targets change the minimum workload flexibility required under mandatory network response, whether joint chronology creates an extra requirement or portfolio relief, and what signed capacity bias results from separate accounting. This RQ2 question is the primary paper's focus. Multistage F/X interconnection, grid-expansion delays, and the planning effects of annual versus hourly CFE remain project extensions.

The approved finite-v2 development contract evaluates all applicable service requests during a 168-hour enrollment interval and timely completion of deferred work born within that interval, followed by up to 24 additional hours when needed to determine enrollment outcomes. The total simulated span is at most 192 hours. Each independent episode starts from an explicit mechanism initial state; recovery debt, event budgets, and grid states carry across days. Curtailment q and recovery r share the bidirectional capacity q+r≤D. Recovery is also limited by business headroom, deadlines, and applicable same-hour CFE-compatible surplus. Follow-up requests remain in the physical accounts without expanding the enrollment scoring set; missing necessary follow-up remains unresolved or right-censored.

The study compares network-only, CFE-only, joint-correct, and joint-B6. Its target is the minimum normalized bidirectional capacity that admits one causal workload policy over the complete declared training support. The four objects \(D_N,D_C,D_B,D_J\) retain the signed decomposition \(I_{joint}=D_J-\max(D_N,D_C)=I_{sep}+A_{B6}\), with \(I_{sep}=D_B-\max(D_N,D_C)\) and \(A_{B6}=D_J-D_B\). B6 plans with separate accounts that each use the available workload and capacity; fixed-policy actual execution uses one shared physical envelope. Evidence is organized as valid lower bounds and complete-service upper bounds for the same contract. Missing finite certificates remain unknown, and cross-arm ordering or contrast signs are not presumed.

The current design combines 19 workload contracts with 100 hourly-CFE targets, from 1% to 100% in one-percentage-point steps, for 1,900 cells. It is an exploratory successor developed after observing earlier diagnostics. Its scientific parameters are approved for development, while the execution candidate remains DRAFT_NONAUTHORITATIVE. Available evidence includes synthetic planning mechanisms, scoped public selected-N-1 DC benchmarks, and component development checks. The complete continuous four-arm experiment, capacity frontier, and formal holdout results have not been published.

**Keywords:** AI data center; hourly CFE; joint service; finite enrollment; bidirectional flexibility capacity; recovery debt; causal policy

## 2 Related Work

### 2.1 Separate Institutional Objects and the Contract-Overlap Hypothesis

FERC 195 FERC ¶ 61,216 and the PJM precedent it cites show that large loads willing and able to limit withdrawal may receive network-side service up to a specified MW contract level enforced through control or protection measures. The EnergyTag Granular Certificate Matching Standard and Google's 24/7 CFE methodology support ex-post hourly CFE accounting and matching within specified temporal, geographic, and metering boundaries. These evidence chains separately support network-contingent service arrangements and hourly-CFE accounting and matching. Direct evidence linking both obligations to the same contract, meter, and internal workload resource remains necessary. The paper therefore states their potential mapping to one temporal workload envelope as a falsifiable contract-overlap hypothesis.

### 2.2 Flexible Interconnection and Grid-Capacity Planning

Data-center interconnection research covers candidate siting, capacity allocation, and interconnection expansion. Kim, Dong, and Xie [1] incorporate firm, pause, and shift envelopes into planner-initiated siting with hourly and single-contingency screening, showing that flexibility changes candidate-point evaluation. Chen and Zheng [2] compare workload deferral, temporal shifting, and cross-node migration in an investment-and-hourly-operation model of interconnection expansion. Li, Fang, and Chen [3] combine robust firm capacity, CVaR flexible capacity, and locational attributes in static transmission-capacity allocation, while Mytton et al. [6] explain the practical grid-capacity and governance constraints surrounding large data-center connections. These studies establish the flexible-interconnection and grid-capacity-planning baseline. The primary paper focuses on the common workload resource behind separate obligations; multistage F/X release, project lead times, and delays at a fixed point of interconnection remain project extensions.

### 2.3 Demand Response, Carbon-Aware Computing, and Workload Envelopes

Wierman et al. [13] review the technical opportunities and operating constraints of data-center demand response, and Liu et al. [14] study workload control and cost under utility peak-demand response. GreenSlot [15] and Parasol and GreenSwitch [16] use batch scheduling and systems coordination to exploit on-site renewable energy. Qureshi et al. [17] route workloads across locations to use electricity-price differences, while Liu et al. [18] use geographical load balancing to follow renewable supply. Radovanović et al. [19] form hourly virtual capacity curves from regional carbon-intensity signals, establishing an operational carbon-aware-computing pathway.

For resource limits, Kwag and Kim [20] show why demand response requires more than a static MW ceiling. Crozier and Liska [7] review flexibility from protection, precooling, CPU/GPU control, and job scheduling, and Williams et al. [5] provide GPU-cluster and inference-workload evidence on fast response and sustained curtailment. These studies support the technical boundaries of workload adjustability, power, duration, and recovery. The paper organizes these established mechanisms into a shared finite-enrollment envelope with on-demand follow-up, carrying recovery debt, event states, and bidirectional power capacity across days. A B6 counterfactual tests the consequences of separate planning.

### 2.4 Network-Renewable Coordination and Deliverability

Wan and Li [4] incorporate data-center spatiotemporal load flexibility into security-constrained unit commitment, using a unified dispatch variable to relieve congestion and improve renewable utilization. Wan, Fang, and Li [26], posted as arXiv:2511.08759 v1 in 2025 and updated as v2 in 2026, analyze congestion, renewable curtailment, and cost through one spatial-redispatch variable. Ma et al. [27] induce spatiotemporal shifting through endogenous locational prices; Lin and Chien [28] allocate multisite load-decoupling resources for carbon benefits; and Zhang et al. [29] characterize how transmission constraints reduce the availability of flexible resources. Together, these works establish the direct benchmark of network-renewable coordination under unified physical dispatch.

Fan and Zhao [30] jointly optimize workload distribution and regulation-capacity commitment, using chance constraints and queue-VaR constraints for instantaneous and cumulative deliverability. Khanal et al. [31] model firm, flexible, and interruptible tiers in capacity expansion for PJM and Korea, including depth, duration, ramping, minimum recovery, annual energy, and hourly limits. Capacity commitment, deliverability, event shape, and recovery therefore have clear priority boundaries. The paper focuses on the complete-temporal deliverability frontier as hourly-CFE targets increase under fixed mandatory network response, using a signed four-arm decomposition to separate single-service bottlenecks, joint interaction, and B6 capacity bias.

### 2.5 Multistage Transmission Expansion and Robust Planning

Han, Kim, and Lee [8] use a scenario tree for long-term multistage transmission expansion under demand uncertainty. Webster [9] develops a wide-area multistage stochastic transmission-expansion algorithm, and Akhavizadegan, Wang, and McCalley [10] study scenario selection for iterative stochastic expansion. Jabr [11] treats robust transmission expansion with uncertain renewable generation and load, while Li et al. [12] add multiple uncertainties and active load. These studies provide the foundations for scenario trees, nonanticipativity, robustness, and expansion decisions. The project extension applies these foundations to fixed-point data-center ramp-up, F/X release, and project delays; multistage or robust optimization is not positioned as a contribution of the primary paper.

### 2.6 Annual Matching, Hourly CFE, and Clean Computing

de Chalendar and Benson [21] show why annual 100% renewable-energy claims do not fully represent consumption timing or power-system decarbonization. Miller, Novan, and Jenn [22] quantify differences between hourly accounting and annual or monthly aggregation. Riepin and Brown [23] compare the cost and system effects of annual and 24/7 CFE procurement, and Riepin, Jenkins, Swezey, and Brown [24] examine how 24/7 matching affects the deployment of advanced clean technologies. Riepin, Brown, and Zavala [25] then jointly optimize spatiotemporal computing-load shifts to align computing activity with clean electricity across time and location. These studies form the direct accounting, procurement, and clean-computing baseline. The present paper asks whether a separate network-contingent obligation and hourly-CFE obligation draw on the same workload envelope.

### 2.7 Joint Deliverability, Attribution, and Robustness

The scientific object is the workload-flexibility requirement frontier as hourly-CFE targets increase under a fixed mandatory network response. The four arms first identify the limiting single service, then estimate the signed joint interaction, separate-envelope interaction, and B6 capacity bias. RTS-GMLC and Alibaba retain separate provenance, clocks, and training/holdout splits; their combinations are declared mechanism-benchmark couplings. Existing transport tools can support pairing robustness, while the continuous contract still requires explicit risk events, window weights, and censoring rules before conditional sharp bounds can be computed over a stated transport polytope. Multimetric statements require one common coupling witness. Negative findings, exogenous grid infeasibility (E0), service shortfall, and unresolved outcomes remain distinct.

![Figure 1. Literature landscape and project positioning](../figures/project_literature_landscape_en.svg)

**Figure 1. Literature landscape and project positioning**. A structured positioning based on the 31 academic works reviewed in this paper, not an exhaustive bibliometric result; the three institutional sources establish only that the two objects exist separately and do not demonstrate real contract overlap.

## 3 Intended Paper Contributions and Project Extensions

### 3.1 A Finite-Enrollment Joint Workload-Flexibility Frontier

The primary paper studies the minimum bidirectional flexibility capacity across CFE targets under fixed common-reference rules, mandatory network response, and the complete temporal envelope. The primary factorial combines three deferrable-workload fractions and three recovery-headroom levels, with ten additional temporal OAT contracts: 19 contracts, each evaluated on the same 100 CFE targets. Complete training support remains the scientific quantifier; computation may use proof-referenced whole-cell analytic exclusions and valid task reuse.

Each arm's capacity object requires one causal workload policy within that cell to serve all declared training support. A valid lower bound requires a legitimate relaxation of the same complete contract. A feasible upper bound requires a named fixed policy with complete-support service witnesses and applicable actual-grid acceptance. B6 upper bounds certify its separate planning accounts; shared actual execution is evaluated separately. A failed fixed-policy probe establishes no successful witness for that policy and capacity, rather than infeasibility for every policy.

### 3.2 Signed Four-Arm Attribution and Fixed-Policy Consequences

The decomposition distinguishes the limiting single service, joint temporal interaction, and B6 accounting bias. Contrasts, intervals, and signs are reported only when supported by the four capacity objects. Joint-correct is an additive benchmark of disjoint service commitments, with common request g+c. B6 checks two planning accounts, while actual execution has one workload availability, capacity D, debt state, and event budget. This estimand does not represent the minimum resource across every physical co-service policy.

Before holdout, capacity and a named policy are frozen from complete training-feasibility evidence. Execution uses only revealed current inputs, and workload actions are committed together with Actual grid states. Hard-grid, CFE, and joint-service outcomes remain separate; missing sources, uncovered recovery deadlines, and solver uncertainty remain explicit unknowns. Public-marginal transport and common-coupling witnesses are supporting robustness tools whose risk definitions and interfaces must match the continuous contract.

### 3.3 Design Versions and the Broader Project

The earlier confirmatory design of 36 factorial and ten temporal OAT cells, totaling 46 cells, and the older 70-cell diagnostic retain their own frozen contracts and result identities. The current 1,900-cell finite-v2 design is an exploratory successor formed after observing those diagnostics. Its mapping, temporal contract, and reference mechanism differ, so new computations are reported under the new contract.

The broader project studies nonanticipative multistage F/X release, expansion initiation, and commissioning as data-center demand and project progress are revealed. It also compares annual and hourly CFE effects on capacity, construction, and flexibility allocation. F denotes firm capacity within the stated security scope; X denotes capacity callable under contractual conditions. Existing B0-B5 planning and fixed-policy execution foundations support this extension.

## 4 Research Objectives and Main Contents

### 4.1 Primary Target and Contract Parameters

The target is causal minimum bidirectional capacity for the complete finite-enrollment contract, together with auditable bounds. Enrollment E=168h uses a 24h start stride; enrolled work is due at birth+24h, with at most 24h follow-up. Enrollment and actual follow-up share one nonrolling accounting period of at most 192h, retaining budgets across days. Initial states, deferrable fractions, recovery efficiency, and headroom are registered mechanism assumptions.

The primary factorial uses f∈{0.05,0.20,0.50} and ρ∈{0,0.10,0.30}; ten OAT contracts vary recovery efficiency, maximum duration, event count, energy budget, and debt cap. Power is normalized by an assumed D_DC=250MW, with D∈[0,1]. The 250MW value is a simulation scale. Raw workload outside the mapping domain is retained and marked mapping unresolved.

### 4.2 Causal Grid and Workload Execution

H1 denotes a grid mechanism using the current hour's revealed inputs at each step. States are separated into common normal N, common reference Rref, and per-arm Actual A chains. The normal baseline excludes the current outage. The reference produces a common network request under current normal commitment and revealed outages or repairs, independently of the CFE target, workload parameters, D, or response-adjusted arm states. Actual chains accept the fixed power resulting from each arm's workload action. Each chain retains its own carry.

The hourly order is revealed input → N update → common Rref request → CFE mapping → causal workload action → Actual acceptance → paired commit. Actual curtailment creates one recovery debt; unserved requests retain separate shortfall records. Recovery follows known due times and then birth order, subject to capacity, headroom, and applicable clean surplus. Follow-up work remains in the physical accounts, while the scoring cohort remains fixed to enrollment births.

### 4.3 Computational Design and Evaluation

1. Preserve separate-source continuous windows within each chain, seed, and split, together with complete-support inventories;
2. Organize four-arm capacity lower bounds, named-policy upper bounds, and analytic exclusions for 19 workload contracts and 100 CFE targets;
3. Bind reused tasks to complete input and initial-state identities, rather than a shared source-hour timestamp alone;
4. Freeze training capacity and policy before holdout, retaining success, failure, unknown outcomes, and deadline coverage;
5. Evaluate pairing robustness and common-coupling witnesses after risk events, window weights, and the coupling set are registered;
6. Audit raw reports, residuals, gaps, state continuity, paired commits, and independent replay after close and reopen.

The current inventory contains 523×28=14,644 training pairs and 512×28=14,336 holdout pairs per cell. These are mechanism-combination identities; overlapping windows are not independent samples. Across 1,900 cells there are 27,823,600 training cell-pair identities. Necessary solver calls depend on analytic exclusions and valid reuse DAGs and must be established by the concrete task package and full resource budget.

![Figure 2. AI data center flexibility deliverability workflow](../figures/project_workflow_en.svg)

**Figure 2. AI data center flexibility deliverability workflow.** Data, four-arm models, and evaluation dependencies under the finite-enrollment contract. The figure shows the complete research design; Section 5 distinguishes accepted synthetic development cases from continuous execution still awaiting acceptance.

![Figure 3. AI data center grid response and CFE matching framework](../figures/project_network_en.svg)

**Figure 3. AI data center grid response and CFE matching framework.** The fixed POI, hourly CFE matching, and shared workload envelope support the primary mechanism study. Staged ramp-up and grid expansion belong to the broader project blueprint.

## 5 Project Feasibility and Current Status

### 5.1 Existing Models and Named Benchmarks

The project implements RTS-24 DC-OPF and joint security checks, deterministic expansion, F/X service balance, B0-B5 baselines, nonanticipativity, synthetic fixed-policy holdout, and duration, event, energy, and recovery-debt envelopes. The frozen deterministic case has access shortfalls of B0=327,600MWh and B1=B2=109,200MWh. B4 improves on B3 by 128,800MWh in the synthetic scenario tree, with deterioration on some holdout paths also retained. These findings support their respective mechanism scopes; formal empirical VMA has not been published.

RTS-GMLC has named six-hour and full 24-hour selected-N-1 DC SCUC/fixed-commitment ED benchmarks and a six-candidate POI comparison. The full-day benchmark audits 12 registered states per hour and has published result files and a manifest. Direct AC and zero-data-center recovery diagnostics still lack complete feasibility witnesses within the official limits, including h15/h21; security_certified remains false.

### 5.2 Public Data and Mechanism Identity

RTS-GMLC grid data, Alibaba workloads, and Google power data retain separate provenance, versions, and clocks. Public marginals support declared mechanism windows and couplings. Absolute workload MW, actual recoverability, deadlines, recovery headroom, and same-clock outage evidence remain insufficient. The 250MW scale and workload parameters retain their mechanism_assumption identity rather than defining an observed joint distribution or empirical service probability.

The approved origin/registry successor covers the six historical outage-source left-boundary gaps. Saved checks report 1,035 unique entries, source_input_unresolved=0, and obligations_removed=0. Source coverage does not establish acceptance of a complete 192h producer execution. Terminal states, on-demand follow-up, and unknown outcomes still require evidence from the continuous chain.

### 5.3 Development Snapshot on 2026-10-20

Finite-v2 scientific parameters were approved for development on 2026-09-30. The concrete configuration remains DRAFT_NONAUTHORITATIVE, with complete_preregistration, formal_execution_ready, and formal_run_authority all false. The normal model, source adapters, persistent state, selectors, raw-report retention, and scoped PRE_SEAL checks have development evidence.

The complete chain_07 synthetic first-hour case and independent-process saved-record replay have finished. Three independent N0 runs proceed through common, shared Rref, and three Actual lanes to paired commit. Heads, projections, and carries agree after close and reopen; independent postcheck supplement 04 closes the case's replay, cleanup, and timing evidence. The original chain took 259,910.325 seconds of wall time, followed by 401.168 seconds for independent-process replay and reference-field checks. These timings describe the legacy synthetic validation path and do not establish a native or production execution budget.

A cross-hour successor has completed a two-hour, three-lane successful prefix and full replay after close and reopen. The batch historical-replay version commits two outcomes covering six paired lane-hours in 509.516 seconds of outer wall time. Workload projections and final scientific states agree with the earlier case at the same scale, and the names and SHA hashes of 212 saved files remain unchanged.

A three-hour outage-continuation, repair, and single-lane stopping case has also finished: three outcomes cover seven paired lane-hours in 1,314.969 seconds of outer wall time. It checks positive network requests, outage continuation, and the generation cap in the first repair hour. A CFE Actual timeout with a feasible incumbent remains actual_unresolved: neither workload nor Actual state advances on that lane, while the others continue. An external pre-close checkpoint supports same-process read-only reopen after all owners close; 444 saved file names and SHA hashes agree. Missing next-hour input occurs during enrollment, leaving a pending attempt and an unterminated episode. This case does not establish formal follow-up censoring metrics.

These cases use synthetic sources or fabricated solver outputs, with zero real native calls, and remain DRAFT/PRE_SEAL development evidence. The full 168h enrollment through up to 24h of on-demand follow-up, phase boundaries, episode termination, and honest right-censoring still require connected acceptance. Work now focuses on valid reuse of dynamic prefix replay and a complete resource budget. The two- and three-hour cases differ in coverage and failure paths, so their wall-time ratio does not estimate optimization gains or 192h costs. Every new experiment requires review of the full task DAG, call multipliers, evidence reuse, stage time, memory, storage, heartbeats, and stop conditions. The 192h value is the maximum simulated span; the production wall-clock budget remains unestablished.

### 5.4 Exits Required Before Formal Execution

| Order | Required object | Current status |
|---|---|---|
| 1 | Complete hour-0, independent saved replay, cleanup, and timing | chain_07 synthetic case and independent supplement 04 complete |
| 2 | Cross-hour producer/phase coverage up to 192h | Two- and three-hour synthetic cases complete; full 168h plus up to 24h pending |
| 3 | Concrete task/reuse DAG, same-contract LB/UB, and resource admission | Incomplete |
| 4 | Successor seal and fresh independent official review | Current execution package not yet through review |
| 5 | Separate package-specific run authorization and formal-result acceptance | Not started |

The old 70-cell diagnostic and V8 nonformal two-block pilot retain their historical evidence. An earlier formal grid attempt produced only nine of 1,071 historical checkpoints; no complete grid package was published. The current continuous contract has no published formal capacity frontier or holdout results.

## 6 Expected Outputs and Research Boundaries

### 6.1 Expected Outputs

1. Four-arm complete-service capacity frontiers, valid LB/UB evidence, and unresolved regions for finite enrollment;
2. The signed decomposition I_joint=I_sep+A_B6 where supported by capacity evidence;
3. Holdout network, CFE, and joint-service consequences of named training capacities and fixed causal policies;
4. Raw reports, paired commits, and independent replay linking workload debt, outage states, and grid carry;
5. Applicable coupling robustness and later multistage F/X, expansion, and annual/hourly-CFE extensions.

### 6.2 Research Boundaries

The primary estimands are workload bidirectional capacities normalized by D_DC and their signed interactions. Interpreting them as conditional interconnection capacity X requires an explicit, validated mapping. Additive commitments, reference dispatch, and recovery policies retain named mechanism identities. Timely completion of the finite enrollment cohort establishes only the stated finite contract, rather than indefinite sustainability.

Holdout weights and transport intervals are conditional on the declared benchmark support and coupling set. Population probabilities, real contract incidence, and causal effects require further evidence. Selected-N-1 DC results apply to their named computational scope; engineering security additionally requires complete security sets, AC, equipment, and control evidence. CFE denotes accounting and matching of attributable clean electricity within the same hour and specified region.

Timeouts, local solver failures, missing incumbents, and incomplete certificates retain the relevant unresolved status. Missing necessary follow-up is reported as unknown or censored, while observed violations remain recorded. Capacity intervals, contrast signs, and service conclusions require complete supporting evidence.

## 7 References

[1] Kim, D., Dong, L. and Xie, L. (2026). “Flexibility-aware framework for efficient planner-initiated siting of data center.” Nature Communications. https://doi.org/10.1038/s41467-026-72324-9

[2] Chen, Y. and Zheng, X. (2026). “To Defer or To Shift? The Role of AI Data Center Flexibility on Grid Interconnection.” ACM Sustainability Week. https://doi.org/10.1145/3765611.3815593; https://arxiv.org/abs/2604.05376

[3] Li, S., Fang, B. and Chen, C. (2026). “Risk-Aware Allocation of Transmission Capacity for AI Data Centers.” arXiv preprint arXiv:2604.08854. https://arxiv.org/abs/2604.08854

[4] Wan, H. and Li, X. (2026). “Data Center Spatio-Temporal Load Flexibility in Security-Constrained Unit Commitment for Enhanced Grid Efficiency and Reliability.” arXiv preprint arXiv:2605.18517. https://arxiv.org/abs/2605.18517

[5] Williams, C., Colangelo, P., Coskun, A. et al. (2026). “Power-Flexible AI Data Centers: A New Paradigm for Grid-Responsive Compute.” arXiv preprint arXiv:2606.25098. https://arxiv.org/abs/2606.25098

[6] Mytton, D., Ashtine, M., Wheeler, S. and Wallom, D. (2023). “Stretched grid? Managing data center energy demand and grid capacity.” Oxford Open Energy. https://doi.org/10.1093/ooenergy/oiad014

[7] Crozier, C. and Liska, M. (2025). “The Potential of Data Center Energy Demand To Provide Grid Flexibility.” Current Sustainable/Renewable Energy Reports. https://doi.org/10.1007/s40518-025-00258-9

[8] Han, S., Kim, H.-J. and Lee, D. (2020). “A Long-Term Evaluation on Transmission Line Expansion Planning with Multistage Stochastic Programming.” Energies. https://doi.org/10.3390/en13081899

[9] Webster, M. (2022). “A Multistage Stochastic Transmission Expansion Algorithm for Wide-Area Planning under Uncertainty.” Technical report. https://doi.org/10.2172/1737833

[10] Akhavizadegan, F., Wang, L. and McCalley, J. (2020). “Scenario Selection for Iterative Stochastic Transmission Expansion Planning.” Energies. https://doi.org/10.3390/en13051203

[11] Jabr, R. A. (2013). “Robust Transmission Network Expansion Planning With Uncertain Renewable Generation and Loads.” IEEE Transactions on Power Systems. https://doi.org/10.1109/TPWRS.2013.2267058

[12] Li, W., Zhao, L., Bo, Y. et al. (2021). “Robust transmission expansion planning model considering multiple uncertainties and active load.” Global Energy Interconnection. https://doi.org/10.1016/j.gloei.2021.11.009

[13] Wierman, A., Liu, Z., Liu, I. and Mohsenian-Rad, H. (2014). “Opportunities and Challenges for Data Center Demand Response.” 2014 International Green Computing Conference, pp. 1–10. https://doi.org/10.1109/IGCC.2014.7039172

[14] Liu, Z., Wierman, A., Chen, Y. et al. (2013). “Data center demand response.” ACM SIGMETRICS. https://doi.org/10.1145/2465529.2465740

[15] Goiri, I., Le, K., Haque, M. E. et al. (2011). “GreenSlot.” SC Conference. https://doi.org/10.1145/2063384.2063411

[16] Goiri, I., Katsak, W., Le, K. et al. (2013). “Parasol and GreenSwitch.” ASPLOS. https://doi.org/10.1145/2451116.2451123

[17] Qureshi, A., Weber, R., Balakrishnan, H. et al. (2009). “Cutting the electric bill for internet-scale systems.” ACM SIGCOMM. https://doi.org/10.1145/1592568.1592584

[18] Liu, Z., Lin, M., Wierman, A. et al. (2011). “Geographical load balancing with renewables.” ACM SIGMETRICS Performance Evaluation Review. https://doi.org/10.1145/2160803.2160862

[19] Radovanović, A., Koningstein, R., Schneider, I. et al. (2023). “Carbon-Aware Computing for Datacenters.” IEEE Transactions on Power Systems. https://doi.org/10.1109/TPWRS.2022.3173250; https://arxiv.org/abs/2106.11750

[20] Kwag, H.-G. and Kim, J.-O. (2012). “Optimal combined scheduling of generation and demand response with demand resource constraints.” Applied Energy. https://doi.org/10.1016/j.apenergy.2011.12.075

[21] de Chalendar, J. A. and Benson, S. M. (2019). “Why 100% Renewable Energy Is Not Enough.” Joule. https://doi.org/10.1016/j.joule.2019.05.002

[22] Miller, G. J., Novan, K. and Jenn, A. (2022). “Hourly accounting of carbon emissions from electricity consumption.” Environmental Research Letters. https://doi.org/10.1088/1748-9326/ac6147

[23] Riepin, I. and Brown, T. (2024). “On the means, costs, and system-level impacts of 24/7 carbon-free energy procurement.” Energy Strategy Reviews. https://doi.org/10.1016/j.esr.2024.101488; https://arxiv.org/abs/2403.07876

[24] Riepin, I., Jenkins, J. D., Swezey, D. and Brown, T. (2025). “24/7 carbon-free electricity matching accelerates adoption of advanced clean energy technologies.” Joule. https://doi.org/10.1016/j.joule.2024.101808

[25] Riepin, I., Brown, T. and Zavala, V. M. (2025). “Spatio-temporal load shifting for truly clean computing.” Advances in Applied Energy, 17, 100202. https://doi.org/10.1016/j.adapen.2024.100202; https://arxiv.org/abs/2405.00036

[26] Wan, H., Fang, L. and Li, X. (2025/2026). “Grid Operational Benefit Analysis of Data Center Spatial Flexibility: Congestion Relief, Renewable Energy Curtailment Reduction, and Cost Saving.” arXiv preprint arXiv:2511.08759, v1 2025-11-11, v2 2026-03-27. https://arxiv.org/abs/2511.08759

[27] Ma, D., Ye, Y., Wu, Y. et al. (2025). “Bi-Level Optimisation Model for Harvesting Spatial-Temporal Load Shifting Flexibility of Data Centres Using Endogenously Formed Locational Price Signal.” IET Smart Grid, 8(1), e70020. https://doi.org/10.1049/stg2.70020

[28] Lin, L. and Chien, A. A. (2025). “Distribution and Management of Datacenter Load Decoupling.” arXiv preprint arXiv:2511.08936. https://arxiv.org/abs/2511.08936

[29] Zhang, W., Fang, L., Zhao, F. et al. (2025). “Operational risk assessment of power system considering transmission limitation on flexible resources and its application to SCUC.” AIP Advances, 15, 115016. https://doi.org/10.1063/5.0302342

[30] Fan, Y. and Zhao, J. (2026). “Harnessing Flexible Spatial and Temporal Data Center Workloads for Grid Regulation Services.” arXiv preprint arXiv:2602.01508. https://arxiv.org/html/2602.01508

[31] Khanal, S., Roh, G., Yao, B. et al. (2026). “Shift or curtail? How much data-center flexibility is worth depends on the host power grid.” arXiv preprint arXiv:2608.19622. https://arxiv.org/html/2608.19622

## 8 Institutional and Standards Sources

- Federal Energy Regulatory Commission (2026). 195 FERC ¶ 61,216; Docket EL26-69-000, Order Instituting Proceeding Under Section 206 of the Federal Power Act. https://www.ferc.gov/sites/default/files/2026-06/EL26-69-000.pdf
- EnergyTag (2024). Granular Certificate Matching Standard, Version 1. https://energytag.org/wp-content/uploads/2024/03/Granular-Certificate-Matching-Standard_V1.pdf
- Google (2021). 24/7 Carbon-Free Energy: Methodologies and Metrics. https://sustainability.google/reports/24x7-carbon-free-energy-methodologies-metrics/

## 9 Repository Sources for Current Design and Status

- [Research scope and primary-paper focus](../../agent.md): RQ2, the three-question blueprint, and evidence boundaries;
- [Finite-v2 contract](../../configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml) and [model specification](../../docs/model_spec/rq2_finite_mechanism_protocol_candidate_v2.md): 168h, 24h, q+r≤D, 1,900 cells, and development authorization;
- [Execution plan](../../docs/plan/科研项目执行步骤.md) and [blocker register](../../docs/model_spec/blocker_register.md): stage evidence, open issues, and closure conditions;
- [H1 end-to-end milestones](../../docs/plan/H1_端到端里程碑验收_v1.md): acceptance order from complete hour-0 to formal execution;
- [Chain_07 retained timing](../../results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/timing.jsonl) and [source-boundary check](../../results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/source_boundary_status_rechecked_01.json): development progress and approved source coverage;
- [Complete hour-0 report](../../results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/complete_integration_report_supplement_04.md) and [independent supplement 04](../../results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/postcheck_supplement_completion_04.json): the synthetic first-hour chain and independent-process saved replay;
- [Two-hour batch-replay acceptance](../../results/tables/rq2_h1_cross_hour_batch_v2_non_authoritative/acceptance_report.md) and [machine-readable postcheck](../../results/tables/rq2_h1_cross_hour_batch_v2_non_authoritative/connected_01_postcheck.json): six paired lane-hours and saved-state comparisons;
- [Three-hour outage and repair acceptance](../../results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/acceptance_report.md) and [machine-readable postcheck](../../results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json): seven paired lane-hours, lane stopping, missing input, and same-process read-only reopen;
- [B0-B2 results](../../results/tables/rts24_b0_b2_summary.json), [B3-B5 results](../../results/tables/rts24_b3_b5_summary.json), and [24-hour DC benchmark](../../results/tables/rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1/summary.json): the named historical evidence in Section 5.1.
