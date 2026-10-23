# Staged Interconnection and Flexibility Deliverability During AI Data Center Ramp-Up

Updated: 2026-10-23. Project research introduction.

## 1 Background and project objective

This project studies an AI data center as it ramps up toward its target operating scale. It asks whether workload flexibility can support given staged interconnection plans when business growth, computing-equipment commissioning, and grid construction progress at different rates, and which stages are limited by task recovery and hourly clean-electricity requirements.

Growing AI demand places pressure on electricity supply and grid access. The IEA's Energy and AI report examines the links between AI development, electricity demand, and infrastructure [1]. Mytton et al. discuss how geographically concentrated data-center demand can constrain local grid capacity [2]. For an individual project, the issue unfolds throughout ramp-up: tasks arrive gradually, computing modules are commissioned in batches, and supporting lines or transformers follow their own construction schedules.

These paths may become misaligned. Equipment and business may be ready while a grid reinforcement is still under construction, requiring lower electricity withdrawal during some hours. Eligible tasks can be deferred and completed later. Recovery, however, requires spare computing equipment, power headroom, and electricity that meets the clean-matching requirement before the original deadlines. Reducing demand now does not by itself guarantee later task completion.

Ramp-up changes both the source and the limits of flexibility. Early operation may offer spare equipment for recovery but too little eligible work to defer. Later demand growth may increase deferrable work while reducing recovery headroom. Timely equipment additions may ease that pressure. Which stage is more deliverable therefore depends on the relative progress of business, equipment, and the grid.

At one fixed point of interconnection, the project develops an hourly assessment of a small set of given construction and access plans. It identifies the stages in which each plan can deliver, the shortfalls that arise, and whether immediate response or recovery before deadlines is responsible.

Figure 1 connects the whole study: three given progress paths and common service rules feed three assessments. The full temporal assessment links deferral, debt, recovery, and metered power. Stage judgments are compared before the plan, capacity, and policy are frozen for execution on independent paths. Figures 2–4 expand recovery, progress mismatch, and network/CFE checks.

![Figure 1 Overall project research framework](../figures/project_framework_en.svg)

**Figure 1 From given progress paths to stage judgments and independent testing (overall framework).** Read downward through common inputs, three parallel assessments, stage judgments, and frozen-policy holdout. Blue folders are tasks; orange folders are deferred debt. Recovery needs equipment, power, hourly CFE, and compliance with original deadlines; debt and budgets persist across hours. Metered power P enters network and CFE checks. The frozen plan and an independent new path jointly feed holdout execution to identify applicability and failure regions. The figure depicts study design.

## 2 Related research

### 2.1 Data-center flexibility and grid interconnection

Kim et al. incorporate workload flexibility into planner-initiated data-center siting [3]. Chen and Zheng compare temporal deferral and spatial shifting for grid interconnection [4]. Wan and Li embed spatial and temporal load adjustments in security-constrained unit commitment to study congestion and operation [5]. Williams et al. demonstrate power-flexibility control by coordinating computing equipment with grid signals [6]. Together, these studies establish the value of flexibility through planning, scheduling, and practical control.

### 2.2 Task deferral, recovery, and service deliverability

Wierman et al. review opportunities and practical constraints for data-center demand response [7]. Liu et al. examine workload shifting together with local generation for reducing peak withdrawal [8]. GreenSlot schedules batch jobs within their deadlines to use renewable energy [9]. Radovanović et al. develop carbon-aware scheduling for temporally flexible data-center workloads [10]. These studies link deferral to service requirements and subsequent execution capability.

For flexibility commitments and service deliverability, Fan and Zhao jointly model workload queues and regulation-capacity commitments, checking instantaneous response and sustainability under cumulative calls [11]. Khanal et al. include workload make-up, event shape, and recovery restrictions in capacity expansion and compare flexibility across host grids [12]. Butt et al. connect task deadlines to minimum interconnection capacity under onsite PV, storage, and an investment budget [13].

These studies connect flexible demand to workload queues, make-up capability, deadlines, and resource allocation, extending assessment from immediate reductions to later task completion and service commitments.

### 2.3 Staged construction and infrastructure planning

Multistage transmission-expansion methods already represent demand growth and staged investment [14]. Vafamehr et al. study uncertain expansion of data-center modules and data networks [15]. Shao et al. jointly plan long-term data-center and power-system development [16]. Zhao et al. explicitly consider cluster load growth, construction sequence, and staged energy-resource additions [17]. Zhu et al. co-optimize transmission construction with lead times and geographic workload migration [18]. Wang et al. propagate uncertain large-model growth into supporting power-infrastructure expansion [19]. Ghosh et al. propose a phased engineering architecture addressing equipment procurement and interconnection lead times [20].

