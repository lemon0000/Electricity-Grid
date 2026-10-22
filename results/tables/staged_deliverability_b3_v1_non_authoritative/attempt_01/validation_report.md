# B3连续终结与保存重开开发验证

2026-10-22，`DRAFT_NONAUTHORITATIVE`。本次为[B3规格](../../../../docs/model_spec/staged_termination_development_v1.md)及[有界合同](../../../../docs/plan/staged_deliverability_b3_development_contract_v1.md)的一次开发诊断，`attempt_01`实际exit0、completion库存核验有效。B1/B2绑定源、参数及保存结果保持原字节；未创建生产manifest/lease、seal、official receipt或正式结果。

## 保存与终结结果

| 固定路径 | 最后接受小时 | 终结/重开结果 |
|---|---:|---|
| on_time/early | 7 | observation_complete；主任务按期完成 |
| on_time/late | 7 | observation_complete；原0.2 MWh_c永久逾期保留，后补做不抹去 |
| delayed/early | 2 | t=3参考接入权准入拒绝；0.2 MWh_c原债务右删失，当前输入已观察但未接受 |
| missing_input | 1 | 下一个必需小时2未提供；不造零输入/任务，保留0.2 MWh_c债务及右删失 |
| network_unresolved | 0 | t=1实际点声明数值异常；保存部分点、未接受提案与输入，健康重开仅重放已接受3步并审核原异常证据 |
| save_before_publish | 1 | 第5步close注入失败；旧状态确定，pending保留；重开为incomplete_publication并关闭 |
| save_after_publish | 2（重开裁决后） | 原进程commit_outcome_unknown、仅核到小时1；final字节/链/重放核对后确认小时2已接受、债务归零，未重复提交 |

三条主路径各有1个fresh child，完整state及独立network audit与父纯内存参考相等，均退出0。四个探针重开在同一进程执行，不称fresh-process故障恢复。数值异常在重开前已解除，不要求健康环境再造同一失败。完整F/X、一小时业务必要条件、实际轨迹和完整时序背书继续分层：post故障最小调用0.4 MW及登记X0.5 MW均超过aD0.25 MW，反例和`aggregate_contract_release=false`保持。

## 实际工作与成本

- 599次PYPOWER点计算、84次B1提案、86次网络尝试，业务fixture装载10次、fresh child 3个。重放和重复计算不是独立样本量。
- 顶层独立审计17次、network audit 19次，107网络小时与103已接受业务小时审计访问、8额外提案业务step访问、745保存点审核访问；独立审计使用Fraction，不调用PYPOWER。
- journal publish 59次，57次返回成功、2次注入异常；后者之一已有合法final。59个journal文件含保留pending；加16个顶层工件及completion，共76个机器工件、2,229,793 B。
- writer canonical编码334次/4,035,550 B，直接NetworkState编码记录访问391次；不代表嵌套state、ledger或独立审计的全部序列化成本。
- 脚本LAUNCH至完成输出15.3212838 s；PowerShell计时器从启动解释器至退出15.6388186 s。completion前观测15.2301670 s，进程树采样RSS峰值270,778,368 B；均未越过60 s、512 MiB、32 MiB限额。同步阻塞不能被合作式采样即时中断。
- 主要父阶段：fresh child启动/重放/后缀9.0793063 s，开始/结束指纹合计1.8955540 s，四次probe reopen合计0.3521732 s。子阶段与父等待有重叠，不相加为独立耗时；详细阶段见report.json。

completion清单的75个工件及自身读回一致；42仓库、7项选定外部文件/运行包版本、B2 report/completion与B1九pin保持。结果只覆盖本两母线、最多10小时、固定轨迹和保存结构，不外推主实验规模或192小时。

## 检查与限制

最终8份相关测试298 passed、1 skipped（本机symlink权限），pytest26.55 s；6074条警告来自所用PYPOWER的numpy.matrix pending deprecation路径。包括独立算术/期限、全部8个发布阶段、初始化失败、canonical/链篡改、完整/截断pending、witness字节绑定、重开晚错误、重复finish、资源/完成标记与child退出边界。单元测试不计入上述诊断调用量。开发中先前的序列化属性假设由失败测试发现后修复；没有覆盖或重跑已保存attempt。

只读独立pre-seal静态复核已闭合发现；保存后Fraction/哈希复核以verification.json记录为准。这些不是official verdict或receipt。平台目录耐久、真实掉电/坏盘、阻塞I/O、kill与failure报告本身失败的昂贵收尾仍未测；当前文件系统读回的纯模拟接受不提供真实设备exactly-once。完整state摘要仍有O(T²)编码访问，不能以当前小例声称一般线性成本。

下一步按[C范围与成本计划](../../../../docs/plan/staged_deliverability_c_scope_and_budget_plan_v1.md)固定最终网络/主张、DAG及成本复用边界，再测缺口并核定D/E点数。C整体性能审查与主实验规模仍OPEN。本文与verification.json是运行后supplemental说明，不改写原completion清单。
