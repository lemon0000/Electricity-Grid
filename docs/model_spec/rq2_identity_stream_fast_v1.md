# 身份编码性能后继与真实对照

日期：2026-09-27。状态：DRAFT_NONAUTHORITATIVE。

既有真实组件测量显示完整input identity两次约10秒。此后继只优化编码的实现成本，
保持`json.dumps(legacy._encode(value), ensure_ascii=True, allow_nan=False)`的逐字节内容。
原`identity_stream.py`和所有历史工件绑定的模型、执行入口均保留。

## 实现与验收

`identity_stream_fast.py`对exact primitive直接输出原JSON token：float仍校验有限性并使用hex，
str仍使用JSON ASCII转义；dataclass/sequence合并相邻结构token。mapping/set局部编码先分派
primitive，仍以完整encoded pair/value的repr稳定排序。保留dataclass优先级、subclass类型名
与不支持类型的拒绝规则。没有缓存输入、字段布局、依赖或摘要；每次normal identity仍完整
调用原_validate并重算_dependencies。局部mapping/set仍可能较大，不声称通用硬内存界。

当前未接入normal/source/worker执行链。后续consumer须独立绑定新源码，不能用旧执行pin
授权后继；相同内容摘要本身不证明相同执行实现。

新测试包含legacy独立编码oracle、嵌套随机输入、encoded-key碰撞、负零/极端float与500组
float位模式、Unicode代理项和控制字符、subclass/dataclass优先级、内容及字段布局突变、
每次验证与依赖变化。相关新旧identity与原cost probe共157 passed in44.57s；
独立新identity全组41 passed in2.23s，限定pre-seal范围无开放实质finding。
tracemalloc测试仅为合成结构的分配对照，不能外推真实年度峰值或内核60秒门。

identity源码SHA：`2e75712e9d8603ba7e9aadb0dbd20081a9813b83b09caab87c2ff59994828133`；
identity测试SHA：`608df793900062e92177762347583acbb9543984e8e7264b9b0b111d83daf567`。

## 受限真实对照探针

`experiments/diagnose_rq2_normal_cost_fast_v1.py`从原cost probe建立独立后继，schema为
`rq2_normal_identity_comparison_probe_v1`。保留完整prepare、原8项计时及单次旧模型build，
增加两次fast input identity：第一组old→fast，末端fast→old；四个完整摘要均须匹配
声明的原input identity。额外保存新源码SHA；该源码同时进入启动/子进程/汇总前后的实现pin。
父进程逐项验证新元数据、十项计时和elapsed关系。

沿用117秒加3秒静默、process/Job768 MiB，不改原声明、模型数值、solver预算或60秒接受门。
solver_calls=0，禁止normal执行入口与create_solver。`normal_execution_identity`仍指被测
旧kernel的标签；单次旧build不表示fast encoder已接入kernel。所有数值、assignment、
kernel-total、整任务资源及formal authority字段保持false。

一次对照不是稳定性能估计，顺序安排只减少单一顺序偏差，不能消除调度/缓存影响；
不将组件速度比直接外推全kernel，更不从零求解探针推导有效解。超时、摘要不符、
身份漂移或资源错误保持unresolved并保留工件，不自动重试。真实对照及最终探针审查待追加。

探针相关验证命令：
`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_diagnose_rq2_normal_cost_fast_v1.py tests/test_rq2_identity_stream_fast_v1.py tests/test_rq2_normal_task_process_v1.py`，
170 passed in52.96s，进程exit0。包括新旧摘要不符、元数据篡改、构建后突变、
汇总前后实现漂移、solver禁用、失败留存与挂起子进程握手的反例。
探针源码SHA：`20ee35979d365ed63f3f98a9303a856af288e1d4b86686f7f162f5cb5598aee8`；
测试SHA：`a5cdf66a81734b7a3f0a4d27e6fe2502d55289134636cd06cbcd3bddaa0626ba`；
实现pin：`94cd1eed566e92bf0d2f6e82d94002d1e33ad6c422637f4f7eddb033d4a61c96`。

独立probe差分审查：新旧摘要不符、fast元数据及tiny build共14 passed,81 deselected
in10.61s；上述源码/测试字节一致，限定pre-seal范围无开放实质finding。
未生成official verdict/receipt，未打开正式门。

## 真实对照结果

新目录`results/tables/rq2_normal_identity_comparison_probe1_non_authoritative`已终态，
status为normal_identity_comparison_observed，errors为空。使用完整8784小时来源、H25输入；
四次old/fast身份均为`d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c`。
单次旧模型build的structure与先前记录一致，solver_calls=0。

| 组件 | 耗时（秒） |
|---|---:|
| deepcopy | 2.104261 |
| old identity（第一组先测） | 9.834936 |
| fast identity（第一组后测） | 6.865299 |
| execution identity | 0.042330 |
| 旧model build（含旧身份校验） | 10.498907 |
| model scale | 0.017097 |
| model structure | 2.557657 |
| initial snapshot | 0.146311 |
| fast identity（末端先测） | 6.754984 |
| old identity（末端后测） | 9.786799 |

本次两组fast相对old耗时分别减少30.19%与30.98%，仅为这一次开发测量。
prepare47.3985673秒，child elapsed96.5513175秒，Job observed98.625秒，
低于117秒预算；PID32752/FILETIME134349835235906054，exit0、whole-job quiet，437次采样。
process/Job commit峰474095616/475328512 bytes，child working-set峰496193536 bytes，
无resource/API错误。caller工具观测exit0、100.8496508秒，未另存caller进程证明。

normal模型和kernel尚未使用fast，不能声称整段60秒通过或已取得assignment；
这次组件改善足以支持下一步接入独立normal model/kernel后继，保持全部输入/执行身份检查
位置、原数值门、资源上限与接受语义，然后按后继链验证。初态和业务功率映射仍为机制参数；
右删失、风险分母、四臂全任务资源、科学注册和正式启动门继续开放。

31项bytes/SHA索引：
`results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/normal_identity_comparison_probe1_evidence.json`，
索引SHA：`08eee9f3134b3f82e6eb59a3c5fd920fb087e99178b3b16979a1f08d0166d316`。
日志：`results/logs/rq2_normal_identity_comparison_probe1_non_authoritative.log`。
costs SHA：`e8f19f646013315810e1d52c9178250b03fc50419b628882c812e4ad9e96fcf2`；
observation SHA：`b3da10992ef245b7a75caadad305bb4510186249c2c58e8521e015aafcd12226`。
启动、终态和索引前实现pin复算一致，probe与identity源码此后已由真实工件绑定。

本次调用参数（路径已存在，不得覆盖重跑）：

```text
D:/Miniconda3/envs/compute/python.exe -B experiments/diagnose_rq2_normal_cost_fast_v1.py
  --declaration configs/rq2_normal_task_h25_development_v1.DRAFT.yaml
  --expected-sha256 9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6
  --expected-implementation 94cd1eed566e92bf0d2f6e82d94002d1e33ad6c422637f4f7eddb033d4a61c96
  --diagnostic-root results/tables/rq2_normal_identity_comparison_probe1_non_authoritative
  --execute-development
```

独立结果只读核验：31/31项bytes/SHA一致，root为7个预期文件且无failure sidecar；
PID/FILETIME/process pin、源码与实现pin、summary及原文件摘要全部一致。
十组件合计48.6085806秒，加prepare为96.0071479秒，不超过报告elapsed。
旧/新probe的normal/input/assembly/binding/model/execution/structure/snapshot pins一致。
未重跑年度prepare或solver，无实质finding；本次测量及审查不打开正式门。
