# RQ2公开数据鲁棒识别路线图 v3

本文件是`RQ2_公开数据鲁棒识别路线图.md`的24小时执行后继。前驱文件已由
preregistration v2锁定，不再原地修改。

## 1. 研究问题与科学价值

研究对象仍是分离网络服务与小时CFE服务对同一业务时序柔性的重复承诺。
主estimand为`X/D_DC`、标准化服务短缺和恢复债务在未知跨源coupling下的
sharp identification interval，不估计真实企业合同违约概率。

## 2. 研究设计与因果逻辑

- RTS-GMLC v4提供541个training和530个holdout 24小时网络+CFE块。
- Alibaba v3提供34个training和34个holdout 24小时业务块。
- 两个来源没有共同日历，只保留各自经验边缘与块内时序。
- training只冻结策略；holdout只做固定策略Cartesian replay和transport。

Alibaba requested-GPU occupancy只定义逐时availability shape：

$$
a_{jt}=f\min\{w_{jt},1\}.
$$

CFE压力$d^{CFE}_{it}$进入业务模型时定义
$c_{ijt}=\min\{d^{CFE}_{it},a_{jt}\}$，保证单项CFE请求不机械超过该小时
业务资源。物理corrective-LP给出的$g_{it}$不截断；$g_{it}>a_{jt}$保留为
共同不足证据。

## 3. 方法与统计推断

每个OAT parameter cell使用8×8 weighted-stress training代表点，分别求
correct与B6的minimum-capacity full-service policy。若任一策略被证明
training infeasible，该cell的fixed-policy transport estimand未定义并单列。

两策略均冻结后，holdout使用同一因果grid-first规则：每小时只依据当前状态、
mandatory grid call、当前CFE请求和当前recovery headroom决策，不读取未来
小时，不重优化容量或整段recourse。每个eligible cell必须完成
`530 × 34 = 18,020`个pair；缺一pair不得声称sharp。

transport LP对九个注册指标分别输出lower/upper bound及其优化coupling，并
报告independent、comonotone和countermonotone诊断。恢复债务差值与容量、
failure、shortfall共同进入R1/R2/R3分类。

`partially_identified`的兼容区域只报告区间证据未排除的区域：R1/R3要求
全部差值区间均包含0，R2要求所有差值至少可能非负且至少一项可能严格为正。
这只是基于逐指标sharp interval的必要兼容性诊断，不宣称不同指标的极值由
同一个transport coupling同时达到。

## 4. 结果与外推边界

正式结果只允许解释为公开benchmark的部分识别区间。不得外推为Alibaba绝对
MW、经验事故概率、真实合同违约概率、PPA/REC履约、full-N1、AC安全或工程
容量认证。

## 5. 学术写作与叙事

论文主贡献保持为：分离合同下的共享时序资源重复承诺、解析容量/债务边界、
未知coupling的sharp transport identification，以及无未来信息的固定策略
回放。CFE请求截断必须表述为“可由该业务块提供的服务请求”，原始CFE deficit
仍作为电力压力信号保存。

## 6. 审查风险与失败模式

- training infeasible不是solver unresolved，也不是holdout failure。
- 未完成Cartesian product不能称sharp。
- OAT某水平缺失时，该维度的ambiguity-reduction必须为`unresolved`，不得用
  剩余水平缩小集合。
- RTS可靠性抽样不是经验事故概率。
- formal runner必须验证上游summary、schema、manifest、solver identity和
  checkpoint policy identity。

## 7. 执行路径

代码、配置、checkpoint和原子发布链已配置。当前正式门全部关闭：

1. 全量1071-block grid-need dispatch未授权、未发布；
2. pairwise replay与identification依赖该上游包；
3. R4聚焦修复复审尚未PASS；
4. 用户尚未单独授权正式长运行。

因此当前状态为`software-configured`，不是`formal-result-ready`。
