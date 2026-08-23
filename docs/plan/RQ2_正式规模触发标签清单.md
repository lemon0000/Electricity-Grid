# RQ2 正式规模触发标签清单

创建日期：2026-08-22
适用范围：RQ2 首篇主创新的正式规模批处理（L5 λ 前沿 + H2 生成式场景外 + 3-source 消融，及其冻结种子/机制邻域敏感性）。

本页是**执行机打标签运行**的操作清单，不重述科学契约。权威来源：`agent.md` §7/§9/§10（路由/公平性/技术标准）、[科研实验闭环流程.md](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/docs/plan/科研实验闭环流程.md)（跨机闭环与标签约定）、[rq2_formal_batch.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/rq2_formal_batch.yaml)（冻结作业清单）。

> 诚实边界（`agent.md` §4/§8）：本批只编排已过 R3 审查的合成/trace 派生机制入口，`security_certified` 恒为 `false`，不改写冻结的 B3/B4/B5 基线，不启动 repair-010 多阶段长求解。产物性质是机制证据，绝不构成工程/合同/经验-VMA/CFE 认证。

---

## 1. 触发机制（一句话）

固定入口 [run_experiment.ps1](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/scripts/run_experiment.ps1) 在**标签指向的 commit** 上读取 [configs/experiment.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/experiment.yaml) 的 `kind` 字段决定行为：

| `kind` | 行为 | 依赖 | 产物性质 |
|---|---|---|---|
| `pytest-smoke`（分支 HEAD 默认） | 跑确定性单测子集，验证闭环管道连通 | 仅 Python | `pipeline_plumbing_smoke_only` |
| `rq2-formal-batch` | 跑 [run_rq2_formal_batch.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/experiments/run_rq2_formal_batch.py)，19 个预注册作业，产物重定向到 `$runDir` | Python + HiGHS（开源，无许可） | 合成/trace 派生机制证据，`security_certified=false` |

关键点：**分支 HEAD 恒保持 `kind: pytest-smoke`**（“普通提交 ≠ 启动实验”）。要跑正式批处理，须**单独提交一次**把 `kind` 翻到 `rq2-formal-batch`、给该 commit 打 `run-*` 标签、推标签，然后在 HEAD 上把 `kind` 翻回 `pytest-smoke`。标签是不可变快照，会永久捕获 formal-batch 配置；分支 HEAD 回到安全默认。

---

## 2. 预注册作业清单（结果前冻结，19 个）

由 [rq2_formal_batch.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/rq2_formal_batch.yaml) 声明，一次批处理调用全部产出。白名单覆写只允许统计档位与机制工作点标量（seed / n_train / scale / β / budget / λ / target_count），禁止触碰任何诚实标签、`parameter_status` 或产物路径。

| 组 | job_id | runner | 覆写 | 目的 |
|---|---|---|---|---|
| A 核心 | A1_l5_lambda_frontier | L5 economic stochastic | —— | H1/H3：13 点加密 λ 前沿 |
| A 核心 | A2/A3/A4_h2_generated | H2 stochastic holdout（generated） | seed=20260822/23/24 | H2：生成式场景外欠交付跨种子稳健 |
| A 核心 | A5/A6/A7_ablation | 3-source ablation | seed=20260822/23/24 | H2：跨 manual/generated/reduced 稳健 |
| B 机制敏感性 | B1/B2_grid_scale | 3-source ablation | grid_stress_scale=30/50 | H2 符号在网络压力邻域稳健 |
| B 机制敏感性 | B3/B4_green_scale | 3-source ablation | green_call_scale=45/75 | H2 符号在绿电调用邻域稳健 |
| B 机制敏感性 | B5/B6_budget | 3-source ablation | budget=80/250 | H2 符号在预算邻域稳健 |
| B 机制敏感性 | B7/B8_beta | 3-source ablation | β=0.3/0.7 | H2 符号在风险档位邻域稳健 |
| C L5 敏感性 | C1_budget_80 | L5 economic stochastic | budget=80 | **故意**探 H3 失效边界（前沿坍缩） |
| C L5 敏感性 | C2_budget_250 | L5 economic stochastic | budget=250 | H1/H3 在宽预算下 |
| C L5 敏感性 | C3/C4_beta | L5 economic stochastic | β=0.3/0.7 | H3 在风险档位邻域 |

> `B5_ablation_budget_80` 与 `C1_l5_budget_80` 是**如实报告的方法失效区域**（`agent.md` §9），不是错误：预算不足以买断尾部时 H3 单调权衡不成立、前沿坍缩为一点。H1/H2/H3 均为科学发现，逐 job 报告、绝不在批驱动设门；某种子或邻域点削弱某符号也如实透传，不丢弃。

本机端到端自检（2026-08-22，conda `compute`，HiGHS）：19/19 job `gate_passed=true`，`batch_gate_passed=true`，`security_certified=false`；H1 高估量 20 MW（4 个 L5 job），H2 场景外欠交付=true（3 个生成式种子），H2 跨来源稳健=true（11 个消融 job）。全批约 15 秒，`SMOKE_TIMEOUT_SECONDS` 默认 3600 秒绰绰有余。

---

## 3. 推荐触发序列

在**公司 Mac** 上准备并推标签；**执行机**按 [科研实验闭环流程.md](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/docs/plan/科研实验闭环流程.md) 第 5-8 节自动消费。

| 顺序 | 标签 | kind | 作用 |
|---|---|---|---|
| 1（可选，首次跑执行机建议） | `run-20260822-001` | `pytest-smoke` | 先验证 tag→拉取→worktree→运行→产物→上传 闭环连通 |
| 2 | `run-20260822-002` | `rq2-formal-batch` | 跑全部 19 个正式规模作业 |

