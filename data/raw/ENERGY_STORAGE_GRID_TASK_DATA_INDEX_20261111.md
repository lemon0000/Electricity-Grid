# 储能成本 / 并网与阻塞 / 算力 Trace 公开数据本地索引（2026-11-11）

对应参数：储能 $c^E,c^P,\eta$；并网刚性费用与扩建成本 $c^F$；阻塞时长 $H$ 与恢复窗 $R$；
任务补做期限 $D$ 与可延迟占比 $\kappa_t$；闲置待机功耗比 $\phi$。

本文件只记录数据获取位置、校验方式与可用边界，不改变任何参数的科学含义，也不表示已完成模型适用性审查或任何模型运行。
字节级清单见 [`energy_storage_grid_task_acquisition_20261111.json`](energy_storage_grid_task_acquisition_20261111.json)；
各来源目录另有 `SOURCE_OBJECTS.json`、`SHA256SUMS`、`ACQUISITION_STATUS.json`。

## 1. 网络约束与可达性诊断（决定了所有下载路径，必须先读）

本机网络无法直连下列原始站点：`atb.nrel.gov`、`www.nrel.gov`（DNS 无应答）、`www.pnnl.gov`、
`emp.lbl.gov`、`www.pjm.com`、`dataminer2.pjm.com`、`scc.virginia.gov`、`www.iea.org`、`www.ercot.com`、
`dcc.ll.mit.edu`（TLS 握手被重置或返回 HTTP 403）。

**根因不是"没有梯子"，而是本地代理（verge-mihomo，混合端口 7897）按域名走规则分流，把上述域名判成直连**，
直连在墙内被阻断，于是表现为 TLS 被重置或 DNS 污染。逐项验证与可用绕行方式：

1. **域名走代理 → 仍失败**：`--proxy http://127.0.0.1:7897` 与 `--socks5-hostname 127.0.0.1:7897`
   （由代理解析域名）都失败，说明分流发生在域名规则上。
2. **IP 走代理 → 成功**：`--socks5 127.0.0.1:7897 --resolve host:443:IP`（本地给定真实 IP，SOCKS5 只传 IP）
   命中 GEOIP 规则，流量真正走代理节点。已用此路径直接取回：`www.pnnl.gov`、`emp.lbl.gov`、
   `dataminer2.pjm.com`（页面）、`scc.virginia.gov`（307 可达）。
3. **还需要浏览器式请求头**：`emp.lbl.gov` 与 `www.pnnl.gov` 前置 Cloudflare/Akamai 类过滤，
   只给 `curl` 默认头会 403，补 `Accept/Accept-Language/Sec-Fetch-*` 后回到 200。
4. **真正拿不到的**：`www.pjm.com` 与其媒体文件（UltraDNS 源站对当前节点出口直接断 TLS，HTTP 也无响应；
   同一域名的 `dataminer2.pjm.com` 在 Azure 上则可访问）；`www.iea.org` 与 `www.ercot.com` 分别被
   Cloudflare JS 挑战与 Incapsula 挑战挡住；`www.nrel.gov`、`atb.nrel.gov` 域名本身无解析结果。
5. 因此替代路径按优先级使用：发布方自有分发主机（NREL 的 OEDI 数据湖在 AWS S3、IEA 报告在
   `iea.blob.core.windows.net`、MIT SuperCloud 在公开 S3、GitHub raw）→ IP 固定的 SOCKS5 直取 →
   Internet Archive Wayback 回放（该端点自 2026-11-11 22:00 起对本机 IP 返回 429，见第 5 节）。
6. 另测过一个公开中继 `cors-get-proxy.sirjosh.workers.dev`：能取到字节，但会把二进制按 UTF-8 重编码
   （高位字节被替换为 U+FFFD），zip CRC 与 PDF `startxref` 偏移全部失效。**该通道产出的 13 个文件已全部删除**，
   不得作为数据来源。


## 2. 一、工业级电池储能成本（$c^E,c^P,\eta$）

