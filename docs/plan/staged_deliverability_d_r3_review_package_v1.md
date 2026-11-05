# D 线 R3 独立审查包

2026-11-05。供**未参与写入**的独立审查方使用。审查对象是 `src/staged_deliverability_replay_v1.py` 的动作外置与完整时序重放语义，按 `agent.md` §7 属 R3（涉及恢复语义与非预见性）。

## 0. 审查方须知

**为什么需要独立审查**：该模块把"简化方法自己算出的动作"当作**给定命令**送进完整时序物理，是 D 线全部结论（假通过 11/24、23/27 组合）的唯一承重件。若重放语义与 B1 的 `advance()` 有偏差，所有 D1 计数都是在测实现而不是测简化。写入者已自测（P4 恒等 4/4、测试 76 项），但自测不能替代独立审查。

**审查方不应做的事**：不要修改任何文件；不要运行正式实验；不要评价网格设计、敏感性轴选择、结果解读或论文主张——那些属 R4。只判断下述五点的语义是否正确。

**判定结果**：对每点给出 `PASS` / `REWORK`（附具体缺陷与最小修法） / `ESCALATE`（无法判定，说明缺什么）。全部 PASS 后方可写 6.3/6.4 正文。

## 1. 审查对象与不可变边界

| 项 | 值 |
|---|---|
| 待审文件 | `src/staged_deliverability_replay_v1.py`（259 行）<br>SHA-256 `f9738c82308d2379e98e1c46318ff2198e7900fbc9d368e41176db75fd603c7c` |
| 只读依赖 | `src/staged_deliverability_development_v1.py`（B1，440 行，**冻结，不得修改**）<br>SHA-256 `91bbc6aaaac458c8fcb23c11d830a98af99e1d50d42b3c0489246ec1922109e0` |
| 依赖 | `src/rq2_joint_deliverability_boundary_v1/debt_cohorts.py`（冻结） |
| 上游结果 | `results/tables/staged_deliverability_d_v1_non_authoritative/attempt_01/` |
| 下游结果 | `results/tables/staged_deliverability_d_sensitivity_v1_non_authoritative/attempt_05/` |
| 测试 | `tests/test_staged_deliverability_replay_v1.py`（20）、`tests/test_staged_deliverability_d_grid_v1.py`（19）、`tests/test_staged_deliverability_d_sensitivity_v1.py`（37） |
| 解释器 | `D:\Miniconda3\envs\rq2-executor\python.exe`（`compute` 环境缺 pygments，pytest 无法启动） |

审查方应先核对上述两个哈希；若不符，说明字节已变，须重新登记审查对象，不得按本包判断。

B1 的 `advance()` 是新模块必须逐条对应的基准。它未被修改，其行为由既有 188 项测试与 B1–B3 开发验证绑定。

## 2. 审查点一：给定 q 的回分解顺序

**位置**：`replay_step` 第 85–86 行

```python
grid_served = min(q, grid / p.slope)
cfe_served = min(q - grid_served, green / p.slope)
```

**背景**：重放收到的是**合成命令** `q`（= 方法当期的总延期量），但原执行 `advance()` 是按"先电网服务、后清洁服务"分配的（第 194–196 行）：`grid_served = min(grid/slope, room)`，然后 `cfe_served = min(green/slope, room - grid_served)`。

**要判断**：给定 q 拆分回 grid/cfe 时采用同样顺序是否正确。若顺序反了，同一 q 会产出不同的 `grid_shortfall` 与 `cfe_shortfall`，进而改变违约码与判定。

**审查方应检查**：
- 当 `q < grid/slope` 时（只够电网），`cfe_served` 是否为 0；
- 当 `q > grid/slope + green/slope` 时（超出两类请求之和），两个 `_shortfall` 是否都为 0 且是否应另报违约；
- 与 `advance()` 第 194–196 行逐项对照。

**已知证据**：P4 恒等检验显示 `full_temporal` 自身动作重放后 `records_identical=True`（4/4 情景）。但该检验只覆盖 `full_temporal` 产生的 q，不覆盖简化方法产生的 q 的形状差异。**这一点需要独立判断，不能靠 P4 推定。**

## 3. 审查点二：恢复量超过真实余量的判定

**位置**：`replay_step` 第 96 行（计算）与第 110 行（判定），`_full_temporal_recovery_limit` 第 57–66 行