失败重试用新标签，不复用：`run-20260822-002-r2`（`run-*` 标签一旦使用不得删除/强推/复用）。`NNN` 按当日已用序号递增。

---

## 4. 精确操作（公司 Mac）

### 4.1 冒烟连通性标签（可选，序号 001）

分支 HEAD 默认即 `kind: pytest-smoke`，直接打标签即可：

~~~bash
git switch experiment
git pull --ff-only origin experiment
git tag -a run-20260822-001 -m "冒烟：验证跨机闭环管道连通"
git push origin run-20260822-001
~~~

### 4.2 正式批处理标签（序号 002）

**一次性提交**把 `experiment.yaml` 的 `kind` 翻到 `rq2-formal-batch`，打标签，然后翻回默认：

~~~bash
git switch experiment
git pull --ff-only origin experiment

# ① 翻到 formal-batch：把 configs/experiment.yaml 的
#    kind: pytest-smoke  改为  kind: rq2-formal-batch
#    （可选）显式声明 batch_config: configs/rq2_formal_batch.yaml；缺省即用此文件
git add configs/experiment.yaml
git commit -m "trigger: RQ2 正式规模批处理（run-20260822-002）"
git push origin experiment

# ② 给该 commit 打不可变标签并推送（这一步才真正触发执行机）
git tag -a run-20260822-002 -m "RQ2 正式规模批处理：L5 λ 前沿 + H2 生成式 + 3-source 消融（19 job）"
git push origin run-20260822-002

# ③ 翻回安全默认，保证后续普通提交不再误触发批处理
#    把 configs/experiment.yaml 的 kind 改回 pytest-smoke

物理派生 `grid_need` 的 A/B 增量不改写上述 19-job v1。其 successor 清单为
`configs/rq2_formal_batch_network_rts24_v2.yaml`；待单独授权运行时，仍使用
`kind: rq2-formal-batch`，并显式设置
`batch_config: configs/rq2_formal_batch_network_rts24_v2.yaml`。该清单已绑定
`configs/rq2_l5_economic_network_rts24.yaml` 的 SHA-256；本次开发不打标签、
不启动该正式批次。

Temporal H2 successor 另有独立 R4 预注册：

- 预注册：`configs/rq2_h2_temporal_successor_preregistration_v1.yaml`
- base config：`configs/rq2_h2_temporal_successor_formal_v1.yaml`
- batch config：`configs/rq2_h2_temporal_successor_batch_v1.yaml`
- 说明：`docs/plan/RQ2_temporal_successor_preregistration.md`
- 执行机流程：`docs/plan/RQ2_temporal_17job_执行机运行流程.md`

该 17-job 清单当前 `formal_execution_ready=false`。本次只冻结配置，不修改
`configs/experiment.yaml`、不创建或推送 `run-*` 标签。即使 R4 审查通过，也
必须等待用户另行明确授权；届时使用全新标签，并在 trigger commit 中显式声明
`batch_config: configs/rq2_h2_temporal_successor_batch_v1.yaml`。阈值、种子、
样本数、窗口长度、恢复尾部和缩减规模不得在授权提交中修改。
git add configs/experiment.yaml
git commit -m "revert trigger: experiment.yaml 恢复 pytest-smoke 默认"
git push origin experiment
~~~

标签 `run-20260822-002` 永久指向 formal-batch 的 commit（不受 ③ 影响）；分支 HEAD 回到冒烟默认。

### 4.3 执行机侧无需改动

执行机固定调用 [run_experiment.ps1](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/scripts/run_experiment.ps1)，在标签 commit 上读到 `kind: rq2-formal-batch` 后自动：调用 `experiments.run_rq2_formal_batch --config configs/rq2_formal_batch.yaml --output-root $runDir`，把 `batch_manifest.json` 与逐 job 的 `effective_config.yaml`（含 SHA-256）、`summary.json` 全部写到 `$runDir` 下随工件上传。`metrics.json` 记录 `batch_gate_passed` / `job_count`；`status.json` 只描述进程/工件状态，不解释科研结论。

若需超过默认 3600 秒（正式规模 n_train=200，本机 HiGHS 约 15 秒，一般无需），在执行机 `experiment-config.ps1` 设 `SMOKE_TIMEOUT_SECONDS`。

---

## 5. 结果回收（公司 Mac）

~~~bash
git fetch origin experiment-results
git show origin/experiment-results:results/run-20260822-002/summary.md
git show origin/experiment-results:results/run-20260822-002/metrics.json
git show origin/experiment-results:results/run-20260822-002/status.json
~~~

逐 job 的科学发现（H1 高估量 / H2 场景外欠交付 / H2 跨来源稳健 / H3 成本-尾部风险单调权衡及其 Pareto 前沿 + 各 job `effective_config_sha256`）在上传的 `batch_manifest.json` 内；据此做结果分析与论文图表（H3 前沿曲线与 C1 故意坍缩点可直接从各 L5 job 的 `frontier` 数组重画）。`status=success` 只表示批处理进程与门通过，不等于任何工程/安全/经验结论。

---

## 6. 硬规则回顾

1. 普通提交 ≠ 启动实验；`run-*` 标签 = 不可变启动请求。
2. `run-*` 标签不得复用、删除、强推；失败重试用 `-rN` 新标签。
3. 分支 HEAD 恒保持 `kind: pytest-smoke`；formal-batch 只存在于对应标签的 commit。
4. 批驱动 fail-closed：任一 job 抛错/门未过/报告 `security_certified≠false` → 整批 `batch_gate_passed=false` 且退出非零。
5. 覆写白名单只含统计/机制标量；越界覆写、翻改诚实标签或产物路径一律 fail-closed。
