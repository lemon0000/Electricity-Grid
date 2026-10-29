# 智算中心达产过程中的分阶段接入与柔性可交付性研究

## 摘要

AI智算中心从建设转向满负荷运营，需要经历业务需求增长、计算设备分批投运和电网扩建逐步完成的过程，三者的进度可能不同步。通过推迟部分计算，中心可以降低当期用电，但延期任务仍须在原截止时间前完成，其补做能力同时取决于已投运设备、供电余量和小时级清洁电力匹配条件。因此，分阶段接入评价需要把当前能够减少多少负荷与之后能否按期完成任务联系起来。本研究围绕进度错位与恢复资源的相互作用，研究达产过程中的业务柔性可交付性。

本研究以一个固定接入点和少量给定的建设与接入计划为对象，拟构建连接阶段状态与逐小时运行的评价模型，分别表示业务增长、设备投运和电网完工三条路径。模型跟踪任务到达、延期、尚未完成的工作量及原截止时间，将设备待机、任务执行、补做和配套耗能映射为计量点实际取电，并在延期与补做共享的调节容量下，按给定服务规则和网络范围核查电网响应、小时级无碳能源（CFE）电量属性分配与匹配，以及任务完成情况。只有已投运资源提供当期能力，未完成任务与运行状态沿连续时间传递。

比较设计在每条业务路径内保持外生任务、期限、清洁资源和服务规则一致，考察业务快慢达产与电网按期或延期投运的组合。对同一计划和调节容量，分别记录瞬时可调功率、固定恢复余量与完整时序三种评价的判断，并将各自运行安排置于同一完整时序约束下重放。另设恢复时段的匹配对照，在即时服务请求、已兑现延期、开始补做时的未完成工作量，以及清洁额度总量和峰值一致的条件下，仅改变清洁恢复额度的到达时段。随后冻结计划、容量和运行策略，在独立留出路径上按当时可见信息执行。

研究旨在识别履约瓶颈由当期可延期工作转向期限内恢复资源的阶段条件，检验相同清洁资源下恢复时段是否改变任务结局，并界定简化评价与完整时序评价产生不同判断的区域。预期形成阶段性瓶颈图、恢复轨迹对照及方案适用边界，为智算中心达产过程中的分阶段接入方案评估提供依据。

**关键词：**智算中心；业务达产；分阶段接入；任务恢复；小时级无碳能源匹配

---

# Staged Interconnection and Flexibility Deliverability During AI Data Center Ramp-Up

## Abstract

AI data centers approach full operation through growing workload demand, phased computing-equipment commissioning, and grid reinforcement. These processes may progress at different rates. Deferring computation can reduce current electricity demand, but the deferred work must still be completed before its original deadline. Recovery depends jointly on commissioned equipment, power headroom, and hourly clean-energy matching. Assessing staged interconnection therefore requires linking immediate load reductions to subsequent task completion. This study examines how progress misalignment and recovery resources affect the deliverability of workload flexibility during ramp-up.

For a fixed point of interconnection and a small set of given construction and access plans, the study proposes an assessment model linking stage states to hourly operation. Workload growth, equipment commissioning, and grid completion are represented separately. The model tracks task arrivals, deferral, outstanding work, and original deadlines, and maps equipment idle demand, task execution, recovery, and supporting loads to actual metered power. Grid response, hourly carbon-free energy (CFE) attribute allocation and matching, and task completion are checked under a shared capacity for deferral and recovery, within the specified service rules and network scope. Only commissioned resources contribute current capability, while unfinished work and operating states persist across stage boundaries.

Comparisons keep external tasks, deadlines, clean resources, and service rules consistent within each workload path, and examine fast or slow ramp-up with on-time or delayed grid completion. For the same plan and adjustment capacity, the judgments of instantaneous-power, fixed-recovery-headroom, and full temporal assessments are recorded separately, and their operating schedules are replayed under the same full temporal constraints. A separate matched comparison changes only the timing of clean recovery resources while holding immediate service requests, fulfilled deferral, outstanding work at the start of recovery, and the total and peak clean-energy allocation fixed. Plans, capacities, and operating policies are then frozen for execution on independent holdout paths using information available at each decision time.

The study aims to identify stage conditions under which bottlenecks shift from currently deferrable work to recovery resources available before deadlines; test whether recovery timing changes task outcomes under matched clean resources; and delineate regions where simplified and full temporal assessments reach different judgments. Expected outputs include stage-specific bottleneck maps, matched recovery trajectories, and applicability boundaries for the evaluated plans, supporting assessment of staged interconnection during AI data center ramp-up.

**Keywords:** AI data centers; workload ramp-up; staged interconnection; task recovery; hourly CFE matching