```python
headroom = _full_temporal_recovery_limit(params, state, o, reference)   # 第 96 行
...
(r > headroom, "recovery_headroom"),                                    # 第 110 行
```

`headroom` 取四者最小值：`capacity`、`max_recovery`、`ledger.debt / eta`、`compute_capacity - workload`、`(supply_mw - reference) / slope`，以及 `alpha` 存在时的清洁余量项。

**背景**：这是**固定余量法被暴露的唯一机制**。`fixed_headroom` 方法用常数 `p.fixed_headroom` 替代实际可用余量，因此它算出的 r 可能超过真实余量。若此判据错误，D1 的机制解释就不成立。

**要判断**：
- 边界相等（`r == headroom`）时判通过是否正确；
- `headroom == 0` 且 `r == 0` 时不应误报（当前 `0 > 0` 为 False，看似正确，但请确认）；
- 该判据是否与 `advance()` 在 `full_temporal` 模式下对 recovery 的 `limit` 计算完全一致（对照第 199–206 行）；
- 是否存在 `advance()` 会因 limit 而为 0 但重放仍接受 r 的情形。

## 4. 审查点三：阻塞违约时停止而非继续

**位置**：`replay_step` 第 115–116 行，以及第 33–38 行的常量

```python
REPLAY_VIOLATION_ORDER = (
    "grid_service_shortfall", "cfe_call_shortfall", "device_capacity", "scalar_supply",
    "hourly_cfe", "call_ramp", "event_envelope", "call_energy", "recovery_debt",
    "recovery_headroom",
)
NON_BLOCKING = frozenset({"hourly_cfe", "cfe_call_shortfall"})
...
blocking = set(violations) - NON_BLOCKING
committed = not blocking
```

**背景**：`advance()` 的既有划分（第 240 行）是 `blocking = set(violations) - {"hourly_cfe", "cfe_call_shortfall"}`——重放沿用了它。一旦阻塞，`stopped=True`，后续小时不再执行。

**要判断**：
- 沿用该划分是否仍适用于重放场景；
- 特别是 `recovery_debt`、`event_envelope`、`recovery_headroom` 归入阻塞是否合理——它们不直接破坏物理可行性，但会使账本或事件预算失真；
- `recovery_headroom` 是**新模块引入的**违约码（`advance()` 没有），把它归入阻塞（即不加入 NON_BLOCKING）是否恰当。当前代码中它**不在** `NON_BLOCKING` 里，因此一旦触发即停止。审查方需判断这是否过严——例如是否应改为记账但不停止。

**这一条是最可能出现 REWORK 的地方。**

## 5. 审查点四：恢复量到 cohort 的分配规则

**位置**：`replay_step` 第 121–133 行

```python
if committed and r > 0:
    budget = r * p.eta
    remaining_budget = budget
    for cohort in sorted(state.ledger.cohorts,
                         key=lambda c: (c.due_hour, c.created_hour)):
        effective = min(cohort.remaining, max(remaining_budget, ZERO))
        if effective:
            allocations.append((cohort.created_hour - state.hour_offset, effective))
            remaining_budget -= effective
```

**对照 `advance()` 第 206–212 行**：

```python
for cohort in sorted(state.ledger.cohorts,
                     key=lambda c: (c.due_hour, c.created_hour)):
    effective = min(cohort.remaining, max(limit - recovery, ZERO) * p.eta)
    if effective:
        allocations.append((cohort.created_hour - state.hour_offset, effective))
        recovery += effective / p.eta
```

**差别**：原实现**边分配边递减可恢复额度**（`limit - recovery`），重放**先定总预算 `r * eta` 再按序消耗**。

**要判断**：两者在给定 r 下是否严格等价。写入者认为等价（总量相同、排序相同、每步取 min、且 `recovery` 的递推与 `remaining_budget` 的递减互为镜像），但这是**审查最该独立验算的一处**——若不等价，重放的债务轨迹与原执行分岔，而 P4 恒等只覆盖 `full_temporal` 自身，可能掩盖问题。

**建议的验算方式**：构造一个双 cohort、`eta < 1`、`limit` 不足以满足全部债务的例子，手工推演两条路径的 `allocations`，比较是否逐项相等。若可写测试，建议提给写入者作为 REWORK 要求。

## 6. 审查点五：三值映射的边界

**位置**：`label_from` 第 187–205 行

