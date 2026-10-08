# 流式来源 normal 执行与声明入口

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE。

## 入口和独立身份

`source_normal_execution_stream.run_source_normal` 接受新的完整
`StreamingSourceNormalAssembly`，要求独立保留的 source implementation、binder implementation、
assembly、pair、binding、normal input、normal execution、source execution pins。
新 source execution 身份绑定本模块及全部适配依赖、declaration 和这些外部 lineage pins。
构造结果使用新 owned 类型 `StreamingSourceNormalExecutionResult`，旧来源执行链保留。

入口持有输入私有快照，求解前后调用流式 binder 重建来源、核验 power/workload 对应。
除新 binding identity 字段外，直接重算其内容摘要，并核验旧内容 reference 的 body/hash、
assembly/input/pair 对应关系。旧 binding pin 不能授权新执行；旧内容 reference 不是旧代码执行证明。

`normal_declared_execution_stream.run_declared_normal` 接受 bounded
`NormalTaskSourceRequest` 和独立 request/declared execution pins；其他新 pins 同样必须外部提供。
它重读 pinned normal record、pair declaration、audit config，调用完整流式 prepare，
验证返回的 owned 类型、来源与 binding pins 和 mechanism/build-only role，再调用来源执行入口。
prepare 输出不用于自授执行 pin。返回前重核三份声明和实现身份，返回新 owned
`DeclaredStreamingNormalResult`，嵌套保留 source 与 kernel 原始数值证据。

declared execution 身份绑定本模块、当前 prepare/request 身份及独立 source execution 身份；
后者继续绑定 normal kernel、solver specification、budget 和预声明规模。
旧代码、冻结声明、历史失败与成功诊断工件均不修改。

## 接受与拒绝动作

| 阶段或情况 | 实际动作和证据 |
|---|---|
| prepare 前/后身份、角色或文件检查失败 | 拒绝进入来源执行，不调用 native |
| source 求解前重建或 pin 核验失败 | 来源入口抛出拒绝，不调用 kernel |
| 已进入下层但没有完整 owned 返回 | 外层保守记录 solver_calls=null、call_count_complete=false；不从异常位置推断零调用 |
| native timeout、gap、缺界或 assignment 失败 | 保留 kernel evidence，维持 unresolved；不生成不可行证书 |
| 已返回数值结果后 source 重建失败 | 保留 raw/witness 和已知调用数，source acceptance=false |
| source 已返回后声明/实现变化 | 保留全部 source result 与调用数，declared acceptance=false |
| 中断且没有完整返回 | interrupted、未知调用数；不自动重试 |
| 返回字段自洽性或 lineage 不符 | 保留返回证据但拒绝接受；成功布尔值不能覆盖身份与数值检查 |

声明入口接受要求完整来源对应、相同前后 binding、与 prepare 内容一致、精确 kernel
input/execution/specification/budget/scale，以及旧数值接受条件：一次调用、optimal、完整
assignment witness、terminal carry、无错误。入口不创建 current/事故输入，不消费恢复债务。

成功字段一致性检查不是完整归档 replay：timings、peak tuple、payload bytes 等完整资源元数据
仍由 exact pinned kernel 构造，后续独立 replay 必须逐项重验；当前不宣称能认证进程测量或抵御任意
Python 对象篡改。声明入口在 source 返回后另行重算 source/kernel 实现链，检测返回后的实现变化。

## 验证与资源边界

source wrapper 的 tiny native 测试 stub 来源边界，专门覆盖外部 pins、错返回类型、
timeout、来源事后变化、调用记账及接受一致性。声明入口正例使用实际流式 prepare、
来源重建、pair binder、normal 构模和原生 HiGHS，三小时合成网络的 objective=120、
terminal carry.source_hour=3。raw loader/公开 package 边界使用 synthetic fixture，
这不是 RTS-GMLC 真实规模证据，也不是观测业务参数的验证。

