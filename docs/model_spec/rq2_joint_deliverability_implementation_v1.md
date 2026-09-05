# RQ2 联合服务可交付前沿 reference implementation v1

## 1. 文档地位

本文件说明
`configs/rq2_joint_deliverability_preregistration_successor_v5.yaml`
的 reference implementation。科学定义仍以 sealed V5 outer、inner、配置、
estimand 规格和 R4 PASS receipt 为准。

本实现属于 R3，当前只提供可测试的内存执行路径和输出发布原语，不授权正式
46-cell 求解、1071-block grid、holdout、transport、bootstrap 或论文结论。

## 2. 模块边界

### 2.1 场景层

`src/scenarios/rq2_joint_deliverability.py`负责：

1. 严格解析 training/holdout 边缘和 24 小时 block；
2. 将任一小时 E0 提升为完整 power block E0；
3. 展开 36 个主因子和 10 个 OAT cells；
4. 构造 target-specific raw/effective CFE 请求；
5. 构造 business 与 CFE-compatible recovery headroom；
6. 选择 training-only 8×8 representatives；
7. 生成全 training support 的结构性恢复 witness。

### 2.2 模型层

`src/models/rq2_joint_deliverability.py`负责：

1. 构造四臂 Pyomo planning model；
2. 对 shared 或 B6 双 track 应用事件、能量和恢复债务约束；
3. 审计固定 minimum-request trajectory；
4. 调用注册 solver 并输出完整 bound、gap、residual 和状态证书。

grid-active arms 的固定 minimum-request trajectory 失败不是不可行证明，因为
`x_grid`允许超过最低请求。此时 full-support audit 必须回退到 exact MILP。

### 2.3 评估层

`src/evaluation/rq2_joint_deliverability.py`负责：

1. 将 solver 与 full-support 证据归一为 fail-closed capacity status；
2. 传播四臂容量区间并计算有符号归因；
3. 执行 current-state-only、grid-first holdout policy；
4. 分离 E0 与 finite service denominator；
5. 用 sparse HiGHS dual simplex 计算 scalar transport endpoints；
6. 按 PCG64DXSM 固定流重算 bootstrap endpoints；
7. 验证 nested output、provenance、typed tree 和发布提交。

### 2.4 Runner 与 validator

`experiments/run_rq2_joint_deliverability_implementation_v1.py`编排内存阶段。
canonical 只读入口为：

```bash
OMP_NUM_THREADS=1 python -m \
  experiments.run_rq2_joint_deliverability_implementation_v1 --validate-only
```

`experiments/validate_rq2_joint_deliverability_implementation_v1.py`只做静态、
hash、schema 和 AST 检查，不导入优化运行时、不调用 solver、不写结果。

## 3. 数据流

### 3.1 Capacity

1. 在 conditioning 前拒绝任一非 `training` block。
2. power 侧分离 E0，并仅对 finite mass 重新归一化。
3. training-only 选择 8 个 power 和 8 个 workload representatives。
4. 对每个 arm-cell 先扫描完整 finite Cartesian support 的结构恢复下界。
5. 未触发结构门时求 representative candidate。
6. 对完整 support 执行固定轨迹审计；grid-active 反例进入 exact MILP fallback。
7. full-support 未通过时禁止增加容量或重选代表点。

network-only 的 canonical planning key排除 `alpha`，但绑定 raw/effective grid
请求、业务 headroom、其他 cell 参数及完整 solver specification。

### 3.2 Holdout

只有四臂均为 `resolved` 且每臂 `full_support_audit.status=passed` 的 cell
可执行。runner 传入 raw 请求，policy 在单一位置按
`request <= 1e-6 -> 0`生成 effective 请求，并同时保留 raw/effective 审计字段。

每小时只读取当前请求、当前 headroom 和上一小时状态。最后一小时强制 inactive；
终端债务不清零时记录 recovery completion failure，不将其改写为 infeasible。
B6 planning 容量在 holdout 中回到 shared physical state。

### 3.3 Identification

E0 只进入无条件质量，不进入 finite 分子或分母。finite power 边缘重新归一化后，
与完整 workload 边缘形成 transport polytope。每个注册 metric 独立计算 lower
和 upper endpoint；一个 endpoint 失败时仍实际尝试另一个。

