## 审查方：（独立实例标识，需声明未参与写入）

我声明未参与 `src/staged_deliverability_replay_v1.py`、`src/staged_deliverability_development_v1.py` 及其测试的写入；本审查只读，未修改任何文件，未启动正式实验。

## 审查日期

2026-11-05

## 审查对象

`src/staged_deliverability_replay_v1.py` @ `f9738c82308d2379e98e1c46318ff2198e7900fbc9d368e41176db75fd603c7c`（259 行）

## B1 基准

`src/staged_deliverability_development_v1.py` @ `91bbc6aaaac458c8fcb23c11d830a98af99e1d50d42b3c0489246ec1922109e0`（440 行）

两个哈希与行数均已本地复核，与审查包 §1 一致。测试 `76 passed`（`rq2-executor` 解释器，2.65 秒），与 §7 声明一致。

---

## 逐点判定

| 审查点 | 判定 | 依据或缺陷 |
|---|---|---|
| 一 给定 q 的分解顺序 | **REWORK** | 顺序正确，但"`q` 超过两类请求之和"时无守卫，静默吞掉越界调用量 |
| 二 恢复余量判定 | PASS | 公式与 `advance()` 199–207 行逐项相同；3000 次随机对照零差异；边界 `r == headroom` 通过、`r` 略高即触发 |
| 三 阻塞停止划分 | PASS | 沿用 `advance()` 237 行的划分；`recovery_headroom` 归入阻塞恰当，降级会改变 D1 计数 |
| 四 cohort 分配等价 | PASS | 手工推演证明 `r == limit` 时严格等价；合成例逐项相等 |
| 五 三值映射边界 | PASS | 9 种取值组合全部符合 `agent.md` §4；建议的实现层断言非必需 |

---

## 一、给定 q 的分解顺序 —— REWORK

**已确认正确的部分。** `replay_step` 第 85–86 行的分解与 `advance()` 第 195–196 行同序（先电网、后清洁）。逐记录比对 24 个网格单元、三种方法共 **230 条记录，零处不一致**。`q < grid/slope` 时 `cfe_served == 0`；`q == grid/slope + green/slope` 时两个 `_shortfall` 均为 0。

**缺陷。** 当 `q > grid/slope + green/slope`（超出两类请求之和）时：

- `grid_served = grid/slope`，`cfe_served = green/slope`，两个 `_shortfall` 均为 0 —— 无违约码；
- 但 `record.deferred = grid_served + cfe_served < q`，而账本按 `incurred=q` 记账 —— 记账量与请求量分岔。

合成复现（`capacity=1/5, alpha=1, eta=1`，`workload=1, clean_mwh=0, supply_mw=10`，即 `grid=0, green=1`；输入 `q=5, r=0`）：

```
served=(0, 1)  short=(0, 0)  deferred=1  viol=('device_capacity', 'call_ramp')
```

越界的 4 个 `MW_c` 既不进 `deferred`，也不触发任何违约码。`advance()` 中 `q = grid_served + cfe_served` 恒等于两者之和，故该情形在原执行中不可达；`extract_actions` 同样只产出可达的 q，因此这不影响现有 D 结果。但 `replay_full_temporal` 的公开接口接受裸 `(q, r)` 序列，越界即静默。

**最小修法（一行，第 86 行后）：**

```python
if q > grid / p.slope + green / p.slope:
    raise ValueError("command exceeds the hour's total service request")
```

语义判断：`q` 超过两类请求之和不是"服务缺口"（缺口已为 0），而是"越权调用"，应作为命令非法拒绝，不应折算成已有违约码。该守卫不触及 B1 冻结字节，也不改变 D1 的 11/24 与敏感性的 23/27，因为现有方法链从不产出此类 q。

---

## 二、恢复量超过真实余量的判定 —— PASS

`_full_temporal_recovery_limit`（第 57–65 行）与 `advance()` 第 199–207 行逐项相同：`capacity`、`max_recovery`、`ledger.debt/eta`，再并入 `compute_capacity - workload`、`(supply_mw - reference)/slope`，`alpha` 非零时并入清洁余量项；两处均在账本更新**之前**取 `ledger.debt`，比较对象一致。