This research covers modular expansion, construction sequencing, transmission lead times, and long-term joint investment. It represents the relationship between growing demand and infrastructure development and incorporates construction progress into planning or engineering configurations.

### 2.4 Hourly clean-electricity matching

De Chalendar and Benson discuss limitations of annual renewable-procurement metrics [21]. Miller et al. study hourly accounting of emissions from electricity consumption [22]. Riepin and Brown analyze procurement strategies, costs, and system effects of 24/7 carbon-free energy [23]. Riepin et al. discuss how round-the-clock matching can encourage advanced clean technologies [24] and investigate spatial and temporal workload shifting for clean computing [25]. Guo et al. coordinate wind, solar, storage, grid exchange, and hourly supply deliverability for private-wire data centers [26].

Across accounting, procurement, scheduling, and supply planning, these studies connect the timing of clean-electricity availability with consumption and distinguish annual energy balances from matching requirements at finer time scales.

### 2.5 Remaining gaps in the existing research

The literature establishes methods for flexible access, workload recovery, staged construction, and hourly clean matching. For the continuous ramp-up of an individual AI data center, these findings need to be linked more explicitly in three respects.

First, **construction progress and operational delivery.** Models of modular expansion, lead times, and demand growth provide a basis for stage assessment. Assessing a given access plan also requires an hourly account of how misaligned business, equipment, and grid progress changes deferrable work and recovery resources, so that delivery can be checked throughout ramp-up.

Second, **immediate response and recovery before deadlines.** Queues, make-up, and deadlines already have explicit models. During ramp-up, it remains necessary to distinguish insufficient deferrable work now from insufficient recovery resources later, and to test whether the timing of equipment, power, and clean-resource availability changes plan judgments under the same instantaneous flexible MW and comparable total clean resources.

Third, **assessment judgments and their applicability.** Findings on flexibility, construction, and clean matching need to inform judgments about given staged plans through comparisons with common service objectives. This requires identifying when simplified and full temporal assessments agree or differ, and where a selected plan remains applicable on independent new paths.

### 2.6 Focus of this study

The study addresses these gaps at one fixed point of interconnection. Business ramp-up, equipment commissioning, and grid construction are separate given paths. A small set of staged access plans is assessed under the same external tasks, deadlines, and clean resources. The focus is: **when does progress mismatch shift the binding limit from currently deferrable work to equipment, power, or clean recovery resources before deadlines, thereby changing the judgment of a given plan?** Matched comparisons of three assessments and independent holdout execution of frozen policies are used to explain these stage-specific bottlenecks and their applicability boundaries.

## 3 Contributions

The study aims to make the following three contributions. Specific conclusions will depend on the subsequent comparisons and holdout results.

1. **A staged interconnection assessment framework for ramp-up.** Business growth, computing-equipment commissioning, and grid construction are represented separately. Tasks, commissioned computing capacity, and the built network at each stage are mapped to immediate response and recovery conditions before deadlines, supporting continuous delivery assessment of given construction and access plans at one connection point.

2. **An account of stage-specific bottlenecks and decision boundaries under progress mismatch.** With the same external tasks, deadlines, and clean resources, the assessment separates limits from currently deferrable work, equipment capacity, network supply, and clean recovery resources. Mechanism comparisons with matched immediate calls seek to identify when recovery timing changes plan judgments under the same instantaneous MW and how the hourly CFE target affects that boundary.

3. **Applicability boundaries for simplified assessments and selected plans.** Instantaneous-MW, fixed-recovery-headroom, and full temporal assessments are compared for the same given plan to determine whether recovery and deadline constraints explain different judgments. The plan, capacity, and operating policy are then frozen for execution on independent paths. Reporting includes agreement between assessments, conditions under which simpler assessments suffice, and delivery failures.

## 4 Research object and key concepts

| Concept | Meaning in this study |
|---|---|
| Business ramp-up | Externally arriving computing tasks approach the target operating scale; workload and deadlines define the common service objective. |
| Equipment commissioning | A module contributes executable capacity K only after installation and commissioning. |
| Staged interconnection | Given access allowances are checked against the built network and contract conditions. F is the firm portion; X is conditional on specified calls. |
| Workload flexibility | Eligible computation can be postponed and completed before its original deadline. |
| Recovery debt | Deferred but unfinished work, tracked by arrival time, recovery efficiency, and deadline. |
| Hourly CFE matching | A target share of consumption is matched with attributable carbon-free energy from the same hour and eligible region. |
| Deliverability | Response, clean matching, and task completion can be met together under the stated network, service, and information conditions. |