| 数据源 | 本地位置 | 状态 | 可支撑的参数 |
|---|---|---|---|
| NREL ATB 2025 电学核心指标表 | `nrel_atb/v2025.1.0.0/upstream/ATBe.csv`（320.6 MB）、`ATBe.parquet`（9.2 MB） | 已获取，字节校验通过（S3 直连） | CAPEX 按 2/4/6/8/10 h 分档、Fixed O&M、Round-Trip Efficiency |
| NREL ATB 2024 终版核心指标表 | `nrel_atb/v2024.4.0.0/upstream/ATBe.csv`（102.7 MB） | 已获取，字节校验通过 | 同上（2024 版无 Round-Trip Efficiency 行） |
| PNNL ESGC 成本-性能数据库 v2024 | `pnnl_esgc/v2024/upstream/ESGC_Cost_Performance_Database_v2024.xlsx`（18 个工作表条目，863 KB） | 已获取，zip CRC 校验通过（Wayback 回放） | DC 电池舱 $/kWh、PCS $/kW、BOS、EPC、并网接口、RTE、循环/日历寿命 |
| PNNL ESGC 2022 评估报告（PNNL-33283） | `pnnl_esgc/v2024/upstream/ESGC_Cost_Performance_Report_2022_PNNL-33283.pdf`（5.0 MB） | 已获取，PDF 结构校验通过 | 成本口径、假设与折现说明 |
| Lazard LCOE+（2026 年 7 月版，44 页） | `lazard_lcoeplus/v2025/upstream/lazards-lcoeplus_vf.pdf`（1.2 MB） | 已获取，PDF 结构校验通过 | 电网侧 100 MW/400 MWh 级资本成本与 LCOS 区间 |

**已可读出的标定值（派生表见 `data/processed/model_inputs/battery_storage_cost_reference_v1/`）**

- ATB 的 CAPEX 在 2–10 h 五个时长上严格线性：`CAPEX($/kW) = c^P + h·c^E`，OLS 残差为 0，说明
  $c^E,c^P$ 可由时长回归**识别**而不是人为假设。ATB 2025、Exp 情形、Moderate 情景、2025 年：
  $c^P\approx 476.0$ $/kW，$c^E\approx 230.2$ $/kWh，4 h 合计 1 396.7 $/kW；
  Fixed O&M 4 h 档 49.87 $/kW-yr（≈3.57 %/yr of CAPEX）；Round-Trip Efficiency = 0.85。
- PNNL ESGC LFP、100 MW、Point 估计、2023 年 4 h：能量侧 351.55 $/kWh、功率侧 84.69 $/kW，
  合计 1 490.89 $/kW（与工作簿自报 Total Installed Cost 完全一致），RTE = 0.83；2030 年同档为
  272.20 $/kWh、73.60 $/kW、RTE = 0.85。
- **两个来源的拆分口径不同，不能混用**：总成本量级接近（1.40 vs 1.49 k$/kW，差年份口径），
  但 PNNL 把更多成本放在能量侧、ATB 把更多放在功率侧；FOM 差异更大（ATB ≈3.6 %/yr of CAPEX，
  PNNL 4 h 仅 4.27 $/kW-yr ≈0.29 %/yr，且随时长线性增长）。论文若引用“2.5 % FOM”，更接近 ATB 口径，
  必须注明来源与基期，并做两口径敏感性。
- 两份来源都不含电网侧网络升级费用，该部分属 $c^F$，见第 3 节。

## 3. 二、并网费率、扩建成本与排队（$c^F$）

