# 快速身份编码的normal执行链后继

日期：2026-09-27。状态：DRAFT_NONAUTHORITATIVE。

前置证据为`rq2_identity_stream_fast_v1.md`中的真实H25零求解对照：完整内容摘要一致，
本次身份计算约减少30%。本轮将该编码接入独立模型、内核、来源执行和声明入口；
旧实现、冻结配置及历史执行工件不变。

## 模型与内核

`continuous_grid_normal_stream_fast.py`复用既有数学模型和assignment审计，仅使用新编码
及独立CONTRACT/implementation identity。变量、目标、约束、初态残余dwell、完整赋值要求、
残差和integrality阈值、chronology与terminal carry全部保持。内容witness类型仍为旧类型，
只证明内容，不认证旧实现运行。

`normal_execution_stream_fast.py`保持全部输入/执行身份复核的位置，以及私有快照、
admission build、native/canonical build、witness audit、peak/time/payload门。
复用旧NormalExecutionBudget与native solver，独立CONTRACT和owned类型
`FastStreamingNormalExecutionResult`区分实现。旧stream及原始execution pin均不能授权新内核。
最多一次求解，timeout/无解/gap/失败仍unresolved；缺完整raw时调用次数unknown。
同步资源检查不是硬限额，仍须外层Job监督。结果payload按原编码计量，接受仍要求
原生optimal、完整无错witness与terminal carry，不把可行未最优结果改为accepted。

## 来源与声明入口

`source_normal_execution_stream_fast.py`消费独立新normal/source execution pins，返回
`FastStreamingSourceNormalExecutionResult`。前后来源绑定、私有输入快照、结果type与
身份/接受一致性核验保留。依赖清单同时绑定旧identity_stream（prepare/binder仍使用）
与新identity_stream_fast（kernel使用）。来源/prepare/binding实现和内容pins保留原含义。

`normal_declared_execution_stream_fast.py`通过原stream prepare重建来源，再调用新source入口，
返回`DeclaredFastStreamingNormalResult`。独立声明pin与前后声明复核保留；before_source
仍在完整prepare和lineage核对之后、source调用之前执行。缺owned返回保持unknown，
post-source/声明失败保留完整已返回调用证据，不自动重试。

这些入口还没有接入持久化日志、独立replay、固定worker和controller。下一必要工作为其
独立后继连接及小型完整回放验证，再做真实H25受限任务；不能用旧store/controller消费新type。

## 验证与边界

模型全矩阵差分覆盖H1/H25/H49和四组commitment/minimum dwell/age；这些为合成规模。
assignment功率、flow、integrality、reserve和缺变量反例与旧oracle一致。
tiny native例、数值与资源故障、返回证据、调用记账、实现漂移、旧pin拒绝与旧路径禁用均验证。

新旧模型/kernel及fastidentity相关命令：
`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_continuous_grid_normal_stream_fast_v1.py tests/test_rq2_normal_execution_stream_fast_v1.py tests/test_rq2_continuous_grid_normal_stream_v1.py tests/test_rq2_normal_execution_stream_v1.py tests/test_rq2_identity_stream_fast_v1.py`，
204 passed in92.74s。独立模型/kernel关键矩阵、witness、数值门与旧pin/路径隔离31 passed
in14.64s，差分审查未发现实质finding；限定pre-seal，不生成official verdict或receipt。

本轮不提供真实H25 fast kernel耗时或assignment证据，不能宣称原60秒门已过。
原真实任务仍为无解返回且超时门unresolved；身份微测量不是完整执行结果。
初态与业务功率映射仍属机制假设；所有formal/engineering authority保持false。
current/episode、完整UID/四臂资源、恢复右删失、风险分母、科学注册与正式启动门继续开放。

来源/声明首轮68 passed in135.60s。补两项旧pin隔离后，与stream prepare/binder的相关回归
115 passed in157.36s，命令为相同pytest选项加以下四文件：
`test_rq2_source_normal_execution_stream_fast_v1.py`、
`test_rq2_normal_declared_execution_stream_fast_v1.py`、
`test_rq2_normal_task_inputs_stream_v1.py`、`test_rq2_pair_normal_stream_v1.py`（均在tests目录）。
独立来源/声明完整tiny入口和旧pin拒绝4 passed in9.71s。

审查发现before_source虽保留，但新入口缺直接失败窗口测试；新增四项覆盖prepare完成、
lineage及声明复核后callback抛错，source/native均禁入；noncallable在prepare前拒绝；
prepare后lineage/声明漂移阻止callback/source。未改源码。最终定向命令：
`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_declared_execution_stream_fast_v1.py -k "callback or before_source"`，
9 passed,27 deselected in18.13s，含四项新增和五项既有相关反例。
115项回归运行时尚未包含新增四项，不将两批记录写为一次最终119项整组通过。

| 文件 | 本轮SHA256 |
|---|---|
| continuous_grid_normal_stream_fast.py | `9a894e460e266b88d5a69077c2d594856f2dd4d85040eade6eef362b66bd37e4` |
| normal_execution_stream_fast.py | `dfff06ae0b346d07b79439848367de64aa7cba3434cc3c66f7710635ac72e9f0` |
| source_normal_execution_stream_fast.py | `cd80cd7180d25355206781d62287ebcaa1996862e99bb1a3b8e13e2e84a6cd99` |
| normal_declared_execution_stream_fast.py | `fc26322b49a82aba2c765f0a1bb6fea21d91c2114331732ad22ce6a9e2935d11` |
| test_rq2_continuous_grid_normal_stream_fast_v1.py | `1d15070486939195738ef2078ea5c3759ba26356b1b269c03d4fccf8f1b2eb2f` |
| test_rq2_normal_execution_stream_fast_v1.py | `c30951eb5148994a26db9f37c4a54650fb9ed3b76ca2f734379c6bbda0ef4828` |
| test_rq2_source_normal_execution_stream_fast_v1.py | `8e58a5ad19e6a2006e6d1ccbd05f2a12793abef7ce36197c322ec1b71a74ee18` |
| test_rq2_normal_declared_execution_stream_fast_v1.py | `c184802cf19b38bf23b2f96d7500694f342fc6303c1fcb638429245a94a7431d` |

模型/source文件位于src/rq2_joint_deliverability_boundary_v1，测试位于tests。
八批历史188项工件bytes/SHA全部一致；本轮未创建新的真实年度运行结果。

末次独立callback四项8.10s通过，测试覆盖缺口闭合；来源/声明fast层限定pre-seal范围
无开放实质finding。相关回归已终态，最终test SHA与上表一致；不生成official receipt或运行授权。
