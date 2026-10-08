# Numeric normal 完整开发任务 controller

2026-09-27，DRAFT_NONAUTHORITATIVE。新增 `normal_task_controller_stream_numeric.py` 和 `experiments/audit_rq2_normal_task_stream_numeric_v1.py`，连接 numeric worker、capture 与三层 replay。保留两 Job 顺序执行、整 Job 静默后 capture、replay 后再次 capture、固定外部 pin 和父进程资源门。

新声明 `configs/rq2_normal_task_stream_numeric_h25_development_v1.DRAFT.yaml` 使用新任务根 `results/tables/rq2_normal_task_stream_numeric_h25_attempt1_non_authoritative`，仅更新 schema、root 和实现 pin。完整来源、机制初态、solver specification、normal 预算、两 Job/capture/controller 预算、environment、record/report 大小限制均与 fast 声明相同。H25/22275/28004、HiGHS 1.15.1、1 thread、1 秒、normal 60 秒、Job 768 MiB 和 controller 600 秒保持。

声明由旧 pin 通过验证后读取的小型 PairDeclaration 重算新实现链，未运行年度 prepare 或 solver。新测试明确逐字段比较旧/新数据和预算，并拒绝旧 fast 报告 tag（包括外层自洽重 hash）。controller 仍不接受回调或组装年度模型。

初始声明 SHA256 `6cc200dad82041d33ac83277d9067c32e63bc9d0d56428b949081a46b5243b0c`；controller pin `eb17872a206cf009d317ab8cf05971fcdda3663552f3cd10b0e8d851c9d6929c`。各层 pin 为 normal `1a2da00aea5e5ab8936f83207ec3a994205a996fa99629110a58d500f14abc28`、source `837212b20ac1e488c17b553e4bbeb14ef07780fff1a32d1820e010485c6fdd06`、declared `ae8986f02789434d206c15401df523ba1bbd28536fea5b8db64000964d44b199`、replay `d836885892a917600802ae4dd857b926e8ddad41ec5132e1e89a4b81bd16b513`。

只有本轮所需回归和独立 pre-seal findings 闭合才可进行一次既定受限 H25 开发验证；该 draft 不产生 production seal、official receipt 或 formal-run authority。

## 开发验证

compute Python `-B -m pytest -q -p no:cacheprovider tests/test_audit_rq2_normal_task_stream_numeric_v1.py tests/test_rq2_normal_task_controller_stream_numeric_reports_v1.py`：33 passed in 30.23s。controller 全组与独立审查终态另记。

同命令前缀运行 `tests/test_rq2_normal_task_controller_stream_numeric_v1.py`：61 passed in 211.84s，exit 0，覆盖 tiny 双 Job、退出/父死亡窗口和重 hash 报告等。独立 runner、旧/fast report tag、三态报告 13 passed in 7.90s；限定 controller/runner pre-seal 无实质 finding。上述 33 与 61 是分别运行的结果。

旧 334 条工件 bytes/SHA 重核一致，新声明 controller pin 再次计算保持。上述 controller 测试完成时，完整 H25 调用尚待 persistence/replay 全组终态；后续前置验证闭合如下。

persistence/replay 最终 118 passed in 754.68s，exit 0，配合 capture/worker 71 项和既有独立审查，完整开发链的前置测试条件已满足。controller/runner 的 61 与 33 项、独立 13 项均保持，上述脚本、声明和实现 pin 未变。本结论支持既定一次受限开发验证，尚不说明真实 H25 数值门已通过。

| 文件 | SHA256 |
|---|---|
| normal_task_controller_stream_numeric.py | `f725895f455f118452c845748c59c7b23a2e5bb8c6e62c042f881fdca1884a61` |
| audit_rq2_normal_task_stream_numeric_v1.py | `50cd24d39b3c532f0efc0f53ad2645d33eace067e11f2a1bbaea797ade281e35` |
| test_rq2_normal_task_controller_stream_numeric_v1.py | `6eaee4051f91d21d5bf9f40c43c132e093df7ca6d5fdc891196bc7b361ff47b0` |
| test_rq2_normal_task_controller_stream_numeric_reports_v1.py | `0fd3a6322008dcc4880db88056fcdd7f1ed9f12fe132a48d77b0a1832c3e56ce` |
| test_audit_rq2_normal_task_stream_numeric_v1.py | `fa58318cb8f3c03b85f3827311b8050ae204d08d7595a05b1dff67f582de29d9` |

controller 位于 `src/rq2_joint_deliverability_boundary_v1`，runner 位于 `experiments`，测试位于 `tests`。
