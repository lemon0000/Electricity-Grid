# Electricity-Grid

**计及任务补做期限、随达产状态变化的智算中心分阶段鲁棒接入设计。**

当前工作以2026-11-11确认的主线为准：设计各达产阶段的Firm容量与储能，或计算给定电网下的数据中心可接入规模。运行受延期补做期限和非预见性约束。现有demo为初步可行性证据。

## 当前入口

| 内容 | 入口 |
|---|---|
| 中英文介绍与阅读PDF | [论文材料](paper/drafts/README.md) |
| 研究目标、下一步与执行规则 | [agent.md](agent.md) · [AGENTS.md](AGENTS.md) |
| 当前计划与历史计划导航 | [计划目录](docs/plan/README.md) |
| 当前图件及历史源图 | [图件目录](paper/figures/README.md) |
| 科学规格与旧合同 | [规格目录](docs/model_spec/README.md) |
| 本次整理与恢复方法 | [整理记录](docs/review/project_cleanup_20261111.md) |

最新demo位于相邻 [ramp_flex_robust](../ramp_flex_robust/) 目录，其[可行性报告](../ramp_flex_robust/RESULTS_complete_v1.md)及[英文论文](../ramp_flex_robust/paper/paper_draft_en.pdf)不随本仓库Git自动发布。

## 目录用途

| 目录 | 内容 |
|---|---|
| paper/drafts/ | 当前双语介绍、PDF，以及具名历史论文片段 |
| paper/figures/ | 当前图件、历史SVG/PDF母版及生成脚本 |
| docs/plan/、docs/model_spec/ | 计划、交接、规格及冻结合同 |
| docs/literature/、docs/review/ | 文献来源、阅读和审阅记录 |
| src/、experiments/、scripts/、configs/、tests/ | 实现、实验入口、配置与测试 |
| data/、results/ | 数据、来源、实验输出、失败和检查点 |
| environments/ | 执行环境声明 |

旧D/E、H1、CFE和repair材料按原合同保留。三个根目录 `.backup_repair009*` 及 `repair009_chain.log` 仍被历史审计或代码使用；详细用途见[目录说明](docs/plan/项目目录与科研技能.md)。当前进展不要由旧交接的标题推断，以agent.md顶部日期条目为准。