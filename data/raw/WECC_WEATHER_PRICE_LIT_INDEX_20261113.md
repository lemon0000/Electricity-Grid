# 2020 气象 / RTS-GMLC 拓扑 / 迁移开销 / 西岸电价 数据索引（2026-11-13）

对应需求：用 2020 年逐小时实测气象替换 TMY3；核对 RTS-GMLC 母线—区域映射与支路限值；
标定跨园区迁移开销；为三园区选址提供真实电价基准。

字节级清单：[`wecc_weather_price_lit_acquisition_20261113.json`](wecc_weather_price_lit_acquisition_20261113.json)。
本文件只记录数据位置、校验与口径边界，不构成模型运行或参数已校准的结论。

## 1. 2020 年逐小时气象（替换 TMY3）

| 文件 | 站点 | 位置 |
|---|---|---|
| `weather_phoenix_2020.csv` | 凤凰城 33.4484, -112.0740（Area 2） | `openmeteo_2020_3sites/v1/upstream/` |
| `weather_lasvegas_2020.csv` | 拉斯维加斯 36.1699, -115.1398（Area 1） | 同上 |
| `weather_losangeles_2020.csv` | 洛杉矶 34.0522, -118.2437（Area 3） | 同上 |
| `weather_phoenix_2020_america_phoenix_tz.csv` | 凤凰城，本地钟时版（见下方时区说明） | 同上 |

- 来源 Open-Meteo 历史归档（ERA5 再分析），`temperature_2m` / `relative_humidity_2m`，逐小时。
- 每个文件 **8784 行、零缺失**，覆盖 2020-01-01 00:00 → 2020-12-31 23:00，含 2 月 29 日的 24 小时。
- 统计量（可用于先验核对）：凤凰城 −0.3…46.9 °C、平均 RH 31 %；拉斯维加斯 −2.6…45.3 °C、平均 RH 24 %；
  洛杉矶 2.0…44.0 °C、平均 RH 60 %。区域温差与湿度差显著，适合做 PUE/干冷器效率对比。
- **时区口径（重要）**：三个文件都按你给的链接用 `timezone=America/Los_Angeles` 请求。这对拉斯维加斯和
  洛杉矶是本地钟时，但凤凰城全年为 MST（UTC−7，无夏令时），因此**冬季**（PST，UTC−8）的凤凰城小时标签
  会整体偏移 1 小时，夏季因洛杉矶进入 PDT（UTC−7）而一致。为避免这个静默错位，另存了
  `weather_phoenix_2020_america_phoenix_tz.csv`（`timezone=America/Phoenix`）：与 RTS-GMLC 负荷做逐小时
  对齐时应用这一份，或明确声明采用统一太平洋时区并把偏移写进方法。

## 2. RTS-GMLC 拓扑与负荷（本地已有，本次只做核对）

| 文件 | 位置 | 核对结果 |
|---|---|---|
| `bus.csv` | `rts_gmlc/v0.2.3/upstream/RTS_Data/SourceData/` | 73 条母线，含 `Area`、`lat`、`lng`、`Zone`、`Sub Area` |
| `branch.csv` | 同上 | 120 条支路，含 `Cont Rating` / `LTE Rating` / `STE Rating` / `Perm OutRate` / `Length` |
| `DAY_AHEAD_regional_Load.csv` | `.../timeseries_data_files/Load/` | 8784 行（Year/Month/Day/Period + 三个 Area 列） |

- **母线—区域映射**：Area 1 = 101–124（24 条），Area 2 = 201–224（24 条），Area 3 = 301–325（25 条）。
- **2 月 29 日结论**：负荷表 8784 行即**包含** 2020-02-29 的 24 小时。所以气象序列不应剔除 2/29，
  否则会整体错位 24 小时。若既有 E1 容量表按 8760 行建立，需要显式声明并做重采样，而不是无声删除。
- 支路限值列可直接用于生成 N−1 故障下的联合可送达多面体线性约束（`Cont Rating` 为长期额定，
  `LTE`/`STE` 为短期与应急，选择哪一列必须与故障持续时间假设一致）。

## 3. 跨园区迁移开销（文献标定）

