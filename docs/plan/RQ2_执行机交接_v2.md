# RQ2 执行机交接 v2（Windows successor）

本文是执行机交接 v1 的仅执行层 successor。v1、RQ2 v6 preregistration、旧
outer manifest、旧 executor bundle 和历史 checkpoint 全部保持字节不变；本文不修改
estimand、solver 选择、pilot block、阈值或 activation 状态。

## 1. 当前授权边界

执行机当前只允许完成非正式 four-block cross-solver pilot：

```text
verify -> preflight -> pilot -> package-pilot
```

`rq2-public-pilot` 标签入口不接受任意 command，不能触达 `activate-grid`、`grid`、
`pairwise`、`identification`、它们的 resume 命令或 `package-results`。pilot 包回传并
完成独立 R4 复核前，`formal_execution_ready=false`，所有正式 activation 继续关闭。

v2 权威链是非循环的 `outer manifest -> v2 bundle -> handoff/H2 successor/runner`。
runner 必须先以 outer manifest 验证整个 v2 bundle 的 SHA-256，才可信任 bundle 内逐项
inventory/hash；handoff 只记录 outer 的路径而不反向记录 outer hash，避免哈希循环。

## 2. Windows 路径 successor

旧冻结测试有两处使用 `str(Path(...))` 构造 expected manifest key。在 Windows 上该
字符串使用反斜杠，而冻结 manifest 的权威 key 是 repository-relative POSIX 路径，
因此旧测试会产生两个平台性假失败。旧测试已被旧 bundle 锁定，不能改写。

v2 的处置是：

1. 先验证旧测试 SHA-256 仍为
   `f7a8ad71712c2ec731119ce02649c1c1dc2379f190d40238aed001da610edc47`；
2. 仅在 `win32` 对两个精确 nodeid 作 `strict xfail`；旧文件或 nodeid 漂移都会失败；
3. 由 `src/evaluation/repository_paths.py` 与 v2 tests 以 POSIX relative path 重新执行
   完整 inventory/hash 门；
4. 禁止全局 `Path` monkeypatch、静默 ignore 或重签旧 manifest。

冻结 executor 的 `package-pilot` receipt 还使用
`str(Path.relative_to(...))`：Windows 会输出反斜杠，而 transfer manifest 内仍是 POSIX
key。v2 runner 只对 receipt 的 `archive`/`manifest` 字段接受原生分隔符，并先拒绝
absolute、drive-relative、UNC、空段与 `.`/`..` traversal，再归一为 repository-relative
POSIX 路径做大小写敏感的注册路径比较。该兼容层不改变冻结 executor 或 transfer
manifest 的权威格式；合成 Windows 测试同时覆盖原生 receipt 成功和恶意路径 fail closed。

旧H2 temporal preregistration v1还冻结了共享`run_experiment.ps1`的旧SHA。v2不重签
该preregistration或其manifest，而以
`configs/rq2_h2_temporal_executor_entry_successor_v2.yaml`记录唯一变化为标签执行入口；
threshold、seed、sample size、模型/solver语义和既有结果均不变。旧validator test只在
前置执行精确得到`executor_script_sha256 mismatch`后strict-xfail；任何其他失败都会使
collection报错。新的versioned validator先锁旧preregistration/manifest/validator/test
哈希，再用successor manifest替换唯一executor binding，完整重放旧validator的17-job、
threshold、seed、sample size、honesty和gate语义。

## 3. run-* 标签入口

分支 HEAD 的 `configs/experiment.yaml` 继续保持 `kind: pytest-smoke`。只有未来专门的
标签 commit 可以把它改成：

```yaml
experiment:
  kind: rq2-public-pilot
```

家里执行机必须先创建 `environments/rq2_executor_v1.yml` 指定的环境，再在本机配置中
显式注入该环境的绝对 Python 路径，例如：

```powershell
$env:RQ2_EXECUTOR_PYTHON_EXE = "D:\conda_envs\rq2-executor\python.exe"
$env:RQ2_PILOT_TIMEOUT_SECONDS = "21600"
$env:RQ2_EXECUTION_MACHINE = "EXECUTION_MACHINE_CONFIRMED"
```

`RQ2_EXECUTOR_PYTHON_EXE` 必须是绝对的普通文件，不能回退到 `PYTHON_EXE`、`compute`
环境或 PATH。poller 现有的 `SMOKE_TIMEOUT_SECONDS=7200` 只影响 smoke/formal-batch；
pilot 使用独立的 `RQ2_PILOT_TIMEOUT_SECONDS`，缺省和允许的最小值均为 21600 秒。
timeout 后必须执行 `Kill -> bounded WaitForExit -> Refresh -> HasExited` 并证明child退出；
无法证明时状态为failed且禁止成功工件验证。timeout只记执行超时，不是数学不可行证据。

## 4. 回传工件与失败语义

入口递归复制下列工件到 `RUN_ARTIFACT_DIR/rq2_public_pilot/`：

- `preflight/` 及其 `SHA256SUMS.json`；
- `pilot/`、comparison、runs、summary 及其 `SHA256SUMS.json`；
- `transfer/rq2_public_successor_v1_pilot.tar.gz`；
- `transfer/rq2_public_successor_v1_pilot.json`；
- 四个命令的 stdout/stderr 共8个日志；每个都必须是非reparse普通文件。

入口会先安全归一化冻结 executor 的原生 separator receipt，再验证注册路径、源包、
transfer manifest、archive hash 和复制后哈希。
即使四个子进程均退出 0，只要完整工件不能证明，顶层状态仍为 `failed`。
四阶段未完整成功时只复制诊断日志；成功路径还会逐项重验8个日志复制前后的SHA-256。
`metrics.json` 固定保留 `formal_execution_ready=false` 与
`security_certified=false`；pilot 是否使 Gurobi eligible 只作回传字段，不自动激活。

## 5. 当前状态

- Windows successor 与标签入口：已实现，尚未由执行机运行；
- `rq2-executor` 环境、license/Pyomo preflight：尚未取得执行机 receipt；
- cross-solver pilot：尚未运行；
- HiGHS同进程thread scheduler污染：R3 residual，尚未完成隔离诊断；
- grid/pairwise/identification：全部关闭；
- formal result：不存在。
