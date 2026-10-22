# C范围、DAG与结构预算检查点交接

2026-10-22，`DRAFT_NONAUTHORITATIVE`。接续[B3交接](continuation_handoff_20261022_b3.md)、[C总计划](staged_deliverability_c_scope_and_budget_plan_v1.md)及[介绍索引](../../paper/drafts/README.md)。

## 当前选择与已完成

用户明确选择“保留公共网络方向”。本轮确定最小公共网络后继为**PYPOWER IEEE RTS-24、单接入点、声明持续故障状态的DC评价**；两母线保留机制回归。`minimum_curtailment`为待接主要网络请求接口。具体POI、候选工程、F/X、背景负荷、事故集、设备—任务—取电缩放、前史/登记/后续观察及资源点尚须事前输入表固定，不能直接继承旧69事故配置。

[C完整DAG与结构预算页](staged_deliverability_c_dag_and_cost_review_v1.md)已作为保存核验输入绑定，保留用户回复前的候选措辞。本文和C总计划记录回复后的选择，不回写该绑定页。DAG覆盖父连续参考、fresh重开、正常C/故障F-X/实际点、策略/期限、journal、四失败探针及报告；小时和重开按新调用节点展开，不折扣重复工作。

一次[保存记录核验](../../results/tables/staged_deliverability_c_v1_non_authoritative/saved_audit_01/validation_report.md)exit0：118个B1–B3文件/3,234,268B、42仓库pin、7选定外部和RTS-24源SHA一致；独立重算599点/84业务步/86网络尝试，与原登记及保存值一致。四probe的原因/role/adoption和state关系核对通过。10项新针对检查通过，普通只读开发审查无剩余High/Medium发现。

本次新flow/solver/child均为0，未模拟新小时。核验脚本0.4098294s、解释器启动至退出0.5349412s，末段RSS36,401,152B；这些是本次读记录/结构会计成本。原B3的15.639s和10小时仍只支持原两母线组件，公共网络/主实验wall未知。

## 下一步继续

1. 先固定RTS-24输入表及声明主张；保留真实来源和机制假设之分。外生任务/Y在计划之间可比，不从已看结果反调尺度或事故集。
2. 新建独立版本的staged公共网络adapter/配置/审计，保持B1–B3全部绑定源/记录；现有网络仅full_temporal，三种评价及简化动作的完整约束回放仍待接，不能把B1三个名字当成已完成。
3. 先做无solver schema/DAG和独立残差小例，明确每种网络query的solver调用数与exact-key复用条件。需要真实native代表测量时先登记具体包、次数/call cap、wall/RAM/存储、心跳/停止/失败保留及验收问题并取得专项授权；用户确认公共方向没有授予该权限。
4. 在所选网络上补关键成功/昂贵失败、journal/close/fresh-replay/report和更长cohort的代表成本，之后才固定D计划×路径×D点×三方法以及E留出数/总预算。完整F/X反事实时序背书是另一个后继；当前失败反例保持。

完整state摘要/目录扫描与cohort增长、每次L小时前缀重放另计。C整体性能审查仍OPEN，D/E未启动；不由本次读记录核验或24/192结构算术推导资源准入。STAGE-01/02现实合同/归属/功耗/期限等缺口保留，历史H1及formal/native/resource门仍按原定义。

## Git与进程

接入时HEAD与远端`experiment`均为`2e8fd43577d8ab2dc06a91cc02e026ca52157f88`，仅有三个无关未跟踪插图文件：`paper/figures/project_cartoon_assets_v1.json`、`project_rampup_cartoon_v1.png`、`project_recovery_cartoon_v1.png`。这些文件保留，不纳入本C检查点。

接入时未发现Python/solver活动进程；本次审计已exit0，无子进程。后续继续仍须刷新Git/process，不能以本快照推断未来状态。本检查点只同步C新增工具/测试/预算文档/保存核验与导航。最终提交号以远端读回为准，不把上面的接入HEAD当作最新HEAD。
