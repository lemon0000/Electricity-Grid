# Repair-009 IntegralityFocus 修复 - 完整方案总结

## 改动说明

### 1. Config 改动 (`configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml`)

- **添加 `solver_options` 字段**：在 `formal_successor` 块中加入 `IntegralityFocus: 1`
- **修正 `pilot_module_path`**：从 `pilot_..._gurobi.py` 改回 `pilot_....py`（之前记录错误）
- **新 output 路径**：`repair_009_ifocus` 后缀，避免与旧 output root 冲突

### 2. Runner 改动 (`experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py`)

在第 1038 行后添加 solver options 覆盖逻辑：
```python
if "solver_options" in _succ_cfg:
    context.config["formal_solver"]["solver"]["options"] = dict(_succ_cfg["solver_options"])
```

这个覆盖只在 `_hybrid_candidate`（候选 5-6）内生效，候选 1-4 走 `_prefix_candidate` 不受影响。

## 执行步骤

### 步骤 1: 预注册（~4.5 小时）

```powershell
.\scripts\run_repair_009_ifocus_prepare.ps1
```

**预期输出**：
- `results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus/preregistration/registration.json` 发布
- `input_contract.formal_successor.solver_options.IntegralityFocus = 1`
- `input_contract_sha256` 与旧预注册不同（因为 config 改了）

### 步骤 2: 候选生成（~9 小时）

```powershell
.\scripts\run_repair_009_ifocus_generate.ps1
```

**预期输出**：
- 候选 1-4：从 repair-007 导入前缀（秒级）
- 候选 5：direct_then_cost_decision_bisection（~3 小时）
- 候选 6：direct_then_cost_decision_bisection，proxy + level_set（~2 小时）
- `results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus/candidate_frontier/SHA256SUMS` 发布

## 预期结果

### 如果 IntegralityFocus=1 修复了问题

候选 6 level_set 第 3 轮：
- `maximum_integrality_violation` ≤ 1e-8（通过）
- `snapshot_normalization` 和 `snapshot_normalization_error` 非 null
- `incumbent_usable = True`
- 候选 6 成功完成，出现在前沿

### 如果 IntegralityFocus=1 不足以修复

候选 6 level_set 第 3 轮：
- `maximum_integrality_violation` 仍 > 1e-8（如仍是 5.03e-07）
- 候选 6 失败，前沿只包含候选 1-5

## 验证方式

### 方法 1：查看前沿

```powershell
cat results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus/candidate_frontier/SHA256SUMS
```

如果包含 `candidate_00006.json`，说明候选 6 成功。

### 方法 2：查看 progress.jsonl

```powershell
$LOG_DIR = Get-ChildItem "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus" -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
cat "$($LOG_DIR.FullName)/progress.jsonl" | Select-String "maximum_integrality_violation" | Select-String -Pattern "[^0]e-0[0-9]" | Select-Object -Last 5
```

找候选 6 level_set 第 3 轮的违约值，看是否 ≤ 1e-8。

### 方法 3：用 monitor 工具

```powershell
python experiments/monitor_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009.py
```

实时监控候选生成进度和违约判决。

## 成本总结

| 阶段 | 耗时 | 说明 |
|---|---|---|
| 预注册 | ~4.5h | `_build_context` + 预注册发布 |
| 预热 | ~4h | warm-start 构建 |
| 候选 1-4 | 秒级 | 从 repair-007 导入前缀 |
| 候选 5 | ~3h | direct + bisection |
| 候选 6 | ~2h | direct + proxy + level_set |
| **总计** | **~13.5h** | 一次完整运行 |

旧 output root (`repair_009`) 的候选 1-5 检查点不会被破坏，但新前沿不会引用它们。

## 如果修复不成功的后续方案

1. **提高 IntegralityFocus**：改为 `IntegralityFocus: 2` 或更高（Gurobi 上限不明确）
2. **调整 Cutoff**：在 level_set 的 decision MIP 中禁用 Cutoff（需修改 adapter）
3. **放宽容差**：将 `1e-8` 改为 `1e-6`（科学上不推荐，最后手段）

## 监控命令（可选）

在另一个终端实时监控：

```powershell
# 监控进程
while ($true) { Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB } | Format-Table Id,CPU,WS -AutoSize; Start-Sleep 30 }

# 监控 progress.jsonl 大小
while ($true) { $f = Get-ChildItem "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus" -Recurse -Filter "progress.jsonl" -ErrorAction SilentlyContinue | Select-Object -First 1; if ($f) { Write-Host "$(Get-Date -Format 'HH:mm:ss') progress.jsonl = $($f.Length) B" }; Start-Sleep 60 }
```

## 文件清单

- `configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml` (已修改)
- `experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py` (已修改)
- `scripts/run_repair_009_ifocus_prepare.ps1` (新建)
- `scripts/run_repair_009_ifocus_generate.ps1` (新建)
- `docs/repair_009_ifocus_plan.md` (本文件)

---

**准备好后执行**：

```powershell
# 步骤 1
.\scripts\run_repair_009_ifocus_prepare.ps1

# 等待 ~4.5 小时后，步骤 2
.\scripts\run_repair_009_ifocus_generate.ps1
```
