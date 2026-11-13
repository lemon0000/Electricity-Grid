# ASI 本地基准复算结果

2026-11-09。DRAFT_NONAUTHORITATIVE，复算已有文献结果，不作为本项目创新成果。

## 结果与可用范围

本地v1.0.1小时衍生产品可用于固定版本的eligible功率基准。从另附pod聚合表按公开功率公式独立重建central、idle-retained、LP可削减功率，与发布小时产品最大绝对差1.7764e-15 MW。该结论仅覆盖此功率边界与中心参数，不覆盖设施总功率、所有MC参数、实际响应或恢复。

20个持续时长—可靠性组合的K、窗口数与均值比例标量基线均复算一致；持续时长1/2/4/8/24小时，可靠性0.5/0.9/0.95/0.99。原产品scope标签为fleet；首份报告误按top搜索，使archived reference字段为空。原始报告保留，由comparison.json补齐20点和标量对照，最大K差6.67e-16 MW。

## 时间与集群口径

4440个连续小时格，4439个有效小时，唯一缺测为t=126（从0起，第6天第7小时）。have与good完全一致。缺测保留为NaN，不压紧时间；跨缺测窗口全部排除。h1/2/4/8/24分别有4439/4437/4433/4425/4393个有效窗口。

衍生cluster表有16个cluster。按上游对完整网格均值≥0.02MW规则保留13个，组合平均eligible功率3.5308527437MW。原文155410GPU与17个生产cluster口径，不应直接等同该衍生产品中16个cluster或最终13个eligible组合。

|调用时长|95%历史eligible功率/MW|均值比例标量高估|
|---|---|---|
|1h|2.507774|约17.4%|
|2h|2.421692|详见comparison.json|
|4h|2.316798|约25.5%|
|8h|2.161580|详见comparison.json|
|24h|1.946567|约46.6%|

全部集群功率边界的有效小时均值：attributed与node_sleep为5.988070MW，idle-retained为3.546536MW，与发布headline完全一致。它们是不同控制/电气假设，不得混用。

## 行数差异的处置

另附pod_hourly_agg.parquet实际1479356行，其中正gpu_hours行1022646，零gpu_hours行456710。去掉零GPU工作行仍不等于文献声明858816行，所以行数原因仍未闭合，不能称已证明完全同版。

但用于central LP active功率的重建已逐小时吻合，说明该具体用途未发现数值冲突。保留输入hash和行数记录，允许固定版本用于该基准；若拟重算其他功率口径、MC或调度过程，应另核CPU/状态等字段与上游原始处理范围。不存在逐任务ID、SLA期限和checkpoint轨迹，不能由此恢复实际干预债务。

## 统计口径

本次复现numpy默认线性分位数。有限样本下覆盖率可能略低于名义alpha，例如h1、alpha=.95得到0.9499887362。它是原文分位数估计的复现，不是严格95%保证；重叠窗口也不是独立样本。没有另做外样本承诺或统计置信保证。

## 运行与核验

主复算24.379秒，Python跟踪分配峰值350569662字节（不等于RSS），其中衍生表部分0.486秒。只读输入，零求解器、零MC、零新下载。首份报告与后处理均带SHA；源码、契约与输入绑定。后处理读取已保存曲面，补对fleet标签及标量公式，不重复大表重建。

证据：[原始报告](../../results/tables/asi_baseline_reproduction_v1_non_authoritative/attempt_01/report.json)、[完整对照](../../results/tables/asi_baseline_reproduction_v1_non_authoritative/attempt_01/comparison.json)、[曲面CSV](../../results/tables/asi_baseline_reproduction_v1_non_authoritative/attempt_01/surface.csv)。脚本：[主复算](../../experiments/asi_baseline_reproduction_v1.py)、[后处理](../../experiments/asi_baseline_comparison_v1.py)。

## 对研究的直接含义

可以固定这组小时eligible序列及20点曲面作为强文献基准，不再用任意固定柔性比例代替其历史持续性。需要保留时间空洞、功率边界、组合选择和训练/验证分离。

这没有解除此前仿射物理约束可压缩的结论：曲面就是从逐小时序列计算的。后续如研究重复调用或阶段信息，必须检验既有历史eligible产品之外的恢复可行性/决策后果；所有checkpoint损失、原期限、控制可实现比例在缺少观测时仍为明确情景假设。

## 独立只读开发审查

审查确认缺口窗口数、13/16逻辑集群筛选、fleet标签更正后的20点复算一致。契约中的“15集群三种边界”不应作为实际组合定义，采用产物16逻辑集群和筛选后13集群口径；本轮没有逐项保存排除集群阈值裕量。三边界均值属于同ZIP的衍生表与headline内部对照；只有central GPU-side idle-retained时序进行了另附pod聚合表的独立公式重建。标量基线的workload由四层衍生表相加，并非从pod原始记录重建。线性分位数的经验coverage已报告，未实施严格order-statistic保证版本。行差仍未闭合。审查为non-authoritative development review，不是official sealed review。
