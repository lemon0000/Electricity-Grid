# 智算中心达产过程中的分阶段接入与柔性可交付性研究

## 摘要

AI智算中心达产过程中，业务增长、设备投运与电网扩建可能不同步。延期计算虽能降低当期负荷，但任务仍须在原截止时间前完成，其恢复能力受已投运设备、供电余量与小时级清洁电力匹配约束。本研究探讨三条进度路径如何共同影响业务柔性可交付性及分阶段接入方案的可行性。

针对固定接入点和给定建设与接入计划，拟构建连接阶段状态与逐小时运行的评价模型，跟踪任务延期、恢复及期限，将设备运行与配套耗能映射为实际取电，并核查网络约束、小时级无碳能源（CFE）匹配和任务完成情况。可交付性按三值给出：当日响应、清洁匹配与期限内补做共同兑现时为可交付；任一不能兑现时为不可交付；期限尚未进入观察窗（右删失）或缺少求解与核查结果时为未决，未决既不计入成功也不计入失败。任务完成只读原期限，逾期后补做不消除已发生的逾期。

在相同外生任务、清洁资源与服务规则下，对同一计划并列比较瞬时可调功率、固定恢复余量和完整时序三种评价，并按两条对照轴分别定值：其一为各方法自身定值与其安排在实际路径完整时序约束下重放定值的比较，回答该简化方法的安排能否经得起它所忽略的约束；其二为各方法定值与完整时序策略对同一计划定值的比较，回答该简化方法是否拒绝了完整策略能够完成的计划。所比较的两种简化均放宽约束而非收紧，因此两类判断差异预期集中在简化判可交付而重放观察到违规的方向。另设匹配对照，在即时服务请求一致、清洁额度总量与峰值一致的条件下检验清洁恢复额度到达时段的作用；已兑现延期与恢复起点债务属策略运行结果，不在输入层固定，仅在结果分析中作为分层条件。最后将冻结的计划、容量与策略用于独立留出路径评价。

研究旨在识别瓶颈由当期可延期工作转向期限内恢复资源的阶段条件，界定简化评价与完整时序评价产生不同定值的区域，并在完整披露一致通过、一致失败与未决区域计数的前提下，为智算中心分阶段接入提供方案适用边界。

**关键词：**智算中心；业务达产；分阶段接入；可交付性判据；任务恢复；小时级无碳能源匹配

---

# Assessing Flexibility Deliverability for Staged Interconnection of AI Data Centers During Ramp-Up

## Abstract

AI data center ramp-up involves workload growth, equipment commissioning, and grid reinforcement that may progress at different rates. Deferring computation reduces current demand, but tasks must still meet their original deadlines. Recovery is constrained by commissioned equipment, power headroom, and hourly clean-energy matching. This study examines how these three progress paths jointly affect workload flexibility deliverability and the feasibility of staged interconnection.

For a fixed interconnection point and given construction and access plans, the study proposes a model linking stage states to hourly operation. It tracks task deferral, recovery, and deadlines; maps equipment operation and supporting loads to metered power; and checks network constraints, hourly carbon-free energy (CFE) matching, and task completion. Deliverability is three-valued: deliverable when same-hour response, clean matching, and in-deadline recovery are met together; not deliverable when any of them fails; and undetermined when a deadline has not yet entered the observation window (right-censoring) or solve and check evidence is missing, where undetermined counts as neither success nor failure. Task completion reads only the original deadline, and recovery after a deadline does not erase the recorded overdue.

With external tasks, clean resources, and service rules held consistent, instantaneous-power, fixed-recovery-headroom, and full temporal assessments are compared for the same plan and reported on two separate axes. The first compares each method's own verdict with the verdict of its schedule replayed under the actual path's full temporal constraints, asking whether a simplification's own arrangement survives the constraints it ignored. The second compares each method's verdict with the complete temporal strategy's verdict on the same plan, asking whether a simplification rejects a plan the complete strategy completes. Both simplifications compared here loosen constraints rather than tighten them, so disagreements are expected to concentrate in the direction of a simplified pass with violations observed in replay. A matched comparison holds immediate service requests consistent and total and peak clean allocations equal while changing only when clean recovery allocations arrive; delivered deferral and debt at the start of recovery are outcomes of policy execution, so they are not fixed in the design and appear only as stratification conditions in the results. Plans, capacities, and policies are then frozen for evaluation on independent holdout paths.

The study aims to identify when bottlenecks shift from currently deferrable work to recovery resources available before deadlines, to delineate where simplified and full temporal assessments return different verdicts, and to state applicability boundaries for staged interconnection plans while disclosing the counts of agreement, agreement on failure, and undetermined regions in full.

**Keywords:** AI data centers; workload ramp-up; staged interconnection; deliverability criterion; task recovery; hourly CFE matching
