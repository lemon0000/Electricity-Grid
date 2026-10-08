# Normal 组件成本诊断

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE，零solver开发探针。

真实H25流式任务的normal内核耗时67.5576574秒，超过既定60秒门；同时单次1秒原生求解
没有返回解。已有计时不能细分身份编码、模型构建和原生前置操作的成本。
本探针只定位可独立测量的组件，不修改已绑定源码、模型、阈值或已有结果。

## 受限路径

`experiments/diagnose_rq2_normal_cost_v1.py` 保留既有stream prepare探针的父子握手、
本地排他目录、固定environment、PID/FILETIME/process pin、Job静默和失败留存检查。
使用同一旧H25开发声明，117秒子进程预算加3秒静默，process/Job各768 MiB。
默认只检查声明及host余量，`--execute-development`才创建一个新目录并运行。

子进程完整准备来源后，顺序测量八项：独立deepcopy、完整输入身份、执行身份、
单次normal model build、model_scale、native结构指纹、初始变量snapshot、末端完整输入身份。
构建前后输入身份必须相同，实际模型规模必须匹配独立请求；保存structure/snapshot摘要。
model_build内部的验证成本包含在该项内，不拆出后重复相加。

不调用normal/source执行入口，禁止create_solver，solver_calls=0、model_builds=1。
normal_execution_identity只是被测实现/规格的标签，不是一次正常执行的授权或认证。
`numerical_execution_performed`、`normal_assignment_verified`、
`component_costs_are_kernel_total`、`whole_task_resources_verified`和`formal_result`均false。
机制初态与业务功率映射的事实边界保持不变。

## 报告与解释

父进程验证costs.json完整字段、来源和实现pin、H25/8784小时元数据、规模、零求解角色，
以及八项固定顺序的有限非负float计时。顺序组件之和加完整prepare时间不得超过报告elapsed
（仅1e-6秒加减舍入容差）。structure/snapshot摘要是子进程观测，父进程只校验格式；
没有重建年度模型来独立证明该摘要的数值语义。

这是一轮组件微测量。调度、缓存、数据副本和对象存活范围与原kernel不同，不能将各项
乘以猜测次数后当成原67.56秒的精确归因，也不能从该探针推导有效assignment或60秒验收通过。
初步目的在于确定优化应优先检查哪段代码；进一步优化须保留相同编码内容和所有复核门。

异常保留有界failure.json和已有started/launch/request；没有costs.json时不报告完整组件成功。
进程非零退出、超时、无静默、身份漂移、resource/API errors或报告错误都保留unresolved。
不自动重试，不把诊断失败解释为数学不可行。

## 验证记录

首轮迁移测试69 passed in21.29s。补充tiny实际一次model build、solver禁用、输入副本突变、
规模漂移、MemoryError留存和组件计时/角色字段反例；最终相关回归和独立审查结果另行追加。
测试不读取真实年度来源或调用solver。

2026-09-27续接核验：最终相关回归已完成191 passed in49.16s，命令为
`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_diagnose_rq2_normal_cost_v1.py tests/test_diagnose_rq2_stream_prepare_v1.py tests/test_rq2_normal_task_process_v1.py`。
本次复核源码SHA为`ecd618f9108ac8257be6bf34ebb4784536bd50a50387223d834faee8f2d35af7`，
测试SHA为`b8e7b9ca04717e4fbaa3a0edbcd58013fcd33418d507d010ecfe1136e9cb4f48`，
与上述最终测试版本一致；六批历史索引的22+13+11+13+15+54项bytes/SHA全部一致。
独立pre-seal审查和真实组件测量尚待完成，此记录不改变任何正式门。

独立首轮88 passed in47.52s后发现：子进程写完报告至父进程汇总期间，尚缺实现身份复核。
新增读前/验证期间漂移两项反例，先在旧实现复现2 failed,88 deselected in2.80s；
随后在父进程读取costs前和验证后各复核实现pin，发生漂移保持unresolved。
最终上述三文件相关回归193 passed in68.88s，独立受影响2 passed,23 deselected in2.23s，
该finding已闭合，限定pre-seal范围无开放实质finding；未生成official verdict或receipt。