For example, an hour with 100 MWh consumption and an 80% target needs 80 MWh of eligible attributable CFE for that hour. Recovery consumption is included. This is energy-attribute accounting; allocation must conserve available resources and avoid duplicate attribution.

![Figure 2 Recovery conditions and alternative outcomes for deferred tasks](../figures/project_recovery_en.svg)

**Figure 2 How deferred tasks are recovered (expanded framework operation).** Follow 1 deferral now, 2 recovery in later hours, and 3 the original deadline check. Leaders identify the same orange cohort, spare equipment, power headroom, hourly CFE, and the original deadline; teal arrows connect task states. All three resources must be available in the recovery hour, with action budgets and recovery efficiency also respected. The upper outcome is on-time completion; the lower outcome records debt remaining at the deadline as overdue. Late recovery retains that violation; unobserved outcomes remain unresolved. Clocks and folder counts are illustrative.

## 5 Method

### 5.1 Represent the three progress paths separately

The model uses two or three equipment stages, one candidate grid project, and a small set of given access plans. Fast or slow business growth is crossed with on-time or delayed grid completion. Equipment paths separately define installation, construction, and availability. Commissioning follows the given start, lead time, and delay; only commissioned resources provide current capability.

Normal-state network checks cover the full F+X allowance. The declared contingency set checks F and the contractually permitted calls on X. The built network determines required reductions and power headroom during recovery, recalculated for each plan. Workload adjustment capacity D and access allowance X are distinct, linked through tasks, electricity consumption, and network checks.

![Figure 3 How progress mismatch changes operating and recovery conditions](../figures/project_rampup_en.svg)

**Figure 3 How the three progress paths change constraints (expanded framework inputs).** Follow one center through early operation, pending reinforcement, and actual commissioning. Leaders identify current work w, commissioned K, unfinished reinforcement, possible deferral q, and the commissioned grid asset. Three steps below explain current-work limits, supply on the built network, and reassessment of calls and recovery supply after commissioning. Debt and budgets carry across stages; response, recovery, and deadline checks still determine stage judgments. Counts and spacing are illustrative.

### 5.2 Link execution, deferral, recovery, and metered power

Hourly states record task arrivals, baseline work w, deferral q, recovery r, and commissioned equipment K. The quantities w, q, r, K, and adjustment capacity D use a common computing-resource reference unit, MW_c. Equipment parameters translate these units into metered electrical MW. Execution and recovery satisfy:

**0≤w−q+r≤K, q+r≤D.**

The initial model uses one aggregate action direction per hour, q·r=0. Deferral is limited by eligible current tasks. Recovery is limited by spare equipment, recovery efficiency, existing debt, and power conditions. Debt is accumulated and cleared by task batch; late completion retains the recorded deadline violation.

Metered power P includes the idle consumption of commissioned equipment, task execution, recovery, and supporting loads. New equipment can therefore increase both computing capacity and electricity demand. Recovery efficiency determines how much original work is completed, while one consistent equipment mapping converts computing effort into power.

### 5.3 Check network response and hourly clean matching together

The model derives the full grid call from the current network and pre-response baseline power, then checks whether physical response covers it. Clean matching requires αPΔt≤y≤Y in each interval: α is the target share, Δt the interval duration, y the allocated energy, and Y the externally specified attributable limit. Power P includes idle and recovery consumption. Plans share the same external clean resources and allocation rules.

The main comparison specifies independent reduction commitments: reductions separately promised to the grid and CFE services must be delivered using the same equipment, tasks, and recovery resources. Each unit of deferred work is allocated to one promise, and actual power is counted once. This is an explicit service-scenario assumption, consistently applied across comparisons; applicability to a particular project depends on its contract and metering arrangements.

![Figure 4 How metered power enters network and hourly CFE checks](../figures/project_network_en.svg)

**Figure 4 From computing tasks to power and two checks (expanded framework constraints).** Read the leaders around the center, fixed-point meter, and external attribution ledger, then follow 1 computing resources, 2 total metered P, and 3 network/CFE checks. P includes idle, execution, recovery, and support loads. Consumption records and the external hourly limit Y enter clean accounting. Normal-state and contingency F/X access allowances receive their separate contractual checks. The thick blue cable is physical supply; dotted links denote records and attribution. Symbols are illustrative; network judgments remain within the declared DC model and contingency set.

### 5.4 Preserve chronology and information