| 文件 | 位置 | 用途 |
|---|---|---|
| `varuna_arxiv2111.04007.pdf` | `elastic_training_migration_lit/v1/upstream/` | Varuna（arXiv:2111.04007，EuroSys'22）：checkpoint 与恢复开销、低成本大规模训练 |
| `oobleck_arxiv2309.08125.pdf` | 同上 | Oobleck（arXiv:2309.08125，SOSP'23）：故障/迁移后的重算代价与流水线模板恢复 |
| `b4_jain_sigcomm2013.pdf` | 同上 | B4（Jain 等，**SIGCOMM 2013**）：数据中心间广域网带宽利用与可用性 |
| `azure-network-latency.html` | `azure_wan_latency_doc/v1/upstream/` | 官方区域间 RTT 表 |

> **更正记录（2026-11-13 18:20）**：本批第一次下载用错了标识——arXiv:2104.06245 实为一篇实体检索论文、
> arXiv:2303.01866 实为碳纳米管物理论文、Google pubs 43837 实为 Jupiter Rising（SIGCOMM'15）而非 B4。
> 三份错误文件已删除，改用上面三个正确编号重新下载，并通过**抽取 PDF 正文标题**逐一核对
> （Varuna: Scalable, Low-cost Training… / Oobleck: Resilient Distributed Training… /
> B4: Experience with a Globally-Deployed Software Defined WAN）。教训：只校验 PDF 结构无法发现取错文献。

- Azure 官方表实测：West US ↔ West US 2 约 **19–25 ms**，West US 3 ↔ West US 2 约 **40 ms**。
  这比你拟用的 $5\sim12$ ms 更保守；两者口径不同——5–12 ms 对应直连暗光纤的城际往返，
  19–25 ms 含云区域汇聚。建议在论文里明确取哪一口径并给区间。
- 迁移窗口 $\tau^{mig}$ 与重算放大 $\gamma^{mig}$ 需要从 Varuna/Oobleck 的实测段落取值并注明页码，
  不能只写成"文献表明"。

## 4. 西岸三地工业电价（2020）

派生表：`data/processed/model_inputs/wecc_site_electricity_price_reference_v1/eia_industrial_price_az_nv_ca.csv`

| 州 | 对应区域 | 2020 工业电价（¢/kWh） |
|---|---|---|
| NV | Area 1 / 拉斯维加斯 | **5.61** |
| AZ | Area 2 / 凤凰城 | **6.07** |
| CA | Area 3 / 洛杉矶 | **14.27** |

南加州工业电价约为内华达的 2.5 倍，而洛杉矶夏季湿度高、干球温度略低（见第 1 节），
正好构成"电价差 vs PUE 差"的对照，可用于检验迁移价值判据。
原始表：`eia_state_electricity/v2026/upstream/avgprice_annual.xlsx`、`sales_annual.xlsx`（EIA 州级年度数据，止于 2020）。

## 5. 未获取项与原因

1. **LBNL 的 WECC/CAISO 输电升级成本表不存在**。LBNL「Generator Interconnection Costs to the Transmission
   System」数据集覆盖 MISO、PJM、SPP、ISO-NE、NYISO 五个 RTO，以及非 ISO 平衡区 Duke、PacifiCorp、
   Bonneville Power Administration；**不含 CAISO、APS、NV Energy**。因此需求里"下载页面中的 WECC / CAISO
   区域 Excel 数据表"无法从该站获得。可替代来源：CAISO 自身 cluster study 报表中的网络升级估算、
   PacifiCorp/BPA 的 LBNL 数据（WECC 内）、以及各州委员会/FERC 费率表中的 CIAC 条目。
   另外已核：本地的 `LBNL_Ix_Queue_Data_File_thru2025.xlsx`（Queued Up 2026）38,201 条项目记录里
   **没有**升级费用字段，只有 q_status/日期/county/state/region/utility/project_type/MW 等。
2. **Lu et al. (2026)**：在本仓库的草稿、文献矩阵与参考文献表中都检索不到这条引用，
   需要你给出完整题名或 DOI 才能抓取。
3. IEM ASOS 原始观测（需求里的方式 2）未下载：Open-Meteo 已给出零缺失的完整逐小时序列，无需备用源。

## 6. 校验

每个 `upstream/` 目录有 `SHA256SUMS` 与 `SOURCE_OBJECTS.json`（原始 URL、获取路径、SHA-256）。
二进制校验：PDF 检查 `%PDF`、`%%EOF` 与 `startxref` 指向合法 xref/对象；xlsx 用 `zipfile.testzip()` 全成员 CRC；
CSV 核对行数与时区列。全部 10 个文件通过。
