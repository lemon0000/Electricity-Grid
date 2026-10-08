# 开放活动 planner：原生赋值与短求解接入

2026-09-28，`DRAFT_NONAUTHORITATIVE`。实现为 `planner_open_activity_assignment.py` 和
`planner_open_activity_short_solve.py`，接入既有版本化开放活动 builder 与严格 witness。
它补齐开发用原生证据通道，不注册有限登记参数、不发布完整容量证书或正式结果。

## 身份和证据范围

新输入、assignment、owned solve result 具有独立类型及 contract identity。旧模块保持原字节。
复用旧数值快照、标准结构摘要、原生标签解析、开发预算校验规则，不把新结果送入旧planner。
赋值审计从可信输入重建新 canonical 模型；submitted 模型的约束失活不能隐藏实际残差。
严格 Fraction witness 独立于数值赋值接受，边界 `q=1e-6` 的假活动仍被物理见证拒绝。

owned runner 每次 fresh build、最多调用一次 solver；捕获求解前后模型、options、包版本、
原生变量/目标/枚举/界，再显式加载并重建审计。不接受调用方注入模型或结果，结果不能由
普通构造或 dataclasses.replace 改写。缺值、来源不明、超时、多解、异常仍保留 unresolved。
此证据是同进程开发来源检查，不是原生历史执行的外部认证或正式持久执行链。

数值门完整继承旧 short-solve，包括原始有序 LB/UB、严格 `lower<=canonical objective`、
原目标一致性与 gap 计算；不扩展用户只对 normal 作出的数值修复授权。
上限仍为30秒solver time limit、4线程、20000变量、100000约束、16 scenarios、168小时。
时间限是solver选项，不承诺进程wall-clock。新适配不扩大运行规模。

结果显式报告 `activity_representation=open_activity_boundary_outer_relaxation`，区分
`relaxed_prefix_assignment_audited`、`relaxed_prefix_interval` 与 `effective_prefix_witness_available`。
松弛区间按声明数值容差解释，不是精确数学最优证明；prefix/complete容量证书、causal证书、
不可行证书继续为空。B6 witness仅证明separate planning前缀。

## 验证和保留证据

初批新46项测试通过2.03秒，相关六文件共297项通过3.58秒。预审建议补入“数值最优松弛区间存在、
物理见证仍失败”的直接反例后，最终新48项与旧相关回归共299项通过3.52秒；包含新旧builder、
witness、assignment及short-solve。首次收集因测试函数缺少参数名失败，修正后重跑通过。
故障生成器来自旧测试，仅在测试作用域替换其runner/builder，旧测试在同批回归中恢复原绑定。

直接边界反例为3小时grid=(0.25,0,0.25)、GRID_EXCESS、最多1次事件：闭模型用中间小时
q=1e-6连续跨过空请求小时，峰值0.25是独立必要下界。模拟及真实原生结果均得到[0.25,0.25]，
数值赋值接受，严格物理见证拒绝。该例不证明服务不可行，只证明不能从松弛解推断物理履约。

另保存四臂真实HiGHS 1.15.1合成短例：2小时、1线程、每次time limit=1秒；各调用一次。
grid=(0.25,0)、CFE=(0.125,0)、eta=0.8、首小时birth在第二小时到期，minimum_event_power=1e-6。
四臂松弛原生区间分别为[0.25,0.25]、[0.125,0.125]、[0.375,0.375]、[0.25,0.25]，
全部精确恢复见证通过。前三臂23变量/47约束，B6为41变量/88约束。
这些是合成机制算例，不是真实公开数据容量，也不代表有限登记完整支持已验证。

全部原生快照、assignment、witness、options和assessment保存于
`results/tables/rq2_continuous_planner_open_activity_native_v1_non_authoritative/`，
四文件由 `inventory.json` 绑定。该目录不是生产archive，不提供resume。
开发命令和代码hash见同目录 `development_checks.json`。

下一必要工作是有限登记合同的 enrollment/follow-up 支持与验收实现、training容量证书到holdout
策略的绑定，以及全支持资源核验。当前168h短验证预算不能直接用于168h登记加24h follow-up；
若采用该候选，192h输入、对应预算及资源门必须另行明确，不缩短登记集合来绕过门禁。