Task debt, budgets, and operating states carry between adjacent hours and across stage changes. Evaluation has explicit prior history and extends through registered task deadlines and required follow-up. Unobserved outcomes remain unresolved or right-censored; observed violations are retained.

Construction and access plans are fixed before evaluation. The operating policy uses information observed at the time, with identical actions under identical observed histories. Independent holdout paths do not influence plan or parameter selection. Construction plans, capacity, and operating policies are frozen before execution on those paths.

## 6 Comparisons and reporting

The main experiment compares a small number of given plans under the same external workload, deadlines, clean resources, and evaluation criteria. Differences in equipment or grid commissioning remain explicit properties of the plans.

| Comparison | Question addressed |
|---|---|
| Fast/slow business growth × on-time/delayed grid completion, with separate equipment paths | At which stage does progress misalignment become binding? |
| Instantaneous MW, fixed recovery headroom, full temporal assessment | Do omitted recovery timing and deadlines change the plan judgment? |
| Recovery-timing comparisons with matched immediate calls | Can later equipment, power, or clean windows change delivery under identical immediate response? |
| Essential sensitivities in eligible share, deadlines, and CFE target | Where do judgments change, and is the main mechanism stable? |
| Frozen plan and policy executed on independent holdout paths | Does the selected plan remain applicable on new paths? |

Results report access allowances, commissioned capacity, workload occupancy, deferral and recovery trajectories, grid and CFE shortfalls, overdue tasks, and unfinished work by stage. Full contract and task delivery are assessed before attributing a bottleneck. Matched-call cases serve as mechanism diagnostics; actual plan comparisons retain calls that change with the network. Minimum capacity is reported as a point only with adequate bound evidence; otherwise the result remains an interval or unresolved.

The data design uses traceable public network and workload sources and identifies the origins of equipment-power, deadline, stage-progress, and clean-allocation parameters separately. Cross-source records paired through stated assumptions support mechanism scenarios. Equal-weight comparisons of such scenarios do not estimate real ramp-up, construction-delay, or violation probabilities.

## 7 Expected outputs and deliverables

Deliverables comprise an assessment model for given staged interconnection plans, figures explaining stage-specific bottlenecks and decision boundaries, traceable inputs and computational records, and the complete thesis. Conclusions follow the comparisons, including unchanged judgments and failure regions. Network conclusions are limited to the declared DC model and contingency set; engineering application requires the corresponding safety studies.

## References

[1] International Energy Agency (2025). Energy and AI. IEA. <https://www.iea.org/reports/energy-and-ai>

[2] Mytton, D.; Ashtine, M.; Wheeler, S.; Wallom, D. (2023). Stretched grid? Managing data center energy demand and grid capacity. Oxford Open Energy, 2, oiad014. <https://doi.org/10.1093/ooenergy/oiad014>

[3] Kim, D.; Dong, L.; Xie, L. (2026). Flexibility-aware framework for efficient planner-initiated siting of data center. Nature Communications. <https://doi.org/10.1038/s41467-026-72324-9>

[4] Chen, Y.; Zheng, X. (2026). To Defer or To Shift? The Role of AI Data Center Flexibility on Grid Interconnection. DOI: 10.1145/3765611.3815593; arXiv:2604.05376. <https://doi.org/10.1145/3765611.3815593>

[5] Wan, H.; Li, X. (2026). Data Center Spatio-Temporal Load Flexibility in Security-Constrained Unit Commitment for Enhanced Grid Efficiency and Reliability. arXiv:2605.18517. <https://arxiv.org/abs/2605.18517>

[6] Williams, C.; Colangelo, P.; Coskun, A.; et al. (2026). Power-Flexible AI Data Centers: A New Paradigm for Grid-Responsive Compute. arXiv:2606.25098. <https://arxiv.org/abs/2606.25098>

[7] Wierman, A.; Liu, Z.; Liu, I.; Mohsenian-Rad, H. (2014). Opportunities and Challenges for Data Center Demand Response. International Green Computing Conference, 1-10. <https://doi.org/10.1109/IGCC.2014.7039172>

[8] Liu, Z.; Wierman, A.; Chen, Y.; Razon, B.; Chen, N. (2013). Data center demand response: Avoiding the coincident peak via workload shifting and local generation. SIGMETRICS, 341-342. <https://doi.org/10.1145/2465529.2465740>

[9] Goiri, I.; Le, K.; Haque, M. E.; et al. (2011). GreenSlot: Scheduling Energy Consumption in Green Datacenters. SC, Article 20. <https://doi.org/10.1145/2063384.2063411>

