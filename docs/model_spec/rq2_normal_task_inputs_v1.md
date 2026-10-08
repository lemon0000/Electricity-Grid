# Normal 整任务来源准备入口 v1

状态：DRAFT_NONAUTHORITATIVE。`normal_task_inputs.prepare_task_inputs` 从小型路径/哈希声明重建
完整输入，供后继受限任务子进程调用。本模块没有创建 Job、执行 solver、创建归档或恢复游标；
它是把准备移入受限任务范围所需的前置实现，尚不构成整个任务监督。

## 输入与复用

`NormalTaskSourceRequest` 明确给出现有 verified normal build-only JSON、pair YAML、audit YAML 的
绝对路径、独立 SHA256、各自字节上限，及 upstream root、独立 assembly/input/pair/binding/scale pins。
每份声明必须有 exact positive int 上限，且不超过 16 MiB；读取最多上限加一字节，拒绝 reparse、
多 hardlink、读前后文件身份变化、超限或摘要不符。不把完整 RTS 数据对象编码进 controller 的请求。

复用 `experiments.audit_rq2_power_normal_binding_v1.declared_inputs` 的既有纯解码函数，
只调用该函数，不调用 runner 的 main、derive、写文件或 argparse 路径。其文件哈希连同 source
adapter 依赖、normal 核心依赖、本模块、local 文件检查实现一起纳入 task source identity。
执行前后核对调用方独立保留的 identity；没有公开可注入的 builder/observer callable。
磁盘实现绑定采用既有合作进程假设，不认证 Python 内存中的 monkeypatch 或恶意 ABA 替换。

保留旧 JSON 的原始 pretty-printed bytes，以独立文件 SHA256 绑定；不转换、覆盖或重封旧产物。
JSON 解析拒绝重复键、NaN、Infinity。根字段 inventory 固定为当前 build artifact 的 24 项，
核对 verify/build-only/mechanism role、零 solver calls、一次 model build、未验证 assignment、
未形成正式结果，以及所有对应外部 pins。模型规模只比较保存声明和外部 expected scale，
本函数不重新构模；实际模型规模仍必须由 `normal_execution` 的 canonical 构模检查。

## 来源与机制边界

保存的 binding 先独立核正文摘要。声明中的 request/initial/carry 经原 decoder 转成 typed 输入，
再固定调用 `assemble_source_normal` 从当前 RTS 源文件重新组装，核 assembly 与完整 normal input identity。
随后固定调用 `bind_pair_normal` 重建 pair、power、workload baseline 对应关系，核其摘要及完整 JSON
与保存 binding 一致；最后重新读取三份声明并核实现身份。

初态始终为 `mechanism_assumption`；保存的 `initial` 是机制输入，不能改称源数据观测的机组前史。
不恢复 saved assignment、solver result、terminal carry 或 executable cursor。`PreparedNormalTaskInputs`
是由固定准备函数内部生成的 owned 结果，公开构造与 dataclass.replace 均拒绝；包含
assembly、pair declaration、binding JSON 和准备计时。solver_calls 为 0，
observed_power_mapping、normal_assignment_verified、formal_result 为 false。不得由调用方构造
此对象再让后继入口绕过固定准备函数。Owned construction 不认证内存真实性，也不使嵌套的
输入数据成为执行授权；后继 execution/replay 仍须保持原外部 identity 与来源重建检查。

## 真实 H25 开发证据（2026-09-20）

输入沿用现有 `normal_dynamic_verified_non_authoritative.json`，SHA256
`8c9b58ff3de2f37fecddcc283a1950e91c917a0dd0fc3d4c9025c29af317707d`。
pair YAML SHA256 `e4d78a3c4e060f493a8d238e4122a649c7a610cde8c0b2cc882fa091831e5019`；
audit YAML SHA256 `0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5`。
外部规模声明保持 22,275 variables / 28,004 constraints，未在本次重新构模或求解。

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -s -p no:cacheprovider tests/test_rq2_normal_task_inputs_v1.py::test_real_pinned_h25_preparation_without_solver
```

最终版本 **1 passed in 52.13s**，exit 0；测试将 solver factory 替换为禁止调用函数，重建出的 assembly/binding
保持原外部 pins。函数内部一次观测：

| 阶段 | 秒 |
|---|---:|
| 声明读取/解析/身份检查 | 0.032143 |
| 源数据组装及输入身份核对 | 24.723636 |
| pair/normal 来源绑定 | 25.596366 |
| 声明与实现后检 | 0.029367 |
| 合计 | 50.381511 |

这是一次来源准备测量，不是求解器选择 pilot、稳定性能统计或真实 normal 赋值。
没有据此选择或扩大旧 60 秒 worker、30/60 秒 numerical kernel 上限。
后继 task budget 必须另行覆盖 preparation、source execution 前后校验、归档及 replay。

## 最终回归与预审记录

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_task_inputs_v1.py tests/test_rq2_source_normal_execution_v1.py tests/test_rq2_normal_resources_v1.py -k 'not real_pinned_h25'
```

**99 passed, 2 deselected in 21.55s**，exit 0。两项排除是新旧 H25 来源测试；新入口的最终真实
H25 已用上一节命令单独验证，旧来源测试没有重复。

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_task_inputs_v1.py -k 'not real_pinned_h25'
```

独立短测 **33 passed, 1 deselected in 4.17s**，exit 0。构造限制与实际依赖字节绑定两项
pre-seal findings 已闭合，限定 adapter 范围无开放实质 finding。此结论不是整任务监督通过、
official verdict、seal 或 formal-run authority。源码、测试最终 SHA256：

| 文件 | SHA256 |
|---|---|
| normal_task_inputs.py | `5397ca0510d98f15e9e126debc1da5371df4ac9ebcc8259831a179a8f2cb882c` |
| test_rq2_normal_task_inputs_v1.py | `57b019f552ff654a05fa5f1e523e811d498f672952e48fe30775b42d5839fb46` |

更早版本的首次 H25 内部准备 52.453412 秒/pytest 54.21 秒仅为开发历史观测；不混入上述最终版本验证。
