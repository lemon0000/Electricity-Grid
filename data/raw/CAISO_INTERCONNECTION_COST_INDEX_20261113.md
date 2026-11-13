# CAISO 并网与输电升级成本数据索引（2026-11-13）

补的是上一批的缺口：LBNL 的并网升级成本数据集不含 CAISO，因此西岸三园区里的南加州一侧必须回到
CAISO 自身公开材料。本文件记录获取路径、拿到什么、以及可以直接引用的数字。

字节级清单：[`caiso_interconnection_acquisition_20261113.json`](caiso_interconnection_acquisition_20261113.json)。

## 1. 怎么拿到的（可达性）

`www.caiso.com` 在本机 DNS 无解析结果，直接连、走域名代理都失败。可用路径是
**SOCKS5 + 固定 CloudFront 边缘 IP（143.204.55.66）+ 浏览器请求头**；`/documents/<name>` 下的
PDF/XLSX 都走这条路取回。站点结构走 `https://www.caiso.com/sitemap.xml`（5589 条）导航到
`generation-transmission/generation/generator-interconnection/{queue-management,interconnection-request-study}`
与 `transmission/transmission-planning` 三个页面。

## 2. 拿到什么（20 个文件，2.4 MB）

`data/raw/caiso_interconnection/`

| 版本 | 内容 |
|---|---|
| `v2026/upstream/` | Cluster 16 队列报告、Cluster 15 互联申请、资源 ID 报告、队列管理状态报告模板、成本与成本遏制工作簿模板、**可靠性网络升级报销上限**、**紧急互联网络升级上限**、升级成本责任实施规则、2025 集群内可靠性升级优先序 |
| `v2025/upstream/` | 9 家 PTO 的 **2025 并网单位成本指南**（PG&E、SCE、SDG&E、LSPGC、DCR、DSLK、GLW、HWT、VEA） |
| `v2025_2026/upstream/` | TAC 高压资本成本估算 + 含新增资本的 TAC 预测模型 |

派生表：`data/processed/model_inputs/caiso_pto_unit_cost_reference_v1/caiso_pto_unit_costs_2025.csv`
（9 家 PTO、187 条单位成本，含设备类别 / 电压等级 / 单位 / 美元）。

## 3. 可直接引用的硬数字

**(a) 可靠性网络升级（RNU）报销上限，$/MW 装机容量**（CAISO 每年按 Handy-Whitman 指数调整，
2026-06-30 更新版）：

| 适用 COD 起始 | 上限 ($/MW) |
|---|---|
| 2026-07-01 | **104,947** |
| 2025-07-01 | 101,558 |
| 2024-07-01 | 96,112 |
| 2023-07-01 | 85,430 |
| 2022-07-01 | 76,011 |
| 2021-07-01 | 72,902 |
| 2020-07-01 | 71,687 |
| 2019-10-23 | 69,630 |

**(b) 紧急互联网络升级上限**：CAISO 费率 Appendix KK §3.10 判据 (d) 要求紧急网络升级低于
**100 万美元**（按同一方法逐年调整），超出即不得走紧急互联通道。

**(c) PTO 单位成本**（2025 指南，示例取自 PG&E，全部为规划级估算、非成交价）：

| 设备 | 电压等级 | 单位成本 |
|---|---|---|
| 完整 loop-in 变电站（设备 + 单条 gen-tie 接入 + 1 完整间隔 + 1 半间隔） | 60/70 kV | ≈ \$15.0 M |
| 同上 | 115 kV | ≈ \$16.0 M |
| 同上 | 230 kV | ≈ \$19.0 M |
| 单断路器位置 | 115 kV | ≈ \$2.2 M |
| 单断路器位置 | 230 kV | ≈ \$2.4 M |
| 单断路器位置 | 500 kV | ≈ \$6.7 M |
| 500/230 kV 4-1 相变压器组（375 MVA×4） | 500 kV | ≈ \$45.0 M |
| 230/115 kV 1-3 相（420 MVA） | 230 kV | ≈ \$11.0 M |

跨 PTO 的大项区间（同一类 500/230 kV 变压器组）：SCE ≈ \$90.8 M、SDG&E ≈ \$60.2 M、DCR ≈ \$54.5 M、
HWT ≈ \$51.5 M、GLW ≈ \$50.0 M、PG&E ≈ \$45.0 M —— 同一设备在不同 PTO 之间差异可达 2 倍，
**不能用一个平均单价替代全州**。

**(d) 队列规模**：Cluster 16 队列报告与 Cluster 15 互联申请给出项目级记录
（Queue/Project Number、项目名、燃料类型 1–3、NET MW 1–3、县、状态），可直接统计南加州侧
可接入的光伏/储能容量基数；Cluster 15 另含 `Withdrawn` 工作表。

**(e) TAC 高压资本成本估算**：可用于把网络投资折成输电接入费量级。

## 4. 与你原设 $2,660\text{–}6,500\ \$/MW\text{-}week$ 的口径对照（重要）

把上面 (a) 的上限换算成周口径：`101,558 \$/MW ÷ (14 年 × 52 周) ≈ 140 \$/MW-week`，
即使只按 5 年摊销也只有约 `390 \$/MW-week`。也就是说：

- **CAISO 的 RNU 报销上限是一次性的资本性上限（$/MW）**，不是周期性费率；
- 你写的 **2,660–6,500 \$/MW-week 量级（≈ 138k–338k \$/MW-yr）更像容量/输电服务的年费**，
  与 PJM 容量市场 + NITS 的量级（DOM：120k–162k 容量 + 85k NITS ≈ 205k–247k \$/MW-yr）同一档，
  而不是 CAISO 的 CIAC 型一次性上限。

结论：这两个数不能混用。建议在论文里把 $c^F$ 明确拆成
"一次性升级分摊（CAISO RNU 上限 / PTO 单位成本）+ 周期性容量与过网费（PJM BRA + NITS 口径）"两部分，
各自标源，避免被审稿人指出量纲不一致。

## 5. 还缺什么

1. **逐项目的网络升级美元金额**：在 CAISO 各 cluster 的 Phase I/II 研究报告 PDF 里（每份数百页），
   本次未抓。若需要"真实项目级升级成本分布"，可以指定 cluster（如 Cluster 15）后定向抽取。
2. 队列管理状态报告（`caiso-queuemanagement-statusreport.xlsx`）是**空模板**，只定义了字段
   （Precursor Network Upgrade、Network Upgrade ID、Est. In Service Date 等），不是数据。
3. 成本与成本遏制工作簿同样是**空模板**（Instructions / Capital Costs / O&M / Cost of Capital /
   Revenue Requirement / Cost Containment 等 11 个工作表），可用于说明 CAISO 的成本申报口径，
   不含项目实际数值。

## 6. 校验

每个 `upstream/` 有 `SHA256SUMS` 与 `SOURCE_OBJECTS.json`；xlsx 全部通过 `zipfile.testzip()` 全成员 CRC，
PDF 全部通过 `%PDF` + `%%EOF` + `startxref` 偏移检查。20 个文件、0 失败。
