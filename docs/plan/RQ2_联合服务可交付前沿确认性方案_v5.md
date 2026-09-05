# RQ2 联合服务可交付前沿确认性方案 v5

> 状态：`SEALED_READY_FOR_INDEPENDENT_REVIEW`。当前仅进行科学协议设计与pre-seal验证，
> 不授权implementation、solver、formal run、结果发布或论文claim。

## 1. 权威范围

v5采用完整自包含协议：

1. 机器协议：
   `configs/rq2_joint_deliverability_preregistration_successor_v5.yaml`；
2. 指标规格：
   `docs/model_spec/rq2_joint_deliverability_estimands_v4.md`；
3. 执行顺序：本文件；
4. 历史v1-v4只提供provenance和review evidence，不补充当前科学语义。

## 2. 科学设计

研究保持四臂和46-cell设计：

- `network_only_shared`；
- `cfe_only_shared`；
- `joint_correct_shared`；
- `joint_b6_separate_planning_shared_execution`。

主设计为36个
`hourly_cfe_target × flexible_fraction × normalized_recovery_headroom`
cells，时序OAT增加10个cells。四臂容量通过solver证书区间表示，联合交互和B6
偏差只按区间分类。

## 3. Pre-seal验收矩阵

### 3.1 权威闭包

- v5必须完整包含研究问题、数据、四臂、参数、solver、estimands、holdout、
  transport、bootstrap和claim边界；
- 任一历史字段不得通过遗漏继续成为当前权威；
- top-level和每个科学section使用exact keyset；
- 完整semantic payload使用canonical SHA-256；
- 任一字段、值、列表顺序或嵌套结构变异必须fail closed。

### 3.2 四臂与恢复

- `network-only`只使用业务恢复余量且canonical key排除\(\alpha\)；
- CFE-only和joint-correct使用CFE兼容恢复；
- B6规划使用grid/CFE两套track和恢复余量，执行回到共享track；
- 服务平衡、track mapping、调用/恢复cap、事件、energy和debt方程逐项冻结；
- 共同输入、连接需求、support、代表点、非恢复时序参数和solver不得按arm漂移。

### 3.3 结构性零恢复

- 对全部`arm × track × cell × full training pair`在solver前按eligible recovery
  debt lower bound检查；
- `normalized_recovery_headroom=0`和\(\alpha=1\)均只能作为通用触发条件；
- witness字段完整；
- 触发后无solver、无数值容量、无holdout、无四臂contrast。

### 3.4 容量与归因

- 每个resolved arm输出`[LB,UB]`、incumbent、gap、残差和solver证据；
- `D_single`、`I_joint`、`I_sep`和`A_B6`区间传播公式逐项测试；
- 所有前沿crossing、归因label和claim只读取certified interval；
- 点值加法恒等式残差不超过\(10^{-6}\)；
- positive、negative、near-zero和indeterminate均有合成边界测试。

### 3.5 操作后果与不确定性

- 代表点算法在score并列、quantile重复和质量重分配时确定；
- 输入文件、列名、解析类型和hour-to-block E0 lifting逐项固定；
- holdout state transition只读取当前状态，并以golden trajectory验收；
- 规划、结构门与holdout统一把不超过服务容差的请求映射为0；
- grid、CFE和recovery completion failure分渠道验证；
- E0只进入无条件质量，不进入finite服务风险分子和分母；
- 全部power holdout质量为E0时，finite identification统一为unresolved且不调用
  transport solver；
- transport固定SciPy/HiGHS、LP行列顺序、dual convention、metric顺序和canonical
  serialization；
- operational label量词固定为“存在一个注册指标，其符号对全部允许coupling成立”；
  penalty只读取certified scalar lower endpoint，relief只读取certified scalar upper
  endpoint，existential common-\(\pi\) witness不得支持robust label；
- pre-seal transport probe使用解析primal/dual witness并只做残差复算，validator
  不调用优化器；
- bootstrap固定NumPy 1.26.4、PCG64DXSM、ID顺序、概率、draw顺序、quantile
  method和全局unresolved传播。

### 3.6 对抗性变异

validator测试至少覆盖：

1. 启用network-only CFE call；
2. 修改recovery efficiency；
3. 缩窄全局结构性precheck；
4. 删除maximum recovery debt；
5. 替换bootstrap method或PRNG；
6. 替换transport ambiguity set；
7. 恢复点值frontier crossing；
8. 恢复点值attribution label；
9. 改变E0 denominator；
10. 改变holdout future-information gate；
11. 用某个coupling上的有利符号替代全transport polytope的robust endpoint。
12. duplicate YAML key或布尔值替换为整数；
13. 替换规格正文、保留错误生命周期标题或给manifest增加未知字段。

上述任一变异被接受都不得seal。

## 4. 生命周期

1. 在当前路径迭代`DRAFT_NONAUTHORITATIVE`；
2. 完成validator、targeted tests和相关回归；
3. 由新鲜只读reviewer执行non-authoritative adversarial pre-seal audit；
4. 关闭全部pre-seal findings；
5. 仅进行生命周期切换并生成canonical inner/outer；
6. stable readback后进入`SEALED_READY_FOR_INDEPENDENT_REVIEW`；
7. 使用未参与写入和pre-seal audit的新reviewer审查exact outer；
8. official `PASS`后才允许创建implementation successor。

## 5. 后续实现边界

future implementation至少需要：

- exact 46-cell builder；
- arm/track-specific recovery builder；
- global zero-recovery precheck；
- network-only alpha-invariant certificate reuse；
- four-arm solver certificate和contrast interval；
- deterministic representative selection；
- current-state shared holdout state machine；
- channel-separated service metrics；
- E0、scalar transport endpoint和exact bootstrap；
- v3 output schemas和recursive provenance。

本阶段不启动1071-block grid、46-cell求解或任何正式实验。
