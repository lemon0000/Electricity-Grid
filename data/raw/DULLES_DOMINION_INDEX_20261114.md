# 2016 Dulles 气象 / Dominion IRP 电网加强 数据索引（2026-11-14）

对应需求：PJM-DOM（北弗吉尼亚数据中心走廊）算例需要 2016 年逐小时气象与 PJM 负荷严格对齐，
以及 Dominion 侧数据中心负荷与输电加强项目的官方可引数字。

字节级清单：[`dulles_dominion_acquisition_20261114.json`](dulles_dominion_acquisition_20261114.json)（22 个文件）。
本文件只记录数据位置、口径与已核数字，不构成模型运行结论。

## 1. 2016 年 Dulles（KIAD）逐小时气象 —— 两源互校

`data/raw/openmeteo_2016_KIAD/v1/upstream/`（坐标 38.9531, −77.4565）

| 文件 | 时钟 | 行数 | 缺失 |
|---|---|---|---|
| `weather_dulles_KIAD_2016.csv` | America/New_York（你给的链接口径） | 8,784 | 0 |
| `weather_dulles_KIAD_2016_utc.csv` | UTC | 8,784 | 0 |

`data/raw/iem_asos_KIAD_2016/v1/upstream/`（IAD 站点实测，变量 tmpc / dwpc / relh）

| 文件 | 说明 |
|---|---|
| `asos_IAD_2016_m01_raw.csv` … `m12_raw.csv` | 按月抓的原始观测（12 个） |
| `asos_IAD_2016_all_observations.csv` | 合并去重：**10,022 条观测**，覆盖 2016-01-01 00:52 → 12-31 23:52 |
| `asos_IAD_2016_hourly_local.csv` | 按本地小时聚合，8,784 行，5 个小时无观测 |
| `asos_IAD_2016_hourly_utc.csv` | 按 UTC 小时聚合，8,784 行，11 个小时无观测（覆盖 99.87%） |

**两源一致性（8,773 个重叠小时）**：气温平均偏差 +0.07 °C、MAE **1.40 °C**、相关 **0.984**；
相对湿度平均偏差 −3.0 pp、MAE 8.0 pp、相关 0.884；年均气温 14.0 vs 14.1 °C，
夏季（6–8 月）峰值 38.5 °C（Open-Meteo，ERA5 格点）vs 37.2 °C（IEM 机场实测）。

**时必须注意（与负荷对齐）**：ICARUS-PJM 的 `pjm_zone_demand.csv` 列名是 `UTC Time`、2016 年 8,784 行，
即固定偏移 UTC 时钟。而 America/New_York 的 2016 年真实小时数是 8,783（3 月 13 日 02:00 夏令时跳变不存在）：
- Open-Meteo 的本地文件仍是 8,784 行，但其中 **2016-03-13 02:00 那一行是不存在的钟点**（API 不删格）；
- IEM 本地文件该小时自然缺失，UTC 版因此有 11 个空小时。

→ **与 PJM 负荷逐小时对齐请用两份 `*_utc.csv`**（都是 8,784 行）；若坚持用本地钟时，必须在方法里写明
夏令时那 1 小时如何处置，否则全年会整体错位 1 小时。

**IEM 接口两个坑（复现时需要知道）**：单次请求返回的结束日比请求的结束日早 1 天，
且一次请求约 2,500 行上限；按月抓并把结束日顺延一天后，数据才完整。

## 2. Dominion 电网加强项目（$c^F$ 的现实基线）

`data/raw/dominion_irp/v2025_2026/upstream/`
- `2024-irp-w_o-appendices.pdf`（406 页）
- `2025-integrated-resource-plan-update.pdf`（255 页）
- `2026-integrated-resource-plan-update.pdf`（400 页）

派生表：`data/processed/model_inputs/dominion_dc_load_transmission_v1/`

### 2.1 Golden–Mars–Wishing Star 500 kV 集群：逐项造价（Dominion 自己的 IRP 附录，单位 $M）

| 项目 | 电压 | 投运 | 2025 IRP | 2026 IRP |
|---|---|---|---|---|
| 500kV/230kV Line Extension – Southern（Wishing Star → Mars） | 230/500 | Dec-25 / Dec-26 | **842.3** | **867.0** |
| 5-2 Connecter – Mars to Golden | 230/500 | Jun-28 / Jun-29 | **342.9** | **565.0** |
| 5-2 North Line Extension – Aspen to Golden | 230/500 | Dec-27 / Dec-28 | **623.0** | **624.0** |
| Mars 2nd 500-230 kV TX | 230/500 | May-27 / Dec-27 | 42.2 | 42.2 |
| **集群合计** | | | **≈ 1,850** | **≈ 2,098** |
| 500/230kV Morrisville–Wishing Star New 500kV Line | 230/500 | Jun-30 | 863.2 | 896.6 |
| Loudoun Capacitor Banks | 230/500 | Jun-27 / Dec-27 | 90.1 | 109.0 |
| Line #502 / #584 Terminal Upgrade – Loudoun to Mosby | 500 | Jun-26 / Jun-28 | 6.3 / 6.4 | 6.3 / 6.4 |