两个入口都是同步开发函数；`hard_resource_limits_enforced=false`、
`durable_invocation_tracking=false`、`formal_result=false`，observed_power_mapping=false，
initial state/workload-power 继续作为机制假设。kernel 的同步资源门不含来源准备与外层重建，
也不能强制终止 native 调用。年度快照共存的真实峰值尚未测量，调用必须放入后继 Job 监督链。

下一必要工作为流式结果持久化、独立重建与数值 replay，再接 controller/worker，
在原开发预算下验证真实 H25 全链。现有真实 H25 证据仍止于完整 prepare。
恢复右删失、风险分母、current/四臂完整执行、科学注册及正式启动门保持开放。

## 后继接入检查点

1. 以已实现一次性 SQLite intent/result 与独立 replay 为基础，新 schema 接受声明入口的
   nested result；不得把新类型伪装为旧 `SourceNormalExecutionResult`，旧数据库保持原状。
2. intent 必须先于一次执行入口调用落盘；prepare/source/kernel 任一异常后已有 intent
   均不授权自动重试，缺少完整返回仍是未知调用数。
3. replay 使用小型 pinned request 重建来源，逐项验证声明、source、kernel 的嵌套身份、
   完整数值赋值与资源字段；不能从保存的 terminal carry 推断 incoming origin。
4. controller/worker 的 Job 覆盖 prepare、全部快照、求解、归档与独立 replay。
   原资源预算保持，真实规模资源证据必须来自新的独立 non-authoritative root。

## 本轮工件

| 文件 | SHA256 |
|---|---|
| source_normal_execution_stream.py | `a6284d5fee8e34ef06af00d2262caa770a35e7c22103b2200935490c872b9608` |
| normal_declared_execution_stream.py | `c54e3f3cd38a8d6a543405e94be6fba5be6a1761544d2fce625b7daf563162cc` |
| test_rq2_source_normal_execution_stream_v1.py | `efa831ca05be0cf81a30b8d3ac0690f528f5e4b919bc1a1b5db753fa0071631d` |
| test_rq2_normal_declared_execution_stream_v1.py | `433eed72bd2c3ed7a2958cb67a534a1d94512e8867cee65bfc2b25c87ced0a7f` |

旧五批诊断索引22+13+11+13+15项bytes/hash复核一致。上述hash只是开发记录，
不构成production seal、official review receipt或运行授权。

## 验证记录

最终命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_source_normal_execution_stream_v1.py tests/test_rq2_normal_declared_execution_stream_v1.py tests/test_rq2_source_normal_execution_v1.py tests/test_rq2_normal_task_inputs_stream_v1.py tests/test_rq2_pair_normal_stream_v1.py tests/test_rq2_normal_execution_stream_v1.py -k "not real_pinned_h25_sources_reach_kernel_boundary_without_solver"`。

结果：201 passed, 1 deselected in155.96s。唯一排除项是旧入口未受Job限制的真实H25测试，
其年度编码路径已有内存失败证据；本轮不运行真实H25。新source与声明入口共68项，
其余为旧source语义、stream prepare、pair binder及kernel相关回归。`git diff --check` 无错误。

独立只读 R3 pre-seal 审查确认无开放实质finding；source wrapper 36项通过，新增contract反例
另行1 passed,36 deselected in2.93s，合计覆盖当前37项；声明入口31项通过。
审查覆盖旧内容reference与新执行身份分离、返回后身份链复核、拒绝/中断/未知调用数、
已返回证据保留和数值接受条件。资源metadata仍待独立replay，真实H25和Job整任务尚未验证。
本结论不是official verdict/receipt，也不授权运行。

## 2026-09-21 固定 worker 运行态检查接入

声明入口和日志的未seal draft 增加 before_source 运行态检查位置：日志 intent/readback 后准备输入，在source求解前执行固定worker postcheck。检查失败保留pending intent，不调用source、不自动重试；callback不进入header/result，也不作为认证证据。此改动改变draft implementation/execution pins，前文SHA与测试数字保留为历史记录；当前验证与精确SHA见 rq2_normal_task_worker_stream_v1.md。旧冻结工件保持原字节。
