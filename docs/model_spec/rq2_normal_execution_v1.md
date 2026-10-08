# 独立normal短执行内核

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。

`normal_execution.py`实现连续规模合同的normal-only数值内核。输入是完整`ContinuousNormalInputs`，
没有事故表、reference/actual origin或业务执行参数；不生成current输入或正式normal计划。
公开来源身份仍须由已有source/pair绑定层证明，数值内核不重复宣称公开数据验证。

## 入口与身份

`run_normal_only`要求外部`expected_input_identity`、`expected_execution_identity`及`expected_scale`。
`normal_execution_identity`用于事前派生并独立保留候选pin，绑定normal输入身份、实际规模声明、
本文件、旧原生求解核心全部源码依赖及运行时、solver specification和独立budget。
执行拥有完整输入私有副本；调用者修改原对象不改变已绑定模型。
准入实际构模后比较变量/约束数，每次fresh build前后及返回后再核身份。
声明有误或准入前资源超限时，native尚未调用，入口抛出拒绝。

新`NormalExecutionBudget`独立于旧`GridDevelopmentBudget`。它要求显式变量/约束规模上限，
保留单次最多30秒、最多4线程、H最多168的短开发范围，且固定最多一次原生调用、无重试。
执行主体复用原`continuous_grid_candidate._solve`，不修改数学约束、原生加载、gap或残差门。
新类型不是旧selector/episode的合法budget，不会解除它们的20/120次调用门。

## 接受、拒绝和中断

保存完整raw evidence和可得的`NormalAssignmentWitness`；normal_accepted要求单次调用、
`raw.optimal`、完整witness无错且有terminal carry，并通过本内核所有身份与资源检查。
仅有可行incumbent、超时、缺界、gap过大、赋值不合法或审计失败均为unresolved。
底层create失败且有完整raw返回时调用数为0；solve失败有raw返回时保留其调用数。
一旦进入solve pipeline却没有完整raw返回，调用数为null且`call_count_complete=false`。
其中KeyboardInterrupt/SystemExit等中断为interrupted，普通异常为unresolved；不以异常发生在构模附近猜零调用。
审计阶段失败但raw已返回时仍保留known调用数及raw，不能丢失已发生的求解。
返回后来源漂移也保留证据并拒绝接受，不返回可供自动推进的成功状态。

owned结果只能由入口构造；该约束不等于原生来源签名或对恶意Python对象篡改的认证。
`identity`绑定完整返回对象，包括raw/witness、调用记账、耗时、资源观测、错误和状态；
不同执行的耗时等字段变化会产生不同identity，它不是可重跑确定性保证或review receipt。
`normal_accepted`仅表示该开发内核的数值和检查通过，不是formal-ready、因果、安全或完整服务证书。

## 资源证据的准确范围

预算包含独立的observed wall time、process peak working set和core numerical evidence payload字节门。
这些是在边界和返回后检查的接受门，**不是强制终止上限**。
同步native调用不能被本内核杀死；返回`hard_resource_limits_enforced=false`。

| 字段 | 含义与边界 |
|---|---|
| preflight_seconds | 从入口到准入模型检查完成，含私有副本、hash、资源检查与准入构模 |
| solve_load_canonical_pipeline_seconds | 原`_solve`整体耗时，含fresh build、native create/solve/load及canonical审计；不伪称纯solver time |
| normal_witness_audit_seconds | 独立完整normal赋值/机组carry审计耗时 |
| builder_seconds_nested | 准入、求解、canonical builder各次构模计时；已包含在上述分段中，不可重复相加 |
| observed_total_seconds | 最后返回前观测的总耗时，含payload序列化和返回检查；不含调用者归档 |
| process_peak_working_set_bytes | Windows GetProcessMemoryInfo的入口/返回进程生命周期PeakWorkingSetSize；含更早任务，非本次独占峰值、非系统RAM、非commit bytes |
| core_evidence_payload_bytes | JSON `_encode((contract,input pin,execution pin,spec,budget,scale,raw,witness))`的UTF-8字节数；非完整result、归档目录或磁盘空间 |

资源测量缺失或失败不得通过；资源超限仍保留已返回raw，不能清理为成功或推断不可行。
`max_core_evidence_payload_bytes`只限制上表所列核心数值tuple；完整result及归档的字节门尚待监督层实现。
生命周期peak较高可保守拒绝新调用，使用该内核不能据此推断本次独占内存。
入口Windows专用；其他平台在native之前拒绝，尚未提供跨平台memory adapter。

当前没有持久化intent、排他进程所有权、disk admission或恢复游标，
`durable_invocation_tracking=false`；调用者中断后不能据此实现自动重试/恢复。
整任务监督器与持久化记录是后续必要工作，不能把本内核当作真实规模或正式运行入口。

## 验证与下一项

测试包含tiny HiGHS 1.15.1（每次1秒、1线程）、原生返回故障、gap/物理赋值反例、
外部pin/实际scale/horizon/solver准入、私有快照、后置资源失败、审计异常及unknown中断。
与未修改旧candidate在同一小例上比较完整raw evidence及witness；fresh进程核源码导入闭包。
本轮没有真实RTS求解、容量pilot或正式运行，也没有生产manifest/lease/receipt。
下一项是把本内核接到来源绑定输入和独立进程/持久化监督，完成资源与中断验收后再验证真实规模normal。

最终四文件相关回归216项通过（41.52s，exit 0）：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_execution_v1.py tests/test_rq2_continuous_grid_candidate_v1.py tests/test_rq2_continuous_grid_normal_v1.py tests/test_rq2_grid_information_v1.py
```

只读sol_reviewer独立复跑本层54项通过（18.54s，exit 0）。两项pre-seal findings已闭合：
增加完整结果identity；将字节字段/预算明确命名为core子集，并验证完整result大于该子集。
当前限定实现范围无开放实质finding；这不构成official verdict、seal或执行授权。
此前215项是这两项修正前的直接前驱，最终216项覆盖当前字节。

源码SHA256：`c11b4fc0fc465b67443758bf0469734a17e12f9378528be79d43f1124318f183`。
测试SHA256：`7696228814aa02da197076df2f7962951eb80fea4f3ea3879b6fed25f8046eff`。
旧candidate仍为`4f091095c621b6eb2bd403562e28f586447057767033ee1a3b1720780b2a752a`，
旧episode仍为`18b703ed033c8f1012a9725207dc2f27fb0d18e6c1c28f9558f3f0b62ba89725`。
本轮进程检查、旧源码hash、新文件空白检查及`git diff --check`通过；没有修改旧冻结结果或清理工作区。
