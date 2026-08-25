# RQ2公开数据鲁棒识别路线图

## 1. 研究问题与科学价值

首篇论文不再估计真实数据中心的合同违约概率。新问题是：

> 当网络条件服务与小时CFE服务分开承诺、但共同消耗一个只能部分观测的
> 业务柔性包络时，哪些重复承诺结论可由公开边缘数据稳健识别？

研究对象是可识别边界，不是对缺失现场数据作点估计。原70-cell相图作为
冻结探索性predecessor保留，不参与后继参数选择。

## 2. 研究设计与因果逻辑

RTS-GMLC内部的负荷、可再生与可靠性抽样共享同一8,784小时时钟，组成一个
联合的电力系统窗口。Alibaba只提供匿名相对时钟的业务窗口。未知关系只有：

```text
RTS-GMLC网络+CFE窗口  <----未知coupling---->  Alibaba业务窗口
```

主ambiguity set是保持两个经验边缘分布不变的完整离散transport polytope。
任何结果都不得把某一coupling称为观测联合分布。

## 3. 方法与统计推断

### 3.1 瞬时重复承诺定理

对非负调用轨迹`g_t`和`c_t`，共享资源的MW需求与分离承诺需求分别为

$$
R_S=\max_t(g_t+c_t),\qquad
R_B=\max\{\max_t g_t,\max_t c_t\}.
$$

因此

$$
0\le\Delta_R=R_S-R_B
\le\min\{\max_tg_t,\max_tc_t\}.
$$

严格风险条件为`max_t(g_t+c_t)>max(max_t g_t,max_t c_t)`。这是精确代数
结论，不依赖概率或GPU-to-MW拟合。

### 3.2 恢复债务下界

给定合计调用、净可用恢复头寸和效率，逐小时前缀采用全部有效恢复得到最小
可能债务轨迹。若其峰值或终值仍越界，则任何同一调用轨迹都不可恢复。该
结论只在无恢复ramp/跨时成本且活动调用小时恢复头寸为零的声明条件下成立。

### 3.3 未知coupling的sharp bounds

设电力系统窗口概率为`p_i`，业务窗口概率为`q_j`。所有允许的联合分布为

$$
\Pi(p,q)=\{\pi\ge0:\sum_j\pi_{ij}=p_i,\ \sum_i\pi_{ij}=q_j\}.
$$

固定策略在每个完整配对`(i,j)`上的指标为`m_ij`，则

$$
\underline m=\min_{\pi\in\Pi(p,q)}\sum_{ij}\pi_{ij}m_{ij},\qquad
\overline m=\max_{\pi\in\Pi(p,q)}\sum_{ij}\pi_{ij}m_{ij}.
$$

这是有限维transport LP的sharp bound。输入必须覆盖完整Cartesian product；
缺一对、solver未决或哈希漂移均fail closed。

### 3.4 部分识别

- `identified_R2`：所有coupling下B6均不改善任何注册指标，且至少一个风险
  下界严格为正；
- `identified_R1`：所有差值界为零，且correct在所有coupling下成功；
- `identified_R3`：所有差值界为零，且correct在所有coupling下失败；
- `partially_identified`：多个区域与界相容；
- `unresolved`：任一必要优化未解析。

完整事件模型不声明correct/B6可行域一般嵌套，因为分轨后事件分段数可能
变化；这一点通过数值MIP识别，不由MW定理替代。

## 4. 结果与外推边界

主结果使用`X/D_DC`、标准化短缺和标准化债务。WattGPU/NLR只验证外部功率
尺度范围，不把Alibaba逐job转换为MW。允许报告：

- 重复承诺容量的解析上下界；
- 固定策略服务损失的sharp coupling bounds；
- identified/partially-identified区域；
- 参数阈值与ambiguity-reduction value。

禁止报告真实合同违约概率、Alibaba绝对功率、PPA履约、full-N1、AC认证或
场址建议。

## 5. 学术写作与叙事

论文贡献限定为：

1. 分离服务合同对共享时序业务资源的重复承诺问题；
2. 瞬时容量与恢复债务的可证明边界；
3. 仅凭公开边缘数据时的sharp transport identification；
4. 保留事件、能量、恢复债务和固定策略回放的可复现benchmark。

“数据中心柔性”“24/7 CFE”“鲁棒优化”和“工作负荷移峰”均已有先例，
不能单独声明创新。

## 6. 审查风险与失败模式

- 若只画参数热图而无sharp bound，方法贡献不足；
- 若通过看结果选择参数子区间，后继证据失效；
- 若未完成Cartesian pairwise replay，transport bound不是sharp；
- 若把RTS可靠性抽样写成经验事故概率，结论越界；
- 若所有ambiguity set均跨多个区域，应诚实报告未识别，而不是收窄集合；
- 若完整时序模型宣称未经证明的可行域包含关系，理论部分不成立。

## 7. 执行路径

1. 从RTS-GMLC生成联合网络+CFE连续窗口；
2. 将每个抽样停运逐时送入SCOPF得到`grid_need`；
3. 从Alibaba生成dimensionless连续业务窗口；
4. 在每个注册物理参数阈值上冻结correct/B6策略；
5. 对全部电力系统窗口×业务窗口执行固定策略；
6. 用transport LP计算每个指标的sharp bounds；
7. 分类identified/partial区域；
8. 计算缩小单个不确定维度带来的ambiguity-reduction value；
9. 完整报告阴性、partial和unresolved区域；
10. R4独立审查与用户授权后才可启动正式批次。

当前已完成步骤3：`alibaba_dimensionless_workload_blocks_v2`从732,318条
正GPU请求task构造68个training和68个holdout 12小时块。归一化峰值只由
training拟合；908个跨split boundary的job及其916条task从两侧共同剔除，
确保job-level互斥。training marginal只用于拟合并冻结correct/B6策略，
transport column marginal与固定策略评价只使用holdout marginal。

步骤6的transport核心、步骤7的fail-closed分类器及步骤3-5所需的解析边界
组件也已实现。正式执行仍等待逐时outage-to-grid-need包、完整pairwise
outcome构建器、R4独立审查PASS和用户授权。