- **3000 次随机参数对照**（`alpha ∈ {0, 1/2, 7/10, 9/10}`，`eta ∈ {1/4,…,1}`，随机 debt/负荷/容量/供能/清洁）公式值零差异。
- **边界相等**：`r == headroom` 不触发，`r == headroom + 1/100` 必触发，3000 次均成立。判通过正确——`advance()` 的 `limit` 本身是可达上界。
- **`headroom == 0 & r == 0`**：`0 > 0` 为 False，不误报。
- **"advance 会因 limit 为 0 而拒绝、重放仍接受 r"**：`full_temporal` 下 `q > 0` 与 `r > 0` 互斥（`advance()` 仅当 `grid + green == 0` 才进入 recovery 分支，此时 `q == 0`）。重放中 `r > 0` 且 `headroom == 0` 必被第 110 行标出；合并调用时 `headroom` 恒被 `max(compute_capacity - workload, 0)` 与 `max((supply_mw - reference)/slope, 0)` 压到 0，故 `r > 0` 必报。第 66 行的担心已被第 110 行正确处理，实际轨迹上未观察到误报。

---

## 三、阻塞违约时停止而非继续 —— PASS

重放的 `blocking = set(violations) - {"hourly_cfe", "cfe_call_shortfall"}`（第 115 行）与 `advance()` 第 237 行完全相同，只是 `advance()` 另以 `state.method == "full_temporal"` 判 `committed`，而重放本身就是 `full_temporal` 执行，沿用旧划分是正确的。

实跑证据（24 单元、重放共 181 条记录：`full_temporal` 70、`instantaneous` 65、`fixed_headroom` 46）：

| 方法 | 违约码 | 次数 |
|---|---|---:|
| fixed_headroom | `recovery_headroom` | 5 |
| fixed_headroom | `hourly_cfe` | 6 |
| fixed_headroom | `scalar_supply` | 4 |
| fixed_headroom | `grid_service_shortfall` / `cfe_call_shortfall` | 2 / 2 |
| instantaneous | `event_envelope` | 3 |
| instantaneous | `cfe_call_shortfall` | 1 |
| full_temporal | `hourly_cfe` / `scalar_supply` / 两类 shortfall | 2 / 2 / 2 / 2 |

**`recovery_debt`、`event_envelope` 归入阻塞：应保持。** `advance()` 亦然；重放的存在意义就是忠实复现 `full_temporal` 语义（P4），放宽这两项会破坏恒等。

**`recovery_headroom` 归入阻塞：应保持，不降级为"记账不停止"。** 理由：

1. `advance()` 在 `full_temporal` 下构造上保证 `r ≤ limit`，该码永不触发；重放触发即"给定 r 超过真实可行性边界"。
2. 重放契约禁止重新规划（§8.1），对不可行命令只能如实报告并停止，没有"裁剪后继续"的合法选项。
3. 这是固定余量法被暴露的机制（§3）。改为非阻塞后，5 个带该码的 `fixed_headroom` 单元会继续执行并可能被记为 D1，直接改变 D1 的 11/24 计数。

**"过严"的担忧在判决层不成立。** `assessment()` 对 `full_temporal` 的判据是"无相关违约且无期限未完成且未停止"，任何重放违约都使 `replay_verdict=False`；`recovery_headroom` 是否停止只影响重放覆盖到哪一小时，不改变 `replay_verdict`。

---

## 四、恢复量到 cohort 的分配规则 —— PASS

**手工推演。** `advance()` 循环中 `recovery` 是累积量，第 k 个 cohort 实得

```
a_k = min(rem_k, max(limit - Σ_{j<k} a_j/eta, 0) · eta) = min(rem_k, max(limit·eta - S_k, 0))
```

其中 `S_k = Σ_{j<k} a_j`。重放中 `remaining_budget = r·eta - S_k`，`a_k = min(rem_k, max(r·eta - S_k, 0))`。

两式**唯一差异是常数 `limit·eta` 被换成 `r·eta`**。`r == limit` 时二者在每一步上恒等，所有部分和一致。而 `full_temporal` 的 r 正是由同一公式算出的 `limit`，故重放时 `r == limit` 恒成立，分配严格等价。`extract_actions` 把任何方法的 `recovery` 原样作为 r 传入，因此一般情形下 `r = min(limit, p.fixed_headroom)`（`fixed_headroom`）或 `0`（`instantaneous`），差异只在常数项。

**合成例逐项验证**（双 cohort：`remaining = 3` 与 `5`，`eta = 1/2`，`limit = 1`）：

