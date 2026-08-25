# RQ2执行机交接 v1

## 1. 研究问题与科学价值

执行机只生成RQ2 v6的cross-solver pilot和正式数值证据。容量指标是
`normalized minimum flexibility underprovisioning`，不是接入容量$X$。

## 2. 研究设计与因果逻辑

执行顺序固定为`preflight -> pilot -> grid -> pairwise -> identification`。
后两阶段必须读取并验证上一阶段的完整manifest和provenance后才能激活。
v3 HiGHS checkpoint只作历史诊断证据，不得复制到v4 Gurobi目录，也不得
正式resume。其v5 manifest记录的旧`formulation.md`字节已不可恢复，故这些
checkpoint不是执行机bundle依赖或正式可复验证据。

## 3. 方法与统计推断

环境由`environments/rq2_executor_v1.yml`固定。四块pilot包括：

- ordinary：`holdout_s20260822_0013`
- congested：`holdout_s20260822_0091`
- generator E0：`holdout_s20260822_0089`
- branch E0：`holdout_s20260822_0150`

HiGHS/Gurobi各重复两次。Gurobi只有在状态、incumbent/bound、residual、模型
规模、finite grid need与E0分类全部一致时才可进入正式successor；wall time
只用于性能比较。

## 4. 结果解释与外推边界

pilot不是正式RQ2结果。E0只证明冻结selected-N-1 DC benchmark在零数据中心
端点仍不可行，不是工程系统不可行。正式transport结果条件于finite-grid
support，并单列无条件E0质量。

## 5. 学术写作与叙事

执行机产物只提供机器证据，不直接修改论文结论。最终claim由开发机在回传后
根据manifest、sharpness与状态审计确定。

## 6. 审查风险与失败模式

- `timeout`、缺incumbent或ambiguous termination不得解释为不可行。
- pilot失败时不得把Gurobi写入正式activated config。
- 任一output/checkpoint目录已存在但身份不一致时停止，不覆盖。
- `RQ2_EXECUTION_MACHINE`缺失或hostname命中开发机黑名单时停止。
- 当前activation文件仍为false；在pilot回传并完成R4复核前，正式命令会失败。

## 7. 执行命令

创建环境：

```bash
conda env create -f environments/rq2_executor_v1.yml
```

静态核验、runtime preflight和pilot：

```bash
conda run -n rq2-executor python scripts/rq2_public_executor.py verify
export RQ2_EXECUTION_MACHINE=EXECUTION_MACHINE_CONFIRMED
conda run -n rq2-executor python scripts/rq2_public_executor.py preflight
conda run -n rq2-executor python scripts/rq2_public_executor.py pilot
conda run -n rq2-executor python scripts/rq2_public_executor.py package-pilot
```

Windows PowerShell设置执行机标记：

```powershell
$env:RQ2_EXECUTION_MACHINE = "EXECUTION_MACHINE_CONFIRMED"
```

pilot包回传开发机并完成审查后，更新并重新验签
`configs/rq2_public_successor_activation_v1.yaml`，再依次执行：

```bash
conda run -n rq2-executor python scripts/rq2_public_executor.py activate-grid
conda run -n rq2-executor python scripts/rq2_public_executor.py grid
conda run -n rq2-executor python scripts/rq2_public_executor.py activate-pairwise
conda run -n rq2-executor python scripts/rq2_public_executor.py pairwise
conda run -n rq2-executor python scripts/rq2_public_executor.py activate-identification
conda run -n rq2-executor python scripts/rq2_public_executor.py identification
conda run -n rq2-executor python scripts/rq2_public_executor.py package-results
```

`grid`与`pairwise`中断后分别使用`resume-grid`和`resume-pairwise`；两者复用的
仅是同一activated config绑定的新v4 Gurobi checkpoint。
