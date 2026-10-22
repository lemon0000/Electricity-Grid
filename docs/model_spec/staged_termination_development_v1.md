# B3连续终结与模拟接受记录规格

2026-10-22，`DRAFT_NONAUTHORITATIVE`。承接[B3/C计划](../plan/staged_deliverability_b3_c_next_steps_v1.md)，限于B2两母线合成小例、单写入者和纯模拟。新增后继，不修改B1/B2绑定文件。没有真实设备副作用；本文的“提交”是当前文件系统可读回的模拟接受，不提供掉电耐久、真实设备exactly-once或工程/容量认证。

## 接受点和状态

genesis绑定调用者的config、parameters、plan、trajectory identity、初始小时、登记边界、声明观察终点、初始完整状态摘要及实现/输入/选定依赖指纹。每个成功小时只保存一个step文件，包含ordinal、物理小时、exact observation、B2完整当小时record、genesis/parent SHA及before/after完整状态摘要。

只有B2实际运行row为`conditional_operating_point_committed`、`committed=true`、proposal存在且`ledger_applied=true`，candidate没有stopped并且business恰推进一小时，才可以写step。完整F/X的业务必要条件失败不阻止该实际条件轨迹step，也不被step发布提升为合同释放。

写入顺序为：独占pending→write→flush→file fsync→close→pending严格JSON/字节核对→同目录不可覆盖发布→final严格读回。最后读回一致后才在本进程采用candidate。每小时文件包含完整row，故不需要另设候选/accept双对象。父状态在计算和I/O失败时保持不变；性能计数记录实际计算，包含未提交计算，不作为业务状态。

进入发布调用之前失败，父状态确定，残留pending保留。step进入发布至final读回完成之间发生异常，标`commit_outcome_unknown`；原进程不采用、不继续，最后确定状态仅为下界，不称其为最终已提交状态。attempt/checkpoint/terminal的同类异常标`publication_outcome_unknown`，已接受业务状态保持known，工件/终结发布结果未知。I/O失败会话不再写普通terminal，其报告仅内存或外层best-effort保存。

fresh reopen验证最终文件与整个连续前缀后裁决：valid final可接受；pending无final是未提交尾部，返回closed、状态known的`incomplete_publication`，保留并停止；坏final、gap、final+pending或矛盾证据均拒绝，禁止静默回滚续写。若外部已报告发布失败，调用者必须携带`recovery_witness`的operation/target/expected SHA/是否可能发布/原终结意图/已观察当期输入；不能只凭目录丢失了所有尾部文件就恢复成从未发生失败。无final且step可能已发布时仍为未知；其他工件缺失可保留已接受业务状态known，但工件结果未确认并禁止续写。没有可移植目录fsync/存储硬件保证，因此不声明抗断电能力。

## 终结与任务结局

| 原因 | 保存与解释 |
|---|---|
| observation_complete | 到声明终点；任务结局仍可包含已观察逾期，与过程正常结束分开 |
| missing_input | 声明范围内下一必需小时未提供/不连续；不调用该小时策略，不造任务或零输入 |
| followup_horizon_insufficient | 到声明终点但已接受主要任务仍未到期；保留右删失，不能称完整主要覆盖 |
| policy_or_admission_rejected | 保留B2具体status及拒绝attempt；固定策略拒绝不等于数学不可行；当期到达已观察但未接受 |
| network_unresolved | 保留异常、阶段和部分合同/参考/提案；不在健康环境重造同次异常，不写成零请求或不可行 |
| persistence_failure / commit_outcome_unknown | 分清发布前失败和提交结果未知，记录操作、phase、候选与最后确定前缀；失败报告本身仅可best-effort保存 |
| publication_outcome_unknown / incomplete_publication | 非step发布结果未知或pending-only未完成；业务状态与工件结果分别表示，均封闭当前会话 |
| independent_audit_failure | 保存执行器已接受head与audit_validity=failed，禁止继续；不撤销旧step，不把独立审计失败混成存储状态丢失 |
| initialization_failure | create抛带零接受前缀的CreateError；保存genesis发布阶段与recovery_witness。无有效genesis时禁止推进；fresh reader仅在身份与目录无矛盾时裁决初始化工件，valid final可重开 |
| reopen_failure | 保留最后已核前缀、坏位置及可能更晚接受；最终状态未知，不返回可续写会话 |

已有任务仅按已接受业务小时结算。`last_accepted_hour`、`attempted_hour`、`next_required_hour`分别保存；永久逾期不被未提交恢复或后续故障抹去。已提供但未接受小时的arrival单列`observed_pending_unaccepted`，不加入ledger；缺输入的arrival为`not_observed`；正常结束为`none`。跳时输入只记录provided_hour，不保存未来workload/Y/due。future_arrivals_unobserved按最后已观察arrival（包括合法attempt）与声明终点比较。到达但没有延期的任务也保留，未来未观察任务不生成行。任务期限恰为未提交attempt小时仍按最后接受小时右删失，不制造该小时末逾期。

## 重开与独立审计

调用者提供**确切的已接受观察前缀**，若另有拒绝/未决attempt，再单独提供该小时observation；继续执行的新输入另传，不能混进prefix。按genesis核对身份、实现和参数，逐step重新执行纯B2转换，同时比较exact row、before/after完整状态摘要和parent SHA。拒绝/未决attempt以其保存证据附到已接受前缀做一次B2独立审计，不要求重复产生异常。

step只表示执行器模拟接受；独立审计在终态/重开时对完整前缀做一次。审计失败不撤销已发布step，报告最后已核前缀及未知并停止。这样避免每小时全prefix独立审计；完整状态摘要本身仍序列化增长历史，存在O(T²)字节访问，当前T≤10逐项预算，不能声称一般规模线性。每小时仅存新row，持久记录为O(T)条；重开需额外T次策略/潮流，按实际次数记录，不计成新独立样本。

genesis、step、attempt、checkpoint和terminal均不可覆盖、限制2 MiB、严格canonical字节、拒重复JSON键/NaN。B2 report先与其原completion清单核size/SHA，再核旧源及选定外部依赖/版本。flat store拒目录、symlink、未知文件、gap、bool-hour、错误摘要及多余step。live append核genesis/当前head SHA和exact ordinal文件名；零步checkpoint也绑定初始head。checkpoint只在指定前缀保存一次完整状态及head；关闭是所有文件句柄已随单次写操作关闭后的会话封闭，不拥有外部控制句柄。保存/关闭/发布/读回失败、未知提交裁决及坏重开窗口均需针对性故障测试。

重开时外部witness必须与唯一pending的目标一致，不能用其他角色的pending掩盖未知step。无witness的完整canonical step/attempt pending可恢复“已观察但未接受”输入；step只识别输入信封，不提升其科学有效性或接受状态。坏/截断pending保留`evidence_unresolved`，未来输入是否观察为null，不能宣称未观察。数值未决优先按原row status保存，即使terminal后续保存失败也不改变该结局。成功finish及成功终态重开后的重复finish只做等值读回，不重写终态；内容不同即拒绝。

本轮有界测量的规模、调用量、资源上限与未知范围见[B3执行合同](../plan/staged_deliverability_b3_development_contract_v1.md)。主实验规模、昂贵真实磁盘故障/清理和一般网络范围不由本规格解除。
