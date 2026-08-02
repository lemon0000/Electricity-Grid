# Datadog 监控接入说明

## 前提

- Datadog Agent 已安装并运行（http://localhost:5002 可访问）
- 账号处于试用期（告警 Monitor 可用）

---

## 第一步：以管理员 PowerShell 执行（一次性）

### 1a. 开启日志采集

打开 **管理员 PowerShell**，运行：

```powershell
# 开启 logs_enabled
$cfg = "C:\ProgramData\Datadog\datadog.yaml"
$content = Get-Content $cfg -Raw
if ($content -notmatch "^logs_enabled:\s*true") {
    Add-Content $cfg "`nlogs_enabled: true"
    Write-Host "logs_enabled: true appended"
} else {
    Write-Host "logs_enabled already true"
}
```

### 1b. 复制日志采集配置

```powershell
New-Item -ItemType Directory -Force `
    "C:\ProgramData\Datadog\conf.d\electricity_grid.d"

Copy-Item `
    "D:\CUHKSZ\Research Project\electricity-grid\configs\datadog\conf.d\electricity_grid.d\conf.yaml" `
    "C:\ProgramData\Datadog\conf.d\electricity_grid.d\conf.yaml"
```

### 1c. 重启 Agent

```powershell
Restart-Service -Name "datadogagent"
Start-Sleep -Seconds 5
& "C:\Program Files\Datadog\Datadog Agent\bin\agent.exe" status 2>&1 |
    Select-String "electricity|Logs Agent|log_file"
```

日志接入成功时，`agent status` 输出里能看到 `electricity_grid` 的 check 条目。

---

## 第二步：在 Datadog UI 创建告警 Monitor

### 2a. Dead-man's switch（heartbeat 消失告警）——最重要

1. 进入 **Monitors → New Monitor → Logs**
2. **Search query**: `service:electricity-grid @event:heartbeat`
3. **Alert condition**: count `< 1` over the last **5 minutes**
4. **Message**（填入邮件地址）:
   ```
   MIP solver heartbeat missing for 5+ minutes.
   repair run may have crashed silently (like repair-008 on 2026-07-30).
   Check: python -m experiments.push_datadog_progress --log-root results\logs\...
   ```
5. **Save**

这条 Monitor 会在进程静默死亡后 5 分钟内触发，正好对应你 `repair-008` 的问题。

### 2b. Gap 停滞告警（可选）

1. **Monitors → New Monitor → Metric**
2. **Metric**: `mip.solver.relative_gap_pct`
3. **Alert**: `change(avg, 2h) >= 0`（2 小时内 gap 无改善）
4. **Message**: `Gap has not improved in 2 hours — solver may be stuck.`

---

## 第三步：启动指标推送（每次求解时运行）

在第二个终端（普通权限即可）：

```powershell
cd "D:\CUHKSZ\Research Project\electricity-grid"
conda activate compute
python -m experiments.push_datadog_progress `
    --log-root results\logs\rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009
```

脚本每 30 秒轮询一次 `build_status()`，将 gap/incumbent/nodes/elapsed 推到 DogStatsD（本地 UDP，无需 API key），求解结束后自动退出。

---

## 推送的指标

| 指标名 | 含义 |
|---|---|
| `mip.solver.relative_gap_pct` | 当前相对 gap |
| `mip.solver.absolute_gap` | 绝对 gap |
| `mip.solver.incumbent` | 当前最优可行解目标值 |
| `mip.solver.lower_bound` | 对偶下界 |
| `mip.solver.nodes` | B&B 节点数 |
| `mip.solver.elapsed_seconds` | 累计求解时间（秒） |
| `mip.solver.completed_candidates` | 已完成候选数 |
| `mip.solver.requested_candidates` | 预算候选总数 |

附带标签：`experiment:repair_009`、`status:running/stale/...`、`current_candidate:<name>`

**基数说明**：约 8 指标名 × 6 候选 × 3 状态值 = 约 20–30 个时间序列，远低于 Pro 每主机 100 个配额。
不要把 `run_id`（`formal_repair_009_...`）加进指标 tag——会随运行次数无限增长。
日志里的 `run_id` 是可搜索属性，无基数风险。
