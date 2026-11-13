# 电网—任务耦合公开数据本地索引（2026-11-09）

对应参数清单：

- `docs/plan/empirical_grid_task_parameters_v2.json`
- `docs/plan/empirical_grid_task_coupling_benchmarks.csv`
- `docs/plan/empirical_data_sources_and_parameter_guide.md`

本索引只记录数据获取与位置，不改变参数的科学含义，也不表示数据已经通过模型适用性审查。

| 数据源 | 本地位置 | 获取状态与范围 |
|---|---|---|
| ASI / Alibaba 2026 `asi-trace-power` | `asi_trace_power/v1.0.1/upstream/` | 已获取代码、小时级衍生产品及 49 MB 聚合 Parquet；未获取约 351 GB 原始 pod 表 |
| Tiered-DC-CEM PJM/Korea | `tiered_dc_cem/v2/upstream/` | 已获取 Zenodo v2（record 22680958）完整包 `src.zip`，1,268,476,882 字节，整包 MD5 与记录一致（`2bb602b6…`），ZIP 完整性测试通过 |
| ICARUS-DC | `icarus_dc/327ef39ada1cff606ca191c3ce56f20224b92c3f/upstream/` | 已获取固定 commit 完整公开包；含 DCS_Full/PJM/New York 等记录 |
| ICARUS-PJM | `icarus_pjm/0cb6a1af86e2bdfc1d160f44b6e4a7518ca3ffe3/upstream/` | 已获取固定 commit 完整公开包；含 21 区、节点模型、时序和数据中心容量 |
| NLR GenAI Power | `nlr_genai_power_2026/v2/` | **原始 ZIP 未获取**：官方站点 TLS 握手失败；配置、下载器、论文和 ASI 再分析已存在，未用镜像替代 |
| Camus / Princeton PJM 分期接入 | `camus_flexible_data_centers_2025/v1/upstream/whitepaper.pdf` | 已获取完整报告；不含原始 SCADA 或网络模型 |
| 行业合同与规程证据 | `google_operational_flexibility_evidence_v1/current/upstream/` | 已保存可访问网页；NGED 与 NFM 因 HTTP 403 未获取，详见状态 JSON |
| 核心论文 | `../docs/literature/empirical_grid_task_20261109/` | 已保存核心 PDF/HTML 与 SHA256；CEM 论文仍在既有 `arxiv_three_papers_20261108/` |

## 使用前的科学边界

1. Alibaba 的生产调度记录是观测数据，但 MW 为模型重建值；持续时长曲面是未干预 eligible-power 统计，不是恢复后的可交付能力。
2. Tiered-DC-CEM 的层级比例和 Layer B/C 参数包含论文声明假设，不能称为统一电网合同实测值。
3. ICARUS 的空间、规划和网络数据不提供与 Alibaba 同址、同钟或同任务的配对关系。
4. NLR 原始数据包尚未落盘，不能宣称已具备该数据集的本地复现或动态校准能力。
5. 各目录 `SOURCE_OBJECTS.json`、`ACQUISITION_STATUS.json` 与 `SHA256SUMS` 分别记录来源、失败状态和字节校验；下载不授权或触发任何模型、求解器或正式实验。
