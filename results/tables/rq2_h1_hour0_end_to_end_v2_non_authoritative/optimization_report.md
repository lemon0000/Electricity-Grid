# Hour-0 校验优化记录

2026-10-14。范围为完整合成链的提速和可靠启动；科学合同、数值验收限及旧封存依赖保持不变。

## 实测结果

最终代码在同一份 378-file 保存记录上进行三对交替、独立进程、无 profiler 的串行计时：

| 配对 | 旧路径（秒） | 新路径（秒） |
|---|---:|---:|
| 1 | 47.495 | 40.421 |
| 2 | 47.563 | 39.826 |
| 3 | 48.829 | 39.934 |
| 中位数 | 47.563 | 39.934 |

该环节中位耗时减少 **16.04%**。六次科学投影逐字节一致，SHA256 为
`b7136ce39e1b048f3a84018a0b3e1dfe66876eb8b885e9609b67f2f130c56868`。
每次保存文件和实现 pins 前后均一致，真实 native 调用为零。
证据：[最终配对计时](exact_source_timing_pairs_02/terminal.json)。
初稿曾出现带 profiler 的新路径慢于旧路径，原始记录和后续对照均保留；最终结论使用上述串行计时。

独立调用计数观测为：旧路径 8 次完整 hour replay；新路径 4 次完整 replay、
4 次 fresh byte/context revalidation。两个 prefix 的作用域独立，原 source/registry/join/
projection/final observation 边界保留。新 audit 只改变 schema/implementation identity，
并增加 verifier 和计数字段；旧科学投影和 normal/source/registry audit 内容保持一致。
见 [最终等价记录](optimization_pass_01/exact_source_equivalence_02.json)。
该 profile 与回归并行，仅用于调用次数和等价检查，其 wall time 不参与提速计算。

## 接线与验收

新增 exact-source v2、phase-owner v2 和 consumption-preview v2，显式接入 manifest/common/handoff v2。
预演器同步使用新 owner，修复 planned retention hash 与实际提交不一致的问题。
新 owner 的 source scope 明确为 N0；仍需要下一小时的情况下，在任何 attempt 写入前拒绝，
保持 192 小时科学 episode 声明，且不把未完成的 episode 标为结束。

修复后的 76 项 source/owner/routing/persistence/selector 回归全部通过，exit0，
34 个测试绑定文件的 before/after/current hashes 一致；耗时 3375.62 秒。
覆盖双 Actual 共享 Rref 的实际提交、故障窗口、重开及锁释放。
见 [回归终态](exact_source_routing_checks_02/terminal.json) 和 [测试输出](exact_source_routing_checks_02/stdout.log)。
首次回归失败、主动停止记录和定位到旧 preview 的反例均保留。
另有 [1082 项旧依赖保持性检查](optimization_pass_01/predecessor_preservation.json)，无漂移。

后台启动采用隐藏 WMI host，并核对独立父进程、命令、创建身份和代码 pins；
发起 shell 返回后的 12 秒短 probe 正常终止，见 [host_probe_04](host_probe_04/terminal.json)。
启动后身份未核实或父进程错误时，保留 `LAUNCHED_UNVERIFIED` 并禁止自动重试；
可复现 mock 证据位于 `synthetic_host_fault_03/` 和 `synthetic_host_fault_04/`。
短 probe 不代表整链清理、正式 lease 或资源准入已经通过。

其余热点及保留理由见 [优化清单](optimization_pass_01/opportunity_register.json)。
全局 package identity 缓存会删去 freshness 观察；保留等价观察需要更大的版本化 numerical stack，
当前没有识别出另一项小范围、低风险且明显提速的改动。

## 当前出口

独立只读 reviewer 已完成最终证据复核，未见新增 finding，记录见
[限定范围 PRE_SEAL 复核](optimization_pass_01/preseal_review_01.json)。
以上均为 development/PRE_SEAL 证据。完整三 arm → Rref/Actual → paired commit →
关闭重开重放仍须从新目录跑通，里程碑 2 尚未关闭。
16.04% 是单环节收益，不能直接折算成全链耗时或 native 预算。
192 小时覆盖、资源准入、封存及 official review 仍有各自出口；正式实验未启动。

2026-10-14 23:09（Asia/Shanghai），新 `chain_06` 已在独立 WMI 后台启动，
wrapper PID 38752、pytest PID 39032；独立监督 PID 36684。
启动身份见 [chain receipt](host_chain_06/launch_complete.json) 和
[supervisor receipt](host_chain_06_supervisor/launch_complete.json)。
监督等待完整链终态，成功后接续独立保存重放及全链报告；当前启动状态不表示链已通过。
本次从新目录执行，旧 chain_05 的中断工件保持原样。