最终probe源码SHA：`afe68b849e2fdd52f7fac2a8f9dfabd497583035cc2ca0ee947e1fc2e99faf8f`；
测试SHA：`8128551a157c9b160f1d010c8ef4b884e1be55805bf8e3f7e6a174db2d448238`；
实现pin：`b33ee530c9ad20e838e6deb148001642dc8c716f1cfbf2a99583d1b3f65650c1`。
后续工件索引必须核对启动pin与当前实现、源码，避免把漂移后的文件收为本次证据。

## 2026-09-27 真实H25组件测量

新目录`results/tables/rq2_normal_cost_probe1_non_authoritative`已终态，
`status=normal_component_costs_observed`、errors为空。仍使用完整8784小时来源、
H25/22275变量/28004约束；normal、assembly、binding内容身份均复现。
一次model build，solver_calls=0；model structure身份与先前H25记录相同。

| 顺序组件 | 耗时（秒） |
|---|---:|
| deepcopy | 2.103563 |
| input identity | 10.223881 |
| execution identity | 0.044423 |
| model build（包含其内部校验） | 10.610566 |
| model scale | 0.016264 |
| model structure | 2.589644 |
| initial snapshot | 0.161498 |
| post input identity | 9.739884 |

完整prepare为47.835529秒，child报告elapsed为83.902627秒；两者及组件遵守顺序计时检查。
Job观察耗时86.125秒，PID14388/FILETIME134349827305064543，exit0、静默true，383次采样。
process/Job commit峰为474791936/476012544 bytes，低于原805306368上限；
child lifetime working set峰496336896 bytes，无resource/API errors。
caller工具观测exit0、elapsed88.3887992秒；该caller退出码未另存独立进程证据，
其强度低于已保存的Job observation。

两次完整input identity各约10秒，表明身份计算本身值得优先优化；尚未区分输入验证、
递归编码和SHA更新各自的比例。model build含其自身input identity，不可把10.61秒
都归为数学模型构建。不同日期的prepare耗时已有差异，不能直接把本次组件乘以调用次数
视为旧67.56秒的精确归因，也没有证明优化后60秒门可过。下一必要工作是保持逐字节编码
和所有检查位置的身份编码后继，通过等价性/突变反例及受限测量，再决定数值链接入。

初态与业务功率映射继续标为机制假设。无normal assignment、数值执行、恢复认证或正式结果；
完整UID/四臂资源、右删失、风险分母、科学注册和正式启动门继续开放。

启动及终态/索引前复算实现pin一致。29项bytes/SHA索引：
`results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/normal_cost_probe1_evidence.json`，
SHA256：`7f0d5fa4fb3fce23588bbb117bfa319ca3abdb1f987e609ff6a240ac924a9e50`。
日志：`results/logs/rq2_normal_cost_probe1_non_authoritative.log`。
costs SHA：`47046a4d59f94062b3558c1d618fce7c55bb6b2f0091bc869e545d5ace533e61`；
observation SHA：`512a943b76d3b788e6bbf9b789592c925798984b95d784b7136a1bb9d3412133`。

本次调用参数（wrapper以排他`xb`日志、CREATE_NO_WINDOW运行；以下目录已存在，不能重跑覆盖）：

```text
D:/Miniconda3/envs/compute/python.exe -B experiments/diagnose_rq2_normal_cost_v1.py
  --declaration configs/rq2_normal_task_h25_development_v1.DRAFT.yaml
  --expected-sha256 9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6
  --expected-implementation b33ee530c9ad20e838e6deb148001642dc8c716f1cfbf2a99583d1b3f65650c1
  --diagnostic-root results/tables/rq2_normal_cost_probe1_non_authoritative
  --execute-development
```

独立结果只读核验完成：29/29项bytes/SHA一致，root为7个预期文件且无failure sidecar；
request/launch/started/observation/costs的PID、FILETIME和process pin交叉一致，
按声明environment顺序复算process pin一致；当前实现及stream/prepare/model/execution pins一致。
summary与原始costs/observation及其摘要一致。八组件合计35.4897217秒，
加prepare共83.3252510秒，不超过child elapsed83.9026270秒。
未重跑年度prepare或solver；无实质finding。该核验不改变上述证据边界与正式门。
