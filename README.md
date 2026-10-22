# Electricity-Grid

智算中心达产过程中的分阶段接入与柔性可交付性研究。

面向一个固定接入点，分别表示业务增长、计算设备分批投运和电网扩建进度，评价业务柔性能否支撑给定的分阶段接入计划，并解释任务恢复与小时CFE在哪些阶段限制履约。

## 从这里开始

| 要看什么 | 入口 |
|---|---|
| 给导师的中英文介绍、PDF与研究框架 | [项目介绍](paper/drafts/README.md) |
| 当前目标、模型不变量与执行规则 | [agent.md](agent.md) · [AGENTS.md](AGENTS.md) |
| 当前执行进度与下一步 | [科研项目执行步骤](docs/plan/科研项目执行步骤.md) · [交接入口](docs/plan/continuation_handoff_20261022.md) |
| 尚未解除的阻塞与运行边界 | [blocker登记](docs/model_spec/blocker_register.md) |
| 当前阶段评价规格 | [最小阶段评价规格](docs/model_spec/staged_deliverability_minimum_spec_v1.md) |
| 项目文件用途与科研skill选择 | [目录与技能说明](docs/plan/项目目录与科研技能.md) |
| 旧实验、repair与验证流水 | [截至2026-10-22的历史研究记录](docs/review/project_history_20261022.md) |

## 目录用途

| 目录 | 内容 |
|---|---|
| `paper/` | 当前介绍、论文文字、原始插画与导出图件 |
| `docs/plan/`、`docs/model_spec/` | 执行计划、交接、科学规格与阻塞登记 |
| `docs/literature/`、`docs/review/` | 文献证据、引用核对与审阅记录 |
| `src/` | 模型、网络、运行与审计实现 |
| `experiments/`、`scripts/`、`configs/` | 实验入口、辅助脚本和配置 |
| `tests/` | 测试源码，验证余额、期限、网络、保存及重开等行为 |
| `data/` | 原始数据、来源信息与可重建的处理数据 |
| `results/` | 运行工件、失败记录、检查点、表格与验证证据 |
| `environments/` | 专用执行环境声明；常规依赖见[requirements.txt](requirements.txt) |

`__pycache__`、`.pytest_cache`和`.ruff_cache`是可重建缓存。三个根目录`.backup_repair009*`保留旧runner、配置和候选检查点，仍被历史对照及审计引用；具体用途见[目录说明](docs/plan/项目目录与科研技能.md)。

## 既有科学协议

当前阶段研究与既有冻结协议分别按自己的规格解释。[联合服务可交付前沿v1](docs/plan/RQ2_联合服务可交付前沿确认性方案_v1.md)及其[后继v2](docs/plan/RQ2_联合服务可交付前沿确认性方案_v2.md)保留原定义：`I_joint = D_J - max(D_N,D_C)`，`I_joint = I_sep + A_B6`。历史开发验证、失败和预审状态以对应记录为准。

2026-10-23文件整理的删除范围、保留原因和访问限制见[清理记录](docs/review/project_cleanup_20261023.json)。