[10] Radovanović, A.; Koningstein, R.; Schneider, I.; et al. (2023). Carbon-Aware Computing for Datacenters. IEEE Transactions on Power Systems, 38(2), 1270-1280. <https://doi.org/10.1109/TPWRS.2022.3173250>

[11] Fan, Y.; Zhao, J. (2026). Harnessing Flexible Spatial and Temporal Data Center Workloads for Grid Regulation Services. arXiv:2602.01508v1. <https://arxiv.org/abs/2602.01508v1>

[12] Khanal, S.; Roh, G.; Yao, B.; et al. (2026). Shift or curtail? How much data-center flexibility is worth depends on the host power grid. arXiv:2608.19622v1. <https://arxiv.org/abs/2608.19622v1>

[13] Butt, H. Z.; Fatima, R.; Li, X. (2026). Minimizing Grid Interconnection Capacity Requirements for AI Data Centers: A Developer-Side Planning Framework with Onsite Resources and Workload Flexibility. arXiv:2608.29359v1. <https://arxiv.org/abs/2608.29359v1>

[14] Han, S.; Kim, H.-J.; Lee, D. (2020). A Long-Term Evaluation on Transmission Line Expansion Planning with Multistage Stochastic Programming. Energies, 13(8), 1899. <https://doi.org/10.3390/en13081899>

[15] Vafamehr, A.; Khodayar, M. E.; Manshadi, S. D.; Ahmad, I.; Lin, J. (2019). A Framework for Expansion Planning of Data Centers in Electricity and Data Networks Under Uncertainty. IEEE Transactions on Smart Grid, 10(1), 305-316. <https://doi.org/10.1109/TSG.2017.2738444>

[16] Shao, Z.; Yu, N.; Wong, D. (2025). Stochastic Long-Term Joint Decarbonization Planning for Power Systems and Data Centers: A Case Study in PJM. International Journal of Electrical Power & Energy Systems, 173, 111377. <https://doi.org/10.1016/j.ijepes.2025.111377>

[17] Zhao, H.; Yu, C.; Fu, G.; et al. (2026). Source-Load Coordinated Multi-Stage Low-Carbon Planning for Data Center Clusters Considering Construction Sequence. Energies, 19(17), 4153. <https://doi.org/10.3390/en19174153>

[18] Zhu, M.; Kai, Q.; Liu, Y.; Yan, Y.; Zhao, H. (2026). Virtual Transmission Lines from Data Center Workload Migration: Coordinated Multi-Year Transmission Expansion Planning. arXiv:2610.13032v1. <https://arxiv.org/abs/2610.13032v1>

[19] Wang, Q.; Huang, T.; Liu, Q.; Na, J. (2026). Power-infrastructure expansion planning for training-oriented AI data centers under large-model scaling uncertainty. Energy and AI, 25, 100840. <https://doi.org/10.1016/j.egyai.2026.100840>

[20] Ghosh, S.; Mohammed, N.; Sadi, M. A. H. (2026). A Phased Development Framework Enabling Islanded Operation of Sustainable AI Data Centers With Onsite Grid-Following and Grid-Forming Energy Architectures. arXiv:2607.17391v1. <https://arxiv.org/abs/2607.17391v1>

[21] de Chalendar, J. A.; Benson, S. M. (2019). Why 100% Renewable Energy Is Not Enough. Joule, 3(6), 1389-1393. <https://doi.org/10.1016/j.joule.2019.05.002>

[22] Miller, G. J.; Novan, K.; Jenn, A. (2022). Hourly accounting of carbon emissions from electricity consumption. Environmental Research Letters, 17(4), 044073. <https://doi.org/10.1088/1748-9326/ac6147>

[23] Riepin, I.; Brown, T. (2024). On the means, costs, and system-level impacts of 24/7 carbon-free energy procurement. Energy Strategy Reviews, 54, 101488. <https://doi.org/10.1016/j.esr.2024.101488>

[24] Riepin, I.; Jenkins, J. D.; Swezey, D.; Brown, T. (2025). 24/7 carbon-free electricity matching accelerates adoption of advanced clean energy technologies. Joule, 9, 101808. <https://doi.org/10.1016/j.joule.2024.101808>

[25] Riepin, I.; Brown, T.; Zavala, V. M. (2025). Spatio-temporal load shifting for truly clean computing. Advances in Applied Energy, 17, 100202. <https://doi.org/10.1016/j.adapen.2024.100202>

[26] Guo, F.; Soares, J.; Ma, L.; et al. (2026). Integrated planning of wind-solar-storage-grid systems for private-wire supplied data centers. Applied Energy, 414, 127841. <https://doi.org/10.1016/j.apenergy.2026.127841>
