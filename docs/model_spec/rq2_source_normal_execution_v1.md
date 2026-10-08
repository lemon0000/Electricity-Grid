# 公开来源绑定的normal执行连接层

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。

`source_normal_execution.py`将已有`pair_normal_binding`与`normal_execution`连接，
保持两者代码和语义不变。它接收完整`SourceNormalAssembly`及显式`PairDeclaration`，
以输入私有副本执行同一normal内核，随后再次从源重建配对/normal绑定。

## 外部身份与来源核查

调用者须分别持有assembly、pair、binding、normal input、normal execution和source execution身份。
binding重建仍验证固定RTS文件、公开边缘包、窗口/训练分割、小时映射和精确动态baseline；
额外比较绑定报告的normal identity与本次私有输入，避免把不同normal输入的成功绑定拼接到求解。
连接层直接核assembly自身身份及报告的assembly/pair/normal身份，并重算报告内容摘要，
不只相信返回dict的binding_identity字段或下层已接受传入pin。
`source_execution_identity`绑定外部assembly/pair/binding/kernel pins、配对声明以及来源适配导入闭包源码；
kernel pin另行绑定数值模型、运行时、solver specification、budget及scale。
路径只定位源文件，不替代内容身份；所有来源仍须经原适配器验证。

执行前来源失败直接拒绝，不调用normal内核。执行后再次重建并核外部pins和前后报告完全相等，
对普通来源/源码漂移拒绝接受。没有源文件写锁，不声称能识别恶意ABA或提供来源真实性签名。
来源核对耗时和报告序列化属于wrapper，不包括在内核的资源预算中；单独报告`observed_wrapper_seconds`。

## 返回与接受语义

结果包含不可变的前后绑定报告JSON、完整owned内核结果和全对象identity，来源诊断不由调用者持有的可变dict保存。
`source_correspondence_verified`只表示前后来源对应成功，即使数值求解失败也可以为true。
`source_bound_normal_accepted`同时要求前后来源一致、内核返回与本次输入/执行/spec/budget/scale对应、
内核normal_accepted及无wrapper错误。底层normal接受门继续要求数值最优与完整无错witness。
内核成功字段须与status/errors、完整单调用、raw最优/赋值有效、witness输入/assignment identity、
terminal carry及非认证flags一致；typed对象的成功标志不能单独提升为外层成功。

kernel数值成功而post-source失败时，保留原raw/witness与known调用数，wrapper保持unresolved。
没有完整owned内核返回时调用数为null、call_count_complete=false；不根据异常文字推定零调用。
KeyboardInterrupt/SystemExit等中断单独标识；没有自动重试、恢复或后续current/episode执行。
绑定报告原有normal_assignment_verified=false等字段描述来源检查本身，不改写为数值求解状态；
数值状态位于normal_result及wrapper的联合接受字段。

完整结果identity覆盖来源报告、kernel结果、调用记账、错误、状态及wrapper耗时。
它是开发记录内容身份，不是canonical result、生产manifest、审查receipt或不可伪造签名。

## 尚未完成的执行义务

连接层保持hard_resource_limits_enforced=false和durable_invocation_tracking=false，
不提供进程超时强制终止、完整结果/磁盘预算、跨进程排他或持久化intent。
源码/输入检查不能替代这些运行义务，也不注册coupling、功率标定或业务参数。
registered_coupling、observed_power_mapping、formal_result及security_certified均保持false。
真实规模normal赋值、current连接和完整158 UID选择链仍需后续验证。

## 验证范围

小型原生正例使用合成网络及替代的来源边界，只证明连接层与内核组合行为；不称公开网络求解。
故障例覆盖外部pin、未解决来源、post-source变化/异常/中断、内核超时/缺返回/错误身份、调用者变更及源码漂移。
fresh进程验证全部src导入闭包分别被来源与kernel身份覆盖。

另以外部文件hash绑定既有H25动态normal记录及配对YAML，重建真实RTS assembly、完整配对绑定，
核动态baseline与normal identity，在kernel入口主动停止并禁止native solver调用。
该例检验真实来源连接到数值入口的对应关系，不检验真实normal可行性或资源容量。
wrapper保守记录缺返回为unknown；测试中的禁止solver钩子独立确认该测试没有原生调用。

最终独立验证覆盖32项，按同一最终源码分两组运行：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_source_normal_execution_v1.py -k "not real_pinned_h25"
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_source_normal_execution_v1.py -k "real_pinned_h25"
```

分别为31 passed/1 deselected（17.65s）和1 passed/31 deselected（103.14s），均exit 0。
后者的耗时包括真实来源/assembly重建，不能写成solver耗时或单独wrapper耗时。
主线程相关五文件124项回归通过（24.17s，exit 0）：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_execution_v1.py tests/test_rq2_pair_normal_binding_v1.py tests/test_rq2_power_normal_binding_v1.py tests/test_rq2_source_pair_v1.py tests/test_rq2_source_normal_v1.py
```

独立pre-seal检查中补齐assembly/pair直接pin、绑定正文重哈希及内核伪成功一致性检查，
相关反例覆盖后限定范围无开放实质finding。该结论不是official verdict、seal或运行授权。
源码SHA256：`56a59908c99b5da24047bdd4c93478da6576b9224ca91e2994bc60cad79d57cf`。
测试SHA256：`35a8a777826e617aaa45f2138efd5a2d707e1922060e64a76acb5ae51c7a5759`。
原normal kernel仍为`c11b4fc0fc465b67443758bf0469734a17e12f9378528be79d43f1124318f183`，
pair binding仍为`bfda25bee227772902ce8eeb29dcf657d3949989d6fe94e239b63f242dec7c10`。
本轮diff与新文件空白检查通过，旧公开源/构模产物、冻结结果及其他未提交文件保持。

## 下一项的既有组件核查

独立进程监督已有可供审查复用的仓库实现：
`experiments/run_rq2_public_grid_two_block_pilot_activation_transport_v5.py`提供
`monitor_owned_child_resources`，按PID和创建时间检查所属子进程，观测private commit与系统commit余量，
并处理watchdog、资源超限和采样失败；`episode_store.py`已有本地合作进程排他及SQLite intent/result链。
后续先核查这些原语和测试的适用性，避免重新开发已有功能。
transport_v5的8GiB/2GiB/5秒设置属于旧冻结协议，不能自动成为连续normal的新资源声明；
旧完整controller、receipt与执行授权也不能直接移植。按采样停止不等于内核级瞬时内存硬限。
episode_store绑定四臂小时事务，不能把它已有的恢复能力直接宣称为normal-only持久化已经完成。