```
eta=1/2  limit=1  advance r=1 alloc=((-1, 1/2),) | replay r=limit alloc=((-1, 1/2),)  EQUAL=True
eta=1    limit=1  advance r=1 alloc=((-1, 1),)   | replay r=limit alloc=((-1, 1),)    EQUAL=True
replay r=1/4 → budget=1/8 → alloc=((-1, 1/8),)；r=1/2 → 1/4；r=3/4 → 3/8；r=1 → 1/2
```

η 缩放正确（`eta = 1/2` 时 `r=1` 仅回收 `1/2` 工作量，与 `advance()` 相同）。第 130 行的 `remaining_budget < 0` 分支不可达（每次 `effective = min(c.remaining, max(remaining_budget, 0))`），属防御性死代码，无害。排序键 `(due_hour, created_hour)` 与 `advance()` 相同，`created_hour` 唯一，顺序一致。

---

## 五、三值映射的边界 —— PASS

9 种取值组合逐一比对，全部符合 `agent.md` §4 "未决既不计入成功也不计入失败"：

| method \ reference | True | False | None |
|---|---|---|---|
| True | D3 | D1 | D5 |
| False | D2 | D4 | D5 |
| None | D5 | D5 | D5 |

`None` 优先于一切，正确；类型守卫拒绝非 `bool`/`None`。

**关于在 `verdicts()` 加断言的建议：非必需。** `test_full_temporal_cell_never_reports_a_disagreement` 已覆盖全部 8 个单元（2 业务 × 2 电网 × 2 清洁），而非仅 4 个 B1 情景，且 `evaluate_cell` 走的就是生产调用路径。在这批数据上，实现层断言不会比测试层多抓到任何东西；加与不加是防御深度偏好，不是缺陷。若日后网格扩到 P4 未覆盖的参数区，再行加强。

---

## 七、可复用证据的独立复核

| 证据 | 复核结果 |
|---|---|
| P4 恒等 4/4 | 测试通过；`identity_check` 对 4 个 B1 情景断言 `records_identical` / `stop_identical` / `verdict_identical` |
| 动作保真 | 通过；逐项断言重放动作与给定命令相同且不超出长度 |
| 加载器等价 | 通过；D fixture `baseline` 与 B1 fixture 的 `params` 与观测逐字段相等 |
| D2 不可达 | 通过；`test_approximations_are_structurally_permissive` 全网格扫描 |
| 前缀语义 | 通过；`len(executed) <= len(actions)` |

补充：P4 只覆盖 `full_temporal` 自身产出的 q，**不覆盖**审查点一的越界 q 与审查点四的部分 r —— 这两处本轮已用独立合成例覆盖。

---

## 八、非阻塞观察（不计入判定）

审查包对 `advance()` 的行号引用有轻微漂移：§2 称"第 194–196 行"，实际分解在 **195–196** 行；§3 称"第 199–206 行"，实际为 **199–207** 行；§5 称"第 206–212 行"，实际为 **208–213** 行；§4 称"第 240 行"，实际为 **237** 行。哈希一致，内容无误，仅行号需更新，避免后续审查沿用旧行号。

---

**总判定：REWORK**

最小修复集（一项）：

1. `src/staged_deliverability_replay_v1.py` 第 86 行后增加 `q > grid/slope + green/slope` 的 `ValueError` 守卫；可选择性补一条测试（越界 q 应被拒绝）。

该修复不触及 B1 冻结字节，不改变 D1 11/24 与敏感性 23/27 的任何现行结果。按 `agent.md` §7，修复须在新 versioned successor 中进行，旧字节不得修改；同一验收项再次失败即 `ESCALATE`。

R3 PASS 尚不成立；6.3/6.4 正文在此之前不应落笔，且 PASS 本身也不授权 formal run、资源准入或论文主张（§10）。

---

## 九、REWORK 修复登记（2026-11-05，同一写入会话）

按 `agent.md` §7 的 successor 规则修复，v1 字节未动（`attempt_01/report.json` 的 `sources` 已钉住其 SHA-256，不可改写）。

| 文件 | 角色 | 状态 |
|---|---|---|
| `src/staged_deliverability_replay_v1.py` | 被审对象 | **未修改**，`f9738c82…` 不变 |
| `src/staged_deliverability_replay_v2.py` | successor | 新增，`5bd902125112af2c03bf02c9e5842bc1dc4d5db016b119fd284fc68efec6e446` |
| `src/staged_deliverability_d_grid_v1.py` | 调用方 | **未修改**，`d53111ac…` 不变 |
| `src/staged_deliverability_d_grid_v2.py` | 调用方 successor，改走 replay v2 | 新增，`7041d9b9c8227a577f12e0e3187235e56bd89595e5020d92ee92fd34bd82077c` |
| `tests/test_staged_deliverability_replay_v2.py` | 修复测试 | 新增，11 项 |

