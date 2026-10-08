# Numeric streaming normal 模型与来源执行后继

2026-09-27，DRAFT_NONAUTHORITATIVE。真实 H25 零 solver 对照已确认 numeric identity 的逐字节/摘要等价与局部计时改善，见 `rq2_identity_stream_numeric_v1.md`。本后继将该编码器接入模型、normal kernel、来源绑定与声明执行，不改旧 fast 文件及任何历史结果。

新增模块为 `continuous_grid_normal_stream_numeric`、`normal_execution_stream_numeric`、`source_normal_execution_stream_numeric` 和 `normal_declared_execution_stream_numeric`。模型和执行 CONTRACT 以及 owned result 类型使用 numeric 标识；新 pin 不能由旧 stream/fast pin 授权。

## 不变量和依赖

保持原完整矩阵、admission/solve/canonical 模型构建、deepcopy、构建前后和返回后的身份复核、同一 native solver adapter、一次调用与最优性/assignment/witness 共同验收。60 秒门、容差、线程、变量/约束上限和 payload/内存门全部保持。

numeric encoder 会回退到 fast 局部编码，因此 model implementation 显式绑定 `identity_stream_numeric.py` 和 `identity_stream_fast.py`。来源 adapter 同时绑定原 `identity_stream`（prepare/binder）、fast fallback 和 numeric；来源 prepare/binder 继续复用原 stream 模块，数据身份、机制初态和来源角色不变。

声明层保留 prepare 后、source 前的 `before_source` 运行态回调；回调失败不会进入 source，调用计数未知/返回缺失与中断的既有语义保持。所有 formal/security/causal/infeasibility authority 保持关闭。

## 验证记录

主命令前缀 `D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`。

numeric model/kernel/encoder 首轮 137 passed、1 failed in 40.21s；失败是新 fresh-import 测试的预期依赖清单漏列 fast fallback，实际 model pin 已显式绑定它。仅补该测试清单。最终 numeric model/kernel/encoder 加 fast encoder 四文件 179 passed in 45.27s。

覆盖 1/25/49 小时全矩阵差分、完整功率/流量/备用/整数/缺失赋值 witness、真实 tiny 单次求解、原 native 失败状态、资源门、owned result、旧 stream/fast pin 隔离及 fallback 源码漂移在建模前拒绝。后续来源/声明及独立审查终态另记。

来源/声明最终命令的文件集为 `tests/test_rq2_source_normal_execution_stream_numeric_v1.py tests/test_rq2_normal_declared_execution_stream_numeric_v1.py tests/test_rq2_normal_task_inputs_stream_v1.py tests/test_rq2_pair_normal_stream_v1.py`，121 passed in 138.24s，exit 0。

独立先行 4 项（fresh import 修复及模型/kernel），再对旧 pin/fallback/source/declared/callback 等 10 项测试取得 10 passed in 11.28s；结合两个完整终态，限定 pre-seal finding 闭合，不构成 official verdict。

| 新文件 | SHA256 |
|---|---|
| continuous_grid_normal_stream_numeric.py | `34c6c954c8d6f38c7e561b92a0d90c6b3871a2c8d75413b53991e4d3c573b7ce` |
| normal_execution_stream_numeric.py | `2fa2751b9f8fe4c3064a282d6800834566308527ae0fe660dfc7f2a57134f28a` |
| source_normal_execution_stream_numeric.py | `c6116297f40a49798a481f5ee7459daa8aa5cbf5818f7befa0840b46f817b221` |
| normal_declared_execution_stream_numeric.py | `677b92e858db9f83abd9fa5ecfc23895952d6af32454f66c1b904b0288e020d8` |
| test_rq2_continuous_grid_normal_stream_numeric_v1.py | `75f8ef0f779defaaa6d38bf1d719b64682f93b958e514b1fb3aacbfbfea4d96e` |
| test_rq2_normal_execution_stream_numeric_v1.py | `92337acd7d5f261f4aec430242431fb6c4019732a3e8d544dad5469ee5e47874` |
| test_rq2_source_normal_execution_stream_numeric_v1.py | `e3abf3aff13a6ace1c93557f38e239c7942771e0779e23fecf5b892e32ca0a17` |
| test_rq2_normal_declared_execution_stream_numeric_v1.py | `c9529996aad48c31066831f7ddb6b127852d36f10245e2bc1804e078f788831c` |

模块位于 `src/rq2_joint_deliverability_boundary_v1`，测试位于 `tests`。旧文件保持。

上述组件验证结束时尚无 numeric H25 完整任务结果，随后已完成日志/回放/worker/controller 接入和一次完整开发验证，见 `rq2_normal_task_stream_numeric_h25_development_v1.md`。新运行 normal 53.8714377 秒，未触发原 60 秒超时，但仍无可行解。旧 fast H25 的 63.528 秒和 unresolved 记录原样保留。下一项转向 native 求解阶段诊断；已有连续多日、恢复债务、拒绝动作、四臂和诊断组件不重复实现。
