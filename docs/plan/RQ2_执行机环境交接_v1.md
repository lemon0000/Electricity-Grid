# RQ2 执行机环境交接 v1（rebuild successor）

本文只登记 Windows 执行机环境依赖闭包的 versioned successor。已冻结的 executor
handoff v2、outer manifest、bundle、runner、科学配置和历史结果保持字节不变。

## 1. 观测到的环境阻塞

执行机按 `environments/rq2_executor_v1.yml` 全新创建环境后，冻结入口在任何
solver call 或结果写入前因缺少 `pypower` 导入失败；继续检查还确认入口的 eager import
依赖 `osqp`。该现象是执行环境依赖闭包不完整，不是数学不可行、模型不可行或求解器
失败证据。

## 2. Successor authority

- 环境规格：`environments/rq2_executor_v2.yml`，SHA-256
  `310b5c2f1261678269cf2e1424255f48582975aec7e492fe029f45cd5e73bdf6`；
- validator：`experiments/validate_rq2_public_executor_environment_successor_v1.py`，
  SHA-256 `405373122cb2299d0930ac552d5ba0dfad08aab864902234bbd43447fe847abc`；
- successor config：`configs/rq2_public_executor_environment_successor_v1.yaml`，
  SHA-256 `22f93851a42882981f2f1183a1cb02251dd23e30576ffdd71c3865dbbeba61e5`；
- successor manifest：
  `configs/rq2_public_executor_environment_successor_v1.SHA256SUMS.json`，SHA-256
  `f5e1ad0c5e85cce64ae3e2b7e66ed9508546a9730d67de111fe1cff051cc76ec`。

v2 只补齐入口实际导入所需的固定版本 `pypower==5.1.19` 与 `osqp==1.0.5`，不修改
冻结 executor、solver/algorithm、threads、seed、threshold、pilot block 或科学口径。

## 3. 执行机重建与验证

从仓库根目录执行：

```powershell
conda env create --prefix "D:\conda_envs\rq2-executor-v2-audit" --file environments\rq2_executor_v2.yml
& "D:\conda_envs\rq2-executor-v2-audit\python.exe" experiments\validate_rq2_public_executor_environment_successor_v1.py --runtime
$env:RQ2_EXECUTION_MACHINE = "EXECUTION_MACHINE_CONFIRMED"
& "D:\conda_envs\rq2-executor-v2-audit\python.exe" scripts\rq2_public_executor.py verify
```

runtime validator 必须精确验证 Python/直接依赖版本并真实 import 冻结入口，同时保持
`solver_calls=0`、`result_files_written=0`。2026-08-27，本机全新 prefix 已通过 runtime
validator、`pip check` 和冻结 executor `verify`；该证据只解除环境重建阻塞。完成 preflight、
four-block pilot、pilot 证据独立 R4 复核和新 activation authority 前，
`formal_execution_ready=false`，不得进入正式 grid/pairwise/identification。
