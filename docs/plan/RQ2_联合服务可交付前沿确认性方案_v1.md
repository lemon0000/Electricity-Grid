# RQ2 联合服务可交付前沿确认性方案 v1

> 状态：`SEALED_READY_FOR_INDEPENDENT_REVIEW`。科学定义以
> `configs/rq2_joint_deliverability_preregistration_v1.yaml`和
> `docs/model_spec/rq2_joint_deliverability_estimands_v1.md`为准。本方案不授权
> solver、formal run或结果发布。

## 1. 论文主线

首篇论文研究网络安全调用与小时级 CFE 调用共同占用业务时序柔性时的可交付
边界。核心输出不是单独的一条共享预算约束，而是：

1. 随小时级 CFE 目标变化的四臂最低柔性需求曲线；
2. 单服务瓶颈、联合时序交互与B6有符号容量偏差的可审计分解；
3. 冻结策略在共享物理包络中的场景外服务后果；
4. 负结果、不可行和未决状态的完整发布。

B6是四臂分解中的记账诊断。论文主容量指标为
`I_joint = D_J - max(D_N, D_C)`，B6容量偏差为
`A_B6 = D_J - D_B`。

## 2. Problem–Method–Insight

| 项目 | 冻结内容 |
|---|---|
| Problem | 网络安全调用固定为硬服务时，小时级CFE目标提高会把联合业务柔性推到什么边界，单项不足与联合冲突各贡献多少 |
| Method | 46-cell前瞻性设计；network-only、CFE-only、joint-correct、joint-B6四臂；完整24h时序包络；训练支持审计；固定策略holdout |
| Insight | 给出离散柔性需求前沿、加法归因和瓶颈向量，区分单服务受限、联合额外需求、组合缓解和B6高配/低配 |

## 3. 确认性假设

### 3.1 结构门

在同一 cell 和同一 \(\alpha\) 下：

\[
I_{\mathrm{joint}}
=D_J-\max(D_N,D_C)
=I_{\mathrm{sep}}+A_{\mathrm{B6}},
\]

\[
I_{\mathrm{sep}}=D_B-\max(D_N,D_C),
\qquad
A_{\mathrm{B6}}=D_J-D_B.
\]

该恒等式验证指标由同一组四臂容量重建。完整事件包络下不预设四臂容量顺序；
结构门失败时停止归因。

### 3.2 经验判据

- `joint_extra_requirement`：\(I_{\mathrm{joint}}>10^{-6}\)；
- `joint_portfolio_relief`：\(I_{\mathrm{joint}}<-10^{-6}\)；
- `b6_capacity_underprovisioning`：\(A_{\mathrm{B6}}>10^{-6}\)；
- `b6_capacity_overprovisioning`：\(A_{\mathrm{B6}}<-10^{-6}\)；
- `b6_operational_penalty`：B6-minus-correct 的任一注册服务风险满足
  transport `LB>10^{-6}`；
- `single_service_binding`：相应单服务被证明不可行，或服务风险满足
  all-coupling robust positive。

上述标签可并存，不以互斥区域频数代替机制归因。

## 4. 冻结实验矩阵

### 4.1 Primary factorial

| 参数 | 水平 |
|---|---|
| `hourly_cfe_target` | 0.50, 0.70, 0.85, 1.00 |
| `flexible_fraction` | 0.05, 0.20, 0.50 |
| `normalized_recovery_headroom` | 0.00, 0.10, 0.30 |

共 \(4\times3\times3=36\) 个 cells，形成九条四点离散需求曲线。

### 4.2 Secondary OAT

锚点为 \(\alpha=0.85\)、`flexible_fraction=0.20`、
`normalized_recovery_headroom=0.10`。以下五个参数各增加两个非基准水平：

| 参数 | 水平 |
|---|---|
| `recovery_efficiency` | 0.60, 0.85, 1.00 |
| `maximum_event_duration_hours` | 1, 4, 8 |
| `maximum_event_count` | 1, 2, 4 |
| `normalized_energy_budget` | 0.10, 0.40, 1.00 |
| `normalized_debt_limit` | 0.05, 0.20, 0.50 |

新增10个唯一cells，总计46个。OAT只解释局部机制，不声称联合参数稳健性。

## 5. 阶段顺序

严格执行：

1. seal本科学协议并完成独立R4 review；
2. 建立target-specific CFE call、46-cell inventory和非互斥归因的versioned
   implementation successor；
3. 用合成小例验证四臂嵌套、加法分解、CFE目标重建和失败状态；
4. 完成implementation successor的独立R3/R4 review；
5. 验签1071-block grid package；
6. 另获用户formal-run authority；
7. 运行46-cell四臂planning与完整training-support audit；
8. 仅对eligible cells运行holdout Cartesian replay；
9. 计算transport bounds、共同coupling witness和bootstrap；
10. 发布完整cell inventory、frontier、归因、负结果与未决状态。

任何上游stage未完整发布并验签时，不启动下游stage。

## 6. 实现验收矩阵

| 验收项 | 最低证据 |
|---|---|
| CFE目标重建 | 手算alpha=0.50/0.70/0.85/1.00；完整缺口不按available flexibility截断 |
| CFE恢复闭环 | `min(business headroom, CFE-compatible surplus)`逐时审计 |
| 46-cell inventory | 独立生成器与测试oracle得到36+10且无重复 |
| 四臂投影 | 非call字段逐项相等；network-only跨alpha容量完全一致 |
| 容量证书 | solver status、incumbent、bound、gap、residual和full-support audit |
| 结构门 | 每个eligible cell验证`I_joint = I_sep + A_B6` |
| holdout因果性 | 当前状态only；容量和recourse均不使用holdout未来信息重优化 |
| 服务通道 | hard-grid、CFE shortfall和joint failure机器字段分开 |
| E0 | 无条件质量单列；条件风险不含E0 |
| transport | primal/dual、attaining endpoint、边缘残差和common-pi |
| 发布 | 46 cells含negative/infeasible/unresolved；manifest与provenance完整 |

## 7. 结果解释

确认性结果按以下顺序解释：

1. 先报告单服务瓶颈；
2. 再报告 \(I_{\mathrm{joint}}\) 的方向与幅度；
3. 用 \(I_{\mathrm{sep}}+A_{\mathrm{B6}}\) 分解联合交互；
4. 最后报告B6冻结策略的场景外后果。

若大多数cells由某一单服务直接限制，论文结论是该服务决定了注册边界。若两项
单服务均可交付但 \(I_{\mathrm{joint}}>0\)，结论是联合时序增加柔性需求；若
\(I_{\mathrm{joint}}<0\)，必须用事件分段与binding witness解释组合缓解。
\(A_{\mathrm{B6}}>0\)表示B6低配，\(A_{\mathrm{B6}}<0\)表示B6高配。若所有差值均未
达到注册阈值，则报告注册网格内未检测到实质联合交互。

## 8. 当前门禁

- 本协议已seal，等待独立R4 review；
- 旧v6与四臂v1文件保持不变；
- 新的46-cell implementation、runner和output path尚未绑定；
- grid package、独立review、formal-run authority、formal result和paper claim均为
  false；
- 本方案不改变formal activation V1-V4的历史状态，也不创建formal activation V5。