**功能差异仅一处**：`replay_step` 在分解前新增

```python
if q > grid / p.slope + green / p.slope:
    raise ValueError("command exceeds the hour's total service request")
```

其余为模块 docstring 的 successor 说明（无行为差异）。审查点二至五的代码路径逐字节保持。

**验证**：

- 测试 `87 passed`（既有 76 项 + 新增 11 项，3.33 秒，`rq2-executor`）。
- 守卫可达性：24 单元 × 3 方法，所有 `extract_actions` 产出的 q 均满足 `q <= grid/slope + green/slope`，守卫在 D 网格上不可达。
- 回归：v2 网格 24 个轨迹与 `attempt_01/report.json` **逐字段零差异**；复核计数 `{D1: 11, D2: 0, D3: 3, D4: 10, D5: 0}`、策略轴 `{D1: 8, D2: 0, D3: 6, D4: 10, D5: 0}` 均与记账一致。
- 缺陷钉住：`test_v1_swallowed_the_same_command` 以测试固定 v1 的越界行为，确保两种语义不会悄悄回退。

**未做**：未重跑 attempt_01 或敏感性 attempt_05（守卫不可达，重跑不产生新证据）；未提交。敏感性扫描器仍经 `d_grid_v1` 走 replay v1，其结论不受影响。

---

## 十、v2 successor 的写入方技术复核（2026-11-06，**非** official verdict）

按 `agent.md` §7，official R3 结论必须由未参与该 candidate 写入的实例签发。v2 由同一写入代理产出，故本节只是写入方一侧的技术复核，**不得作为 PASS 引用，也不打开任何 gate**。official 判定见 §十一（由独立只读实例给出）。

**被复核字节**：`src/staged_deliverability_replay_v2.py` @ `5bd902125112af2c03bf02c9e5842bc1dc4d5db016b119fd284fc68efec6e446`（276 行）；`src/staged_deliverability_d_grid_v2.py` @ `7041d9b9c8227a577f12e0e3187235e56bd89595e5020d92ee92fd34bd82077c`（267 行）；测试 @ `542d24fa344dfd6b3f8658b45a176c5ef4392902fc29e8c1e37a728df4cd41a7`（120 行）。

### 守卫生效条件

4000 次随机参数下对 `q ∈ {total, total+1/100, total/2, 0}` 共 16000 次调用：守卫**当且仅当** `q > total` 时触发，误触发与漏触发均为 0。`alpha == 0` 分支同样正确（`green` 恒为 0，`total = grid/slope`）。

### 严格 `>` 是必要的，不是风格选择

D 网格 230 条 `extract_actions` 记录中，最小余量 `total - q = 0`，出现在 `fast/on_time/early/instantaneous`。即该单元存在**恰好等于**请求总量的合法 q。若写成 `>=`，该单元会被误拒，D 网格出现真实回归。`advance()` 的 `cfe_served = min(green/slope, room - grid_served)` 在 `room ≥ grid/slope + green/slope` 时正好产出 `grid/slope + green/slope`，故边界合法、越界非法，`>` 是正确的分界。

### 合法区间内逐字节等价

2000 组随机参数 × 5 个合法 q 共 10000 次 `replay_step` 对照：v1 与 v2 返回的 `records`、`stopped`、`ledger`、`events`、`rest`、`call_energy` 与违约元组全部相同，差异 0。新守卫只在不可达区域改变行为。

### 回归

- 测试 87 项通过（既有 76 + 新增 11）。
- v2 网格 24 个轨迹与 `attempt_01/report.json` 逐字段零差异（§九已记）。
- `diff` 核实：相对 v1 的功能改动仅新增守卫一处，其余为 docstring。

### 本节不足以关闭审查门

写入方自查与上一轮已自测的 P4 同理，不能替代独立判断。特别是守卫"是否误伤合法命令"与"严格 `>` 是否恰当"这两项，必须由独立实例确认。

---

## 十一、v2 successor 的 official R3 判定（2026-11-06）

