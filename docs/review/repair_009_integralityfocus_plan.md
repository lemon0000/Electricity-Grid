# Repair-009 IntegralityFocus 修复方案

## 一、问题确认

**零改动重跑验证完成**（2026-08-07T19:52Z），候选 6 第 3 轮 `maximum_integrality_violation = 5.0308642940422033e-07`（容差 `1e-8` 的 50.3 倍），与首次观测**逐位相同**。

确认 `Cutoff` × `IntFeasTol` 交互是**确定性系统行为**，`IntegralityFocus: 1` 现在有依据。

---

## 二、修复方案

### 改动清单

1. **修改 `configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml`**
   - `formal_successor` 块加 `solver_options: {IntegralityFocus: 1}`
   - `output.directory` 改为 `results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus`
   - `logging.directory` 改为 `results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus`
   - 修正 `implementation.pilot_module_path`（当前两个 `pilot_*_module_path` 都指向 `_gurobi.py`，前者应指向非 Gurobi 版本）

2. **修改 `experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py`**
   - `_hybrid_candidate` 第 1038 行后加 solver options 覆盖逻辑

### 为什么需要新 output_directory

`input_contract_sha256` 会因为 `solver_options` 变化而改变 → 现有预注册作废 → 必须新预注册 → `prepare_preregistration` 的 434 行要求 `output_root` 为空或不存在 → 必须用新路径。

现有候选 1-5 的检查点留在旧路径，不会被破坏，但也不会被新前沿引用。

---

## 三、成本与时间

| 阶段 | 耗时（实测参考） | 说明 |
|---|---|---|
| 新预注册 `prepare` | ~4.5h | 包含完整的 `_build_context` + manifest 验证 |
| 候选生成预热 | ~4h | `_build_context` + warm-start 构建 |
| 候选 1-4 | 秒级 | 从 repair-007 导入前缀，写到新 output root |
| 候选 5 | ~3h | 从头计算（proxy + cost normalization） |
| 候选 6 | ~2h | proxy + level_set（预期修复后直接合格或进入 cost 阶段） |
| **总计** | **~13.5h** | 单核满载，Gurobi 4 线程 |

---

## 四、预期结果

### 如果 `IntegralityFocus: 1` 修复生效

候选 6 第 3 轮的 `maximum_integrality_violation` 降至 `<= 1e-8`：
- `adapter:217` 闸门放行
- `snapshot_normalization` 非 null
- `incumbent_usable = True`
- 候选 6 进入 eligibility 判定或直接合格
- 前沿发布，包含候选 1-6

### 如果修复未生效

候选 6 仍然失败，但我们获得了：
- 确认 `IntegralityFocus: 1` 对这个问题无效
- 排除了一个假设，缩小了问题空间
- 可以尝试其他 Gurobi 参数（`Presolve: 0`, `Method: 2` 等）或调整容差

---

## 五、实施步骤

### 步骤 1：应用代码改动

见下节的具体 patch。

### 步骤 2：新预注册

```powershell
$env:PYTHONUNBUFFERED = "1"
& "D:\conda_envs\compute\python.exe" `
  "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py" `
  --config "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml" `
  --stage prepare `
  | Tee-Object -FilePath "repair_009_ifocus_prepare.log"
```

预期完成时间：~4.5h（参考本轮 prepare 耗时）

验证点：
- `results/tables/.../repair_009_ifocus/preregistration/registration.json` 已发布
- `input_contract.formal_successor.solver_options.IntegralityFocus = 1`
- `input_contract_sha256` 与旧预注册不同

### 步骤 3：候选生成

```powershell
$env:PYTHONUNBUFFERED = "1"
& "D:\conda_envs\compute\python.exe" `
  "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py" `
  --config "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml" `
  --stage generate-candidates `
  | Tee-Object -FilePath "repair_009_ifocus_generate.log"
```

预期完成时间：~9h（预热 4h + 候选 1-4 秒级 + 候选 5 3h + 候选 6 2h）

关键判决点：候选 6 第 3 轮 `maximum_integrality_violation` vs `1e-8`

---

## 六、验证方式

### 成功标志

1. `results/tables/.../repair_009_ifocus/candidate_frontier/SHA256SUMS` 存在
2. `candidate_frontier/summary.json` 包含 6 个候选
3. 候选 6 的 `progress.jsonl` 最后事件是 `frontier_published`，不是 `candidate_failed`

### 失败标志

1. `candidate_failed` 事件，`error_message = "strict_cost_separation_not_proven"`
2. 候选 6 第 3 轮 `maximum_integrality_violation` 仍 `> 1e-8`

### 后续决策树

```
候选 6 成功？
├─ 是 → 发布前沿，进入 joint-ac 阶段
└─ 否 → 分析失败原因
       ├─ 违约值仍 5.03e-07 → IntegralityFocus 无效，尝试其他参数
       ├─ 违约值变化但仍 > 1e-8 → 部分改善，调整参数强度
       └─ 新错误 → 根据错误类型决定
```

---

## 七、回滚方案

如果需要回到旧状态：

1. **代码回滚**：`git checkout <commit>` 恢复 config 和 runner
2. **旧检查点保留**：旧 `output_root` 下的候选 1-5 检查点未被修改
3. **新路径独立**：新 `output_root` 与旧路径隔离，互不影响

---

## 八、风险与限制

1. **13.5 小时成本**：无法缩短，预热和候选 5-6 计算是必需的
2. **候选 1-5 不复用**：旧检查点在新 input contract 下不可用
3. **修复不保证成功**：`IntegralityFocus: 1` 是基于 Gurobi 文档的合理尝试，但不保证解决问题

---

## 九、后续优化空间

如果本次修复成功，可以考虑：

1. **调整容差**：`1e-8` 是否过于严格？Gurobi 的 `IntFeasTol` 默认 `1e-5`
2. **记录配置**：将这个 solver override 机制文档化，方便未来调参
3. **候选 1-4 也用 Gurobi**：当前候选 1-4 的 physics 验证仍用 HiGHS，是否需要统一？

---

**准备好了吗？我现在写具体的代码 patch。**