```python
if method_verdict is None or reference_verdict is None:
    return "D5_undetermined"
if method_verdict and reference_verdict:
    return "D3_agree_pass"
if method_verdict and not reference_verdict:
    return "D1_false_pass"
if not method_verdict and reference_verdict:
    return "D2_false_reject"
return "D4_agree_fail"
```

**要判断**：
- `None`（未决）的优先级是否正确——当前任一为 `None` 即整对判 D5，不论另一方取值；
- 该规则与 `agent.md` §4「未决既不计入成功也不计入失败」是否一致；
- `full_temporal` 在**轴一**上两值理论恒等，若出现非平凡不等，当前代码会把它记入 D1/D2/D4 而不报实现缺陷。是否有必要在 `verdicts()` 里加一道断言（`method == "full_temporal"` 且 `mv != rv` 时抛错）？若无必要，请说明理由；若有必要，请指为 REWORK。

**已知证据**：`test_full_temporal_cell_never_reports_a_disagreement` 以测试方式挡了该情形（断言 `full_temporal` 只可能是 D3/D4/D5），但它挡在测试层，不在实现层。

## 7. 可直接复用的证据

审查方不必从零重建，以下已存在且可独立复核：

| 证据 | 位置 | 含义 |
|---|---|---|
| P4 恒等 | `identity_check`，4/4 情景 `records_identical=True` | `full_temporal` 自身动作重放后记录逐字节相同 |
| 动作保真 | `test_replay_executes_the_given_command_without_replanning` | 重放执行的动作序列与给定命令逐项相同，且不超出给定长度 |
| 加载器等价 | `test_baseline_path_reproduces_b1_observations` | D fixture 的 `baseline` 路径与 B1 冻结 fixture 的 `params` 与 10 个观测逐字段相等 |
| D2 不可达 | `test_approximations_are_structurally_permissive` | 简化判失败时参考必判失败 |
| 前缀语义 | `test_replay_accepts_a_prefix_command` | 方法提前停止时重放镜像该停止 |

运行命令：

```
D:\Miniconda3\envs\rq2-executor\python.exe -m pytest \
  tests/test_staged_deliverability_replay_v1.py \
  tests/test_staged_deliverability_d_grid_v1.py \
  tests/test_staged_deliverability_d_sensitivity_v1.py -q
```

预期 `76 passed`。

## 8. 已知的实现约束（不算缺陷）

1. **重放不重新规划**：收到 q/r 后绝不修正。这是设计目标，不是遗漏。
2. **前缀而非全窗**：方法提前停止时，重放只执行给定的前缀，剩余小时留空，由 `coverage_complete` 如实反映。`fast/delayed` 两个单元的 `full_temporal` 在 h2 停止，其 D4 依据是"提前停止即未履约"，与"跑满窗口后失败"证据强度不同——该限制已写入 validation report，属已知而非新发现。
3. **标量机制模型**：所有量为 `MW_c`/`MWh_c`，无 PYPOWER、无 AC、无网络证书。`security_certified=false` 恒成立。
4. **单一 10 小时 fixture**：`hours=10`，`first_hour=-2`，`last_hour=7`。增长关系为线性，未验证更长窗口。

## 9. 审查记录格式

建议按下列格式留档，写入 `results/tables/staged_deliverability_d_v1_non_authoritative/r3_review.md`：

```
审查方：（独立实例标识，需声明未参与写入）
审查日期：
审查对象：src/staged_deliverability_replay_v1.py @ <sha256>
B1 基准：src/staged_deliverability_development_v1.py @ <sha256>

| 审查点 | 判定 | 依据或缺陷 |
|---|---|---|
| 一 给定q的分解顺序 | PASS/REWORK/ESCALATE | |
| 二 恢复余量判定 | | |
| 三 阻塞停止划分 | | |
| 四 cohort分配等价 | | |
| 五 三值映射边界 | | |

总判定：PASS / REWORK（列出最小修复集）/ ESCALATE
```

`REWORK` 时写入者须在新 versioned successor 中修复，旧字节不得修改（`agent.md` §7）。同一验收项再次失败即 `ESCALATE`。

## 10. 通过之后

R3 PASS 只关闭独立审查门，**不**授权 formal run、资源准入或论文主张。6.3/6.4 正文可在 PASS 后落笔，但仍须遵守 blocker 登记中的四条边界：D2 不可达、115 单元按方法分解、失效边界、加强型匹配未做。