你原稿里的「单期工程 6.5 亿–12 亿美元、单位扩容造价 450–650 k$/MW」与上表可以对上：
Wishing Star–Mars 一项 842 M$，若释放 1.5–2.5 GW，则单位造价 **337–561 k$/MW**，
落在你给的区间附近；但**集群口径下总投资要到 1.85–2.1 G$**，比「单期 6.5 亿–12 亿」高一档，
引用时要写清是"单项"还是"集群"。全部 440 条 Dominion 项目（含州、电压、投运时间、造价）见
`dominion_irp_transmission_projects.csv`。

### 2.2 数据中心负荷与合同规模（2025 IRP Update，图 2.1.15，单位 MW，截至各年 7 月底）

| 合同类型 | 2023-07 | 2024-07 | 2025-07 |
|---|---|---|---|
| ESAs | 5,827 | 8,012 | 9,815 |
| CLOAs | 2,008 | 5,835 | 7,098 |
| **Firm Capacity** | **7,835** | **13,847** | **16,913** |
| ELOAs | 8,658 | **7,570** | 30,132 |
| **合计合同** | **16,493** | **21,417** | **47,045** |

**这里要修正一处引用口径**：你说的「7.5 GW 已签并网协议」精确对应的是 **2024 年 7 月底的 ELOAs
（7,570 MW）**，只是四类合同之一；真正进入容量规划口径的是 **Firm Capacity（13,847 → 16,913 MW）**，
而「排队/合计合同」到 2025 年 7 月已是 **47,045 MW**（并非 20+ GW）。论文里请按合同类型分别引用，
不要写成"签约 7.5 GW、排队 20+ GW"——后者既低估了 ELOAs，也混淆了 ELOA 与 Firm Capacity。

### 2.3 一条可直接引用的"刚性"证据

2025 IRP Update 第 27 页原文：data centers *"have been hesitant to participate in demand response or
interruptible service participation programs; the Company has seen no evidence that data center customers
are willing to reduce load in response to high price signals."* —— 这可作为你模型中"数据中心默认不可延期、
柔性只能靠调度/迁移实现"的行业侧依据（引用时注明页码）。

## 3. PJM 官方负荷预测报告（已齐）

`data/raw/pjm_load_forecast_2026/v2026/upstream/`（5 个文件，10.24 MB）

| 文件 | 内容 |
|---|---|
| `2026-load-report.pdf`（8.35 MB） | PJM 2026 Load Forecast Report 正文 |
| `2026-load-report-data.xlsx`（0.21 MB） | 分区逐月峰值与电量，31 个工作表，含 `DOM` |
| `2026-load-report-tables.xlsx`（0.35 MB） | 报告 Table A–F 全套 |
| `dominion-documentation.pdf`（0.83 MB） | Dominion 致 PJM 负荷分析组的说明函（2026-01-06），**三类合同定义 + 4 GW/47 GW/16.6 GW 原始出处** |
| `dominion-vo-documentation.pdf` | DOM 电压优化调整说明 |

获取方式：`www.pjm.com` 对非美国出口重置 TLS，选美国节点后运行
`pwsh scripts/fetch_pjm_load_forecast_refs.ps1`（已验证 5/5 成功；脚本先打印出口国家，非 US 告警，
并逐文件做 zip CRC / PDF `startxref` 校验）。

### 3.1 DOM 分区峰值预测（`2026-load-report-data.xlsx` → `DOM` 表）

派生表：`data/processed/model_inputs/pjm_dom_load_forecast_v1/`

| 年 | 2026 | 2030 | 2035 | 2040 | 2046 |
|---|---|---|---|---|---|
| DOM 夏季峰值 (MW) | 25,193 | 31,939 | 40,855 | 50,730 | 56,242 |

2026→2046 峰值翻倍以上（+123 %）。注意这是 **DOM 全区负荷**（含居民/工商业），不是数据中心单项。

### 3.2 数据中心负荷口径：Dominion 说明函原文（可直接引用）

- 「the Company currently serves the largest data center market in the world with a **2025 coincident peak
  of 4 GW**」——你说的"2024 年底突破 4 GW"应改为**2025 年同时峰值 4 GW**（原文如此）。
- 「as of July 2025, the capacity value of these contracts is **47 GW (9.8 ESA + 7.1 CLOA + 30.1 ELOA)**」
- 「The Company is **forecasting 16.6 GW of demand by 2046**, not the 47 GW of capacity.」
- 三类合同的定性区别（原文）：**ELOA**「are **not** considered firm load」，其容量合计只是"potential
  long-term growth"；**CLOA** 是已开工、需承担成本并在通电前签署 ESA；**ESA** 是"已接入系统"的合同，
  合计为"near-term growth potential"。

→ 这直接印证上一节的修正：**不能把 7.5 GW（那是 2024-07 的 ELOA 一项）或 47 GW（合同容量合计）
写成"已并网负荷"**；已接入的是 ESA（2025-07 为 9.8 GW），而 Dominion 自己预测 2046 年数据中心**需求**
为 16.6 GW。论文引用时请按 ESA / CLOA / ELOA 三类分别标注，并区分 capacity 与 demand。

## 4. 校验

每个 `upstream/` 目录有 `SOURCE_OBJECTS.json` 与 `SHA256SUMS`；顶层清单 22 个文件全部字节与 SHA-256 复核通过。
PDF 用 `%PDF` + `%%EOF` + `startxref` 偏移校验，xlsx 用全成员 CRC，CSV 核对行数与时区列。