```
审查方：独立只读实例，未参与 v2 及本记录任何写入；仓库内未创建/修改/删除文件，
        一次性脚本仅写在系统临时目录
审查日期：2026-11-06
审查对象：src/staged_deliverability_replay_v2.py @ 5bd902125112af2c03bf02c9e5842bc1dc4d5db016b119fd284fc68efec6e446（276 行）
          src/staged_deliverability_d_grid_v2.py @ 7041d9b9c8227a577f12e0e3187235e56bd89595e5020d92ee92fd34bd82077c（267 行）
B1 基准：src/staged_deliverability_development_v1.py @ 91bbc6aaaac458c8fcb23c11d830a98af99e1d50d42b3c0489246ec1922109e0（440 行）
哈希核对：一致
```

| 审查点 | 判定 | 依据 |
|---|---|---|
| 一 给定q的分解顺序 | **PASS** | 与 `advance()` 195–196 行同序；230 条记录反向重算 0 处不一致；守卫当且仅当 `q > total` 触发 |
| 二 恢复余量判定 | **PASS** | v2 70–78 行与 `advance()` 199–207 行公式逐项相同；3000 组随机参数 0 处不一致；`r==lim` 零误报、`r==lim+1/100` 零漏报 |
| 三 阻塞停止划分 | **PASS** | v2 132 行与 `advance()` 237 行字面集合同为 `{hourly_cfe, cfe_call_shortfall}`；`recovery_headroom` 归阻塞不改变判决，只影响覆盖时刻 |
| 四 cohort分配等价 | **PASS** | 代数等价于 `r==lim`；120 例多 cohort 合成差分 0 处不一致；`remaining_budget < 0` 为不可达防御代码 |
| 五 三值映射边界 | **PASS** | 与 v1 逐字节相同；九宫格实测符合 §4；`None` 优先且未被折算 |

**总判定：PASS**（仅针对上述确切字节；不涉及 v1，也不授权 formal run）

### 独立实例的关键结论

- **严格 `>` 正确，`>=` 会误伤**：边界 `q == grid/slope + green/slope` 是 `advance()` 在 `room` 饱和时的正常输出，用 `>=` 会把合法饱和调用判为非法。
- **守卫在真实方法链上结构不可达**：`q = gs + cs`，两项各自受请求量或 `room` 约束，只会被进一步压缩，不会放大；`extract_actions` 取的正是这两项之和。`alpha == 0` 时 `green ≡ 0`，不漏也不误伤；`slope = beta·facility_factor > 0`，无除零。
- **功能差异确为守卫一处**：`diff -u` 仅 docstring 与守卫；`d_grid` 仅 docstring 与 import 来源，网格逻辑零改动。
- **回归**：24 单元 22 个字段与 `attempt_01/report.json` 零差异；计数 `{D1:11, D2:0, D3:3, D4:10, D5:0}` 与 `{D1:8, D3:6, D4:10}` 复算一致；`87 passed`。

### 主代理对子代理回报的核对

按 §7，子代理回报是线索而非证据，以下两条经本代理实测修正后方可引用：

1. **"223/230 条记录恰好落在边界上"——数字对，表述需修正。** 实测拆分为：`q == total > 0` **30 条**、`q == total == 0` **193 条**、严格落在内部 **7 条**。193 条为 `q=0` 的平凡边界，不是"服务量被打满"。但结论不变：`>=` 会误拒那 30 条真实饱和调用，仍构成回归，故严格 `>` 正确。
2. **`d_grid_v1` 行数 259 行**——经 `wc -l` 核实无误。

### 非阻塞观察

- `_full_temporal_recovery_limit` 与 `advance()` 的 limit 逻辑是两处独立实现，靠对照测试维持一致；若 B1 日后变更该公式，此处不会自动报警。属可维护性风险，非当前缺陷。
- 审查期间工作区出现了与本审查无关的改动（`paper/drafts/README.md`、`paper/drafts/staged_deliverability_methods.pdf` 变为 M，新增 `paper/render_current_drafts.py`、`paper/drafts/render_manifest.json`，时间戳 14:24–14:27）。这些不是审查或修复产生的，未被触碰，也不作为本轮证据。

### 状态

R3 独立审查门对 v2 确切字节闭合。v2 是新的审查对象；v1 保持 REWORK 历史记录不改。PASS 不授权 preflight、consume、spawn 或 formal run，也不授权改动科研协议、验收阈值或论文结论。
