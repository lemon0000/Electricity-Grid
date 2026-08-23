# RQ2 Temporal H2 17-Job 执行机运行流程

## 1. 本次运行身份

本次正式实验只能使用以下不可变标签：

```text
run tag: run-20260823-001
trigger commit: d68bc85ee728ae4dca6d6e9790658d59dccac207
source branch: experiment
result branch: experiment-results
batch config: configs/rq2_h2_temporal_successor_batch_v1.yaml
```

当前 `experiment` 分支 HEAD 已恢复为 `pytest-smoke`。执行机不得直接运行当前
`experiment` HEAD；必须运行标签 `run-20260823-001` 指向的 commit。

本批包含 17 个预注册 job，使用 HiGHS。所有结果均为 trace-derived/synthetic
机制证据，保持：

```text
security_certified=false
formal_vma_published=false
```

## 2. 执行前环境检查

以下示例假定主仓库位于：

```text
D:\research\Electricity-Grid
```

若实际路径不同，只替换该路径，不修改仓库内配置。

打开 PowerShell：

```powershell
cd D:\research\Electricity-Grid

git fetch origin --tags --prune
git status
git show-ref --verify refs/tags/run-20260823-001
git rev-parse "run-20260823-001^{}"
```

最后一条必须精确输出：

```text
d68bc85ee728ae4dca6d6e9790658d59dccac207
```

核对标签内的触发配置：

```powershell
git show "run-20260823-001:configs/experiment.yaml"
```

必须包含：

```yaml
kind: rq2-formal-batch
batch_config: configs/rq2_h2_temporal_successor_batch_v1.yaml
```

若 commit 或配置不一致，停止运行，不要自行修正标签或 YAML。

## 3. Conda 环境检查

```powershell
conda activate compute

python --version
python -c "import pyomo, highspy, yaml; print('environment ok')"
python -c "import highspy; print(highspy.Highs().version())"
```

本批冻结使用 HiGHS，不需要 Gurobi。不得临时更换 solver，也不要创建 venv。

## 4. 推荐方式：执行既有轮询器

若执行机已经配置跨机轮询，只运行既有固定入口：

```powershell
powershell -ExecutionPolicy Bypass `
  -File D:\research\agent\run-pending-experiment.ps1
```

轮询器应自动完成：

```text
发现 run-20260823-001
→ 校验标签和 commit
→ 从标签创建独立 worktree
→ 设置 RUN_ID / RUN_TAG / RUN_COMMIT / RUN_DIR / RUN_ARTIFACT_DIR
→ 调用标签 worktree 内的 scripts\run_experiment.ps1
→ 执行 17-job batch
→ 将完整工件提交到 experiment-results
```

不要在轮询器运行期间手动启动第二个相同批次。

## 5. 仅做读取检查，不手工改配置

执行开始后，可在另一个 PowerShell 窗口检查进程：

```powershell
Get-CimInstance Win32_Process |
  Where-Object {
    $_.CommandLine -match "run_rq2_formal_batch|run_rq2_h2_temporal"
  } |
  Select-Object ProcessId, CreationDate, CommandLine
```

检查运行目录：

```powershell
Get-ChildItem D:\research\runs -Directory |
  Where-Object { $_.Name -eq "run-20260823-001" }
```

检查日志尾部：

```powershell
Get-Content `
  D:\research\runs\run-20260823-001\experiment.log `
  -Tail 80
```

实际目录以 `D:\research\agent\experiment-config.ps1` 中的配置为准。

## 6. 不推荐的手工兜底

只有在轮询器未配置或明确故障时，才按
`docs/plan/科研实验闭环流程.md` 的执行器合同人工建立独立 worktree，并设置全部
环境变量后调用：

```powershell
scripts\run_experiment.ps1
```

不要执行以下命令作为替代：

```powershell
git switch experiment
python -m experiments.run_rq2_formal_batch
```

原因是当前 `experiment` HEAD 已恢复为 smoke 默认；直接运行 runner 还会绕过标签身份、
结果目录、上传 manifest 和失败状态记录。

若必须人工兜底，至少先验证：

```powershell
git fetch origin --tags --prune
git worktree add --detach `
  D:\research\runs\run-20260823-001-worktree `
  "run-20260823-001^{}"

cd D:\research\runs\run-20260823-001-worktree
git rev-parse HEAD
```

`HEAD` 必须为：

```text
d68bc85ee728ae4dca6d6e9790658d59dccac207
```

环境变量、结果目录、artifact 目录和结果上传仍必须由既有执行器合同提供。不要只运行
Python runner 后人工拼装结果。

## 7. 成功运行应产生的工件

执行机应向 `experiment-results` 分支发布：

```text
results/
└── run-20260823-001/
    ├── status.json
    ├── status.txt
    ├── metrics.json
    ├── summary.md
    ├── run-info.txt
    ├── manifest.json
    ├── batch_manifest.json
    └── batch_results/
```

`batch_results/` 中必须包含 17 个 job 的完整目录。每个 temporal job 至少应保存：

```text
effective_config.yaml
arms.csv
leaves.csv
summary.json
SHA256SUMS.json
```

执行器顶层 `manifest.json` 必须递归记录 `batch_results/` 内每个文件的相对路径、
字节数和 SHA-256。

## 8. 运行完成后的检查

```powershell
cd D:\research\Electricity-Grid
git fetch origin experiment-results

git show `
  origin/experiment-results:results/run-20260823-001/status.json

git show `
  origin/experiment-results:results/run-20260823-001/metrics.json

git show `
  origin/experiment-results:results/run-20260823-001/summary.md
```

成功的运行状态至少应满足：

```text
status=success
job_count=17
batch_gate_passed=true
security_certified=false
```

`batch_gate_passed=true` 只表示 17 个 job 的计算和正确性门通过，不表示 H2 成立，
也不表示工程、安全或合同认证。

## 9. 失败与超时处置

失败或超时也必须上传：

```text
status.json
metrics.json
summary.md
run-info.txt
manifest.json
error.txt
已有的 batch 工件
```

禁止：

- 删除、移动或强制覆盖 `run-20260823-001` 标签；
- 修改冻结 YAML 后继续使用同一标签；
- 手动删除阴性、unresolved 或失败 job；
- 将 timeout、missing incumbent 或 unresolved 解释为数学不可行；
- 在同一运行目录中直接重启或覆盖结果；
- 把结果提交到 `experiment` 分支。

需要重试时，先保留原失败工件并完成诊断。任何重试必须使用新 trigger commit 和新标签，
例如：

```text
run-20260823-001-r2
```

新标签仍需用户明确授权，不得由执行机自行创建。

## 10. 本次执行机只需要做什么

正常情况下只有三步：

```powershell
cd D:\research\Electricity-Grid
git fetch origin --tags --prune
conda activate compute
powershell -ExecutionPolicy Bypass `
  -File D:\research\agent\run-pending-experiment.ps1
```

随后保持轮询器运行并等待结果上传。不要拉取当前 `experiment` HEAD 来替代标签运行，
也不要修改模型、阈值、种子或 solver。