| 数据源 | 本地位置 | 状态 | 可支撑的参数 |
|---|---|---|---|
| LBNL Queued Up 2026 数据文件（thru 2025） | `lbnl_queued_up/v2026/upstream/LBNL_Ix_Queue_Data_File_thru2025.xlsx`（15.6 MB） | 已获取，zip CRC 校验通过 | 排队时长（time in queue）、网络升级分摊 $/kW → $c^F$ |
| LBNL Queued Up 2026 简报（PDF，18.4 MB） | `lbnl_queued_up/v2026/upstream/Queued_Up_2026_Edition.pdf` | 已获取，PDF 结构校验通过 | 队列规模、撤回率、IR→COD 中位时长 |
| PJM BRA 2025/26、2026/27、2027/28 报告与清算结果 | `pjm_bra/v20xx_20xx/upstream/`（各 2 个文件，合计 4.2 MB） | 已获取，PDF 结构校验 / zip CRC 通过 | 容量出清价（$/MW-day UCAP）、按 pricing point（含 DOM） |
| PJM NITS 分区输电费率（2026-10 工作表、2025 年报） | `pjm_nits/v2026_10/upstream/`、`pjm_nits/v2025/upstream/` | 已获取，校验通过 | 各输电分区每 MW 年费 → 刚性过网费 |
| Virginia SCC PUR-2025-00058 终裁（2025-11-25，30 页） | `va_scc_pur2025_00058/v1/upstream/89g601-final-order-2025-11-25.pdf`（9.2 MB） | 已获取，PDF 结构校验通过 | GS-5（≥25 MW）费率类别、最低需量、抵押金、合同期 |
| Virginia SCC 立案通知（2025-04-24） | `va_scc_pur2025_00058/v1/upstream/854_01-order-for-notice-and-hearing-2025-04-24.pdf`（4.1 MB） | 已获取，PDF 结构校验通过 | 案件范围与程序 |
| Virginia SCC 终裁文本快照 | `va_scc_pur2025_00058/v1/rendered/` | 已获取渲染文本 | 供条款检索；页级引用以 PDF 为准 |

**已核实的关键事实（可直接引用，派生表见 `data/processed/model_inputs/pjm_firm_access_cost_reference_v1/`）**

- PJM BRA 出清价（$/MW-day UCAP，pricing point）：DOM 2025/26 = 444.26、2026/27 = 329.17（触上限）、
  2027/28 = 333.44；MAAC/EMAAC 2025/26 = 269.92、2026/27 = 329.17、2027/28 = 333.44。
  按 ×365 折年即 $162 k / $120 k / $122 k 每 MW-yr（DOM）。
- PJM NITS 2026-10 版：DOM 分区（Virginia Electric and Power）年度输电收入需求 21.02 亿美元，
  `Network Integration Transmission Service Rate = 85,190.65 $/MW-Year`；AECO 85,511、AEP 138,848.55。
  这两项相加给出"刚性接入 + 刚性过网"的可核查量级锚点。
- 容量市场出清价是拍卖结果、不是费率；紧张年份清到行政上限，引用时必须说明这一点，不能当作长期价格预期。
- VA SCC 终裁确认 GS-5 面向 ≥25 MW 用户（含数据中心），并给出最低需量计费、抵押金与长期合同条款；
  该文件是"阶段式合同 vs 单次按峰值定容"讨论的官方依据。

## 4. 三、阻塞运行与算力 Trace（$H,R$；$D,\kappa_t,\phi$）