发布校验从 pair-level metrics 和边缘概率重建 sparse equality system，重新计算
primal objective、dual objective、marginal residual、dual feasibility residual
和向量维度。operational label只读取各 scalar metric 的 certified endpoints。

bootstrap 每个 replicate 重新抽取两侧边缘并重新求全部注册 endpoints；任一
replicate 无 finite mass 或 endpoint unresolved 时全局 fail closed。

## 4. 状态与证书

capacity arm 只允许：

1. `resolved`：solver status 为 `ok`，bound/gap/residual 满足注册阈值，且完整
   training support 通过；
2. `structural_recovery_infeasible_estimand_undefined`：有可复算债务恒等式 witness，
   无 solver 数值；
3. `training_support_failure_estimand_undefined`：representative candidate 可行，
   但完整 support 失败；
4. `proven_infeasible_at_registered_cap_estimand_undefined`：仅接受注册
   infeasible termination/status 对，全部数值结果字段为 null；
5. `unresolved`：timeout、缺 incumbent/bound、数值审计失败或 fallback 未解析。

任何 undefined/unresolved 状态都不填补容量点值。四臂未全部 resolved 时，不生成
有符号容量 contrast；holdout 或 transport 未解析时，不生成 operational label。

## 5. 输出与原子发布

输出固定为：

1. `capacity_frontier.json`
2. `holdout.json`
3. `identification.json`
4. `report.json`
5. `provenance.json`

发布前重算所有 nested identities、solver binding、计数、frontier summary、
transport 证书、report digest 和 live provenance。结果目录使用 exact typed-tree
manifest；额外文件、目录、symlink 或 reparse point 均拒绝。

发布先原子提交 result directory，再原子提交独立
`<result>.PUBLISHED/success.json`。result 已出现但无法证明 result/success 一致时，
状态为 `commit_indeterminate`，不得清理或重试为另一结论。

该 publisher 只发布 `formal_result=false` 的 reference payload。它验证调用者给定
authority 对应的 live bytes，但不自行建立 trust root；也不从 native solver
solution、被省略的 holdout trajectory 或 bootstrap replicate endpoints 独立重放
全部数值结果。因此它不能被正式 execution successor 直接当作最终证据发布器。

## 6. 规模与复杂度

注册规模上界为：

| 项目 | 数量 |
|---|---:|
| arm outputs | 184 |
| representative planning tasks | 157 |
| point transport endpoint solves | 2,116 |
| bootstrap endpoint solves | 423,200 |
| holdout policy executions | 3,315,680 |
| hourly state transitions | 79,576,320 |

单次 holdout policy 对时长 \(T\) 为 \(O(T)\)。一个 \(m\times n\) transport
endpoint 使用 \(mn\) 个变量和 \(m+n-1\) 条独立等式，并以 sparse matrix
构造。总运行时间主要由 planning MILP 和 bootstrap LP 数量决定，不是单次状态
转移。

## 7. 正式执行前 blocker

当前实现不能直接升级为正式 runner。至少还需：

1. streaming holdout persistence；
2. cell/metric 级 resumable bootstrap checkpoints；
3. 注册维度下的 bounded-memory profile；
4. transport runtime 实测投影；
5. 绑定正式路径、activation authority、lease 和 execution provenance；
6. 递归核验注册 input manifests、`541/530/34/34` 数量及跨 split 不相交；
7. 保存 native solver evidence，并从 primal solution 独立重算约束残差；
8. 保存可内容寻址的 holdout trajectory chunks，并从轨迹重算 metrics；
9. 保存 bootstrap draw-stream hash 与 replicate endpoints，或独立完整重算；
10. 从 sealed scientific/implementation outer 和 input manifests 内部派生
    provenance authority，不接受调用者注入 trust root；
11. 独立 R3 execution-successor review；
12. 可用且通过容量与版本门的 Gurobi 13.0.2 环境。

这些 blocker 只表示正式工程执行尚未就绪，不表示模型不可行。

## 8. 验证口径

pre-seal 最低验证包括：

1. focused implementation suite；
2. V1-V5 preregistration、legacy four-arm、public replay 和 identification 回归；
3. Ruff check/format；
4. validator 与 module `--validate-only`；
5. sealed holdout hash、bootstrap RNG hash 和 transport primal/dual oracle；
6. malformed certificate、split leakage、nested output 与 publication fault injection；
7. 新鲜只读 pre-seal adversarial audit；
8. sealed outer 发布后的全新 independent R3 review。
