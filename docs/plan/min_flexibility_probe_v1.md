# 最小业务柔性池探针记录

2026-11-08，`DRAFT_NONAUTHORITATIVE`，可行性探针，不是论文结果。脚本 `experiments/min_flexibility_probe_v1.py`，输出 `results/tables/min_flexibility_probe_v1_non_authoritative/`。

## attempt_01 判定作废

attempt_01 的 `verdict: no_gap` 是分类错误：它把 `None`（柔性比例取 [0,1] 内任何值都不能让该方法判可交付）当成缺失值丢掉，只比较剩下的数值。attempt_02 修正了分类，attempt_01 保留不删，以 attempt_02 为准。

## 结果一：柔性深度 f 的门槛与方法无关

4 个 D 单元上，只要某方法能判可交付，最小 `flexible_fraction` 都是 2/5（二分上界 103/256）。这个值由 h1 的瞬时供电缺口决定：`workload × f ≥ grid_shortfall / slope`，即 `1/2 × f ≥ 1/5`。三种方法在这一项上的计算相同，所以门槛相同。

| 单元 | 瞬时 | 固定余量 | 完整时序 |
|---|---|---|---|
| fast/on_time/early | 2/5 | 2/5 | 无解 |
| fast/on_time/late | 2/5 | 无解 | 无解 |
| slow/on_time/early | 2/5 | 2/5 | 2/5 |
| slow/delayed/early | 2/5 | 2/5 | 无解 |

“无解”的原因不在柔性比例。f 从 2/5 加到 1，债务 cohort 始终是 1/5（只延期缺口那部分），完整时序在 3 个单元里一直判不可交付。fast/on_time/early 在 h2–h4 的恢复上限各项为 `capacity=1/5, max_recovery=1/5, spare_compute=1/2, grid_room=1/5, cfe_room=0`，卡住恢复的是清洁额度（`cfe_room=0`）。把 `compute_capacity` 放大到 2 倍也不改变判定。

结论：只把柔性池当成“可延期比例”时，三种方法给出相同的最小值，这个角度在 f 上退化。

## 结果二：柔性的时长（期限容忍度）上出现方法差异

把 `deadline_lag`（延期工作允许拖延的小时数）从 0 扫到 6，固定 f=1/2，判定串依次为瞬时/固定余量/完整时序：

| lag | fast/on_time/early | fast/on_time/late | slow/on_time/early | slow/delayed/early |
|---|---|---|---|---|
| 0 | PFF | PFF | PFF | PFF |
| 1 | PPF | PFF | PPP | PPF |
| 2（冻结值） | PPF | PFF | PPP | PPF |
| 3 | PPF | PFF | PPP | PPP |
| 4 | PPP | PFF | PPP | PPP |
| 5–6 | PPP | PFF | PPP | PPP |

各方法判可交付所需的最小 lag：

| 单元 | 瞬时 | 固定余量 | 完整时序 |
|---|---|---|---|
| fast/on_time/early | 0 | 1 | 4 |
| fast/on_time/late | 0 | 无解 | 无解 |
| slow/on_time/early | 0 | 1 | 1 |
| slow/delayed/early | 0 | 1 | 3 |

瞬时法不读期限，lag=0 就判通过；完整时序要求 3–4 小时，或者在 late 清洁路径下任何 lag 都不够。

## 解读与限制

- 业务柔性至少有两个维度：深度（f，能延期多少）和时长（lag，能拖多久）。简化方法对深度的估计正确，对时长的需求估计偏低。这是一个非零、随方法变化的差距。
- fast/on_time/late 在 lag 和 f 上都无解，说明恢复资源（清洁额度）不足时，扩大业务柔性也救不回来，需要的是供给侧资源。
- 证据规模小：10 小时玩具 fixture，4 个单元，lag 以小时计，只说明机制存在，不支持量级主张。
- 扫描用的临时 yaml 放在系统临时目录，未写入仓库；lag 扫描是内联运行，未固化为脚本和报告。
- 尚未检查 DC02 等文献是否已经把期限容忍度作为决策变量。