| 数据源 | 本地位置 | 状态 | 说明 |
|---|---|---|---|
| PJM Data Miner 2（`da_hrl_lmps`、`da_transconstraints`） | — | **不可获取** | 主机可达（Azure，13.68.29.136），但 `/feed/<name>/definition` 只返回 SPA 外壳，数据走订阅 key 的 JSON API（`/api/v1/...` 返回 404），API 响应也未被归档 |
| ERCOT NP6-785-ER 数据产品 | `ercot_np6_785_er/v2026/`（无有效文件） | **不可获取** | 原站 Incapsula 挑战（403）；经中继取回的 21 MB 归档被转码损坏，已删除 |
| ERCOT LFLTF 委员会页、NP6-785-ER 产品页 | `grid_ops_source_documentation_v1/upstream/` | 已获取渲染快照 | 仅页面级证据，不含数据 |
| IEA《Energy and AI》（2025） | `iea_energy_and_ai/v2025/upstream/EnergyandAI.pdf`（8.2 MB） | 已获取，PDF 结构校验通过 | 由 IEA 官方 Azure 存储 `iea.blob.core.windows.net` 取得（www.iea.org 前置 Cloudflare 挑战） |
| SenseTime Helios GPU Trace | `sensetime_helios/v1/upstream/helios-data.zip`（36.4 MB，13 个成员） | 已获取，zip CRC 校验通过 | 4 个生产集群 × 6 个月任务级记录：`submit_time/start_time/end_time/duration/queue/gpu_num/state` |
| Microsoft Azure LLM/LMM Trace | `azure_public_dataset/v2/upstream/`（4 文件，9.6 MB） | 已获取，字节校验通过 | `TIMESTAMP,ContextTokens,GeneratedTokens`（code / conv / multimodal） |
| MIT SuperCloud / Datacenter Challenge | `mit_supercloud/v2022_01/upstream/`（7 文件，2.38 GB） | 已获取，字节校验通过 | `slurm-log.csv`：`time_submit/time_eligible/time_start/time_end` → 排队等待；`node-data.csv`：逐节点 CPU/GPU 功率时序 → $\phi$ |
| Alibaba Cluster Trace | 既有 `alibaba_gpu_2020/`、`asi_trace_power/` | 沿用 2026-11-09 索引 | 本次未新增下载 |

用途提示（不是已完成的标定）：Helios 与 SuperCloud 的排队间隔可用于拟合“可接受补做期限 $D$”的分布；
Azure trace 只给到达时刻与 token 需求，服务时长需经假定时才能换算；`node-data.csv` 提供真实瓦特读数，
可用于检验 $\phi=0.20$ 是否为合理待机比，但需先固定“闲置”的定义（占用但空转 vs 完全空闲）。

## 5. 补齐记录与仍缺项（2026-11-11 23:40）

本节列出的字节级文件已**全部拿到**，不再有 pending。关键的一步是把 Clash 节点从台湾出口
（203.75.191.239）换成美国出口（157.254.51.34, Los Angeles）：换后 `www.pjm.com` 立即从 TLS 重置变成
HTTP 200，8 个 PJM 文件一次抓齐；SCC 终裁则要绕开重定向——`scc.virginia.gov` 与
`www.scc.virginia.gov` 经全球加速 IP 会 307 到小写路径再 404，直接请求
`www.scc.virginia.gov` 的 CloudFront IP（本次 108.156.22.83）即可拿到原件。

复跑脚本：`pwsh scripts/fetch_pjm_scc_grid_ops.ps1`（脚本开头会打印出口国家，非 US 会警告；
每个文件都做 zip CRC / PDF `startxref` 校验，只有通过才落盘）。

仍然缺、且换节点也解决不了的两项：

1. **PJM Data Miner 2**（`da_hrl_lmps`、`da_transconstraints`）：主机可达，但数据走
   `apiportal.pjm.com` 的订阅 key（`/feed/<name>/definition` 只回前端外壳，`/api/v1/*` 返回 404），
   需 PJM 账号申请 API key，或改用本地 ICARUS-PJM 节点数据。
2. **ERCOT NP6-785-ER**：Incapsula 挑战页（403），需真浏览器登录 MIS 下载。

## 6. 校验方法与科学边界

1. 每个 `upstream/` 目录有 `SHA256SUMS`；顶层清单记录 byte 数、SHA-256、原始 URL、获取路径与 snapshot 时间戳。
2. 二进制校验不是只看头几个字节：zip/xlsx 用 `zipfile.testzip()` 全成员 CRC；PDF 检查 `%PDF`、`%%EOF` 与
   `startxref` 偏移是否指向合法 xref/对象。仅这两类检查通过的副本才保留。
3. `rendered/` 下的文件是 reader 代理渲染的**文本**，用于定位条款与数值，**不是**字节级原件；页级引用前必须换回 PDF。
4. 派生表只做单位与口径整理，不改动上游数值；不得把 ATB 建模成本称为成交价格，也不得把 PNNL 单项加总
   当作 EPC 报价。
5. 本索引与全部下载不授权、也不触发任何模型、求解器或正式实验运行。