2026-10-15 11:45:15 终态更新：chain_06 exit1，45371.25 秒。Rref 返回和缺 Actual
拒绝检查完成后，第一个 Actual parent 的测试目录 `actual_cfe_only_shared` 缺少
`_non_authoritative` 后缀，真实入口拒绝。监督正确停止，未启动 postcheck。
461 个保存文件清单见 `actual_path_repair_01/failure_preservation.json`，原目录保留。
修复只涉及测试 helper 的目录构造，并在 selector harness 之前验证全部 Actual roots；
真实 `_path` 拒绝规则不变。短反例 3.84 秒复现；`actual_path_checks_01/terminal.json`
记录 5 passed、exit0、34 pins 稳定。当前无完整链运行，未自动重启。

耗时诊断：common genesis 与 inspect 区间为 23734.58 秒（6 小时 36 分钟），
其 `_correspondence()` 多次调用 `common._prepare_locked()`，后者按两轮、三个 arm
重建科学证据；初始化、回执保留和 inspect 又分别触发该路径。此为静态可见的多层
有限重复工作；没有该区间逐函数 profile，不能把全部时间精确归因给某个函数。
该阶段已正常返回并进入 Rref，因此本次失败不是在此处无限循环。
先前 16.04% 的单环节收益未解决这些上层重复调用，不代表整链已经充分优化。

## 2026-10-15：common 单 arm 双投影合并

`h1_phase_exact_source_current_development_v2.prepare_common_bundle` 在一次有界调用内
从同一组已核验证据生成 historical 与 exact-source 两个投影，common `_arm` 显式使用此入口。
仍执行两个独立 prefix、source/registry 重读、完整 audit 对照和末次观察；没有跨 arm、
跨 common 调用的缓存。历史科学投影保持原样，新执行审计单独记录实际校验次数及实现身份。

`common_bundle_checks_06` 为 67 passed、exit0，测试耗时 243.58 秒；全部运行绑定代码
before/after/current hashes 相同。`common_arm_group_profile_01` 在 chain_06 的真实保存记录上
完成三 arm 两轮校验：六次科学投影及旧 audit 内容一致，同一 arm 的完整新 audit 两轮一致，
461 个保存文件和实现 pins 未变。观测为 24 次完整数值 hour replay、24 次 fresh revalidation、
12 次 prefix；此前相同六调用结构需要 48 次完整数值 replay 和 48 次 fresh revalidation。
profile 耗时 389.92 秒，因带 profiler 且与测试并行，不用于计算 wall-time 提速比例。

1082 个旧依赖 pins 再核对无漂移，记录在 `common_bundle_repair_01/preservation_check.json`。
新增三 Actual 后半链预检直接调用完整 integration helper，并检查成对提交和重开保存重放；
其 common/source/roster 与求解执行为显式合成 seam，三个 lane 配置由同一基础配置克隆，
不能替代完整三 arm N0/common 实验。该预检的最终状态以 `three_actual_preflight_04/terminal.json`
为准。路径错误、失败尝试与中断诊断均保留。里程碑 2 仍 OPEN，正式实验未开始。

独立只读审查未发现 bundle 的新增阻断项，限定范围记录为
`common_bundle_repair_01/preseal_review_01.json`；旧 audit 对照仅排除新增执行元数据
和 successor exact-current implementation identity，其余内容严格相等。
另修复 `postcheck_complete.py` 对 Actual 分段计时标签的严格期望顺序；
`common_bundle_repair_01/timing_label_regression.json` 使用预检实际产生的 Rref/三 Actual
18 项完整前缀，证明旧版拒绝、新版相等，缺项与乱序仍拒绝。该检查尚不构成完整 postcheck。

## 2026-10-15：提交后测试比较修复与保存记录续验

`three_actual_preflight_04` 最终 exit1，4748.98 秒：三 Actual、三项 missing-one、
paired consume、1 hour、5 retentions 和三 lane paired_committed 均已通过，随后
helper 直接比较 JSON list 与 dataclass tuple 而失败。只将 common view 断言改为
生产 handoff 已使用的 canonical encoding 比较；字段变化仍拒绝。

`packet_comparison_repair_01/attempt_03/continuation_result.json` 保存独立进程续验：
4.34 秒重新计算原始记录的 plan/tickets/projection/carry，核对 holder 与5项 journal、
原 DB/root/lock identity、4个 parent 保存哈希；重新获取释放9把文件锁，真实重开
holder/phase 并重放得到同一三 lane paired 状态。原保存文件全部 bytes 不变。
`packet_repair_checks_01` 为5 passed、exit0、32.10秒，代码 pins 稳定。
原04仍是失败记录；续验不重建原进程 adapter apply/close 调用次数，也不替代完整三 arm 链。
完整链将继续执行这些未运行到的内存断言。续验脚本初版的导入路径错误及 attempt_01 的
记录解包错误均发生在生产重放前；attempt_01 的失败记录和脚本字节保留。

独立只读审查结论见 `packet_comparison_repair_01/preseal_review.json`：未发现阻止已授权
合成 chain_07 的新问题。机械检查后启动 `chain_07`，wrapper PID43640、pytest PID27888，
监督 PID42184；两份 WMI detached 启动回执为 `host_chain_07/` 与
`host_chain_07_supervisor/`。完整出口仍待本次终态、postcheck、独立保存重放及耗时报告。
