# 保存输入的 append 成本观察

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL。按[自身合同](../../../../docs/plan/staged_deliverability_c_append_cost_probe_contract_v1.md)，各执行一次准备与测量，没有重试、恢复或新增数值输入。公共 RTS-24 主方向保持；本诊断输入来自三母线解析例的旧保存 journal，不是公共网络数值测量。

注册 SHA：`aebdd0be608c771b0571622d710b54641804a9173183252fc1424577137b9dd1`。准备 request 在 spawn 前绑定 runner、observer、test、合同和外部 wrapper 五个新源，以及冻结 guard/runtime、731 个历史文件、旧来源根、P1 注册及十三源、exe/env。原 B1–B3、codec/journal_v1/v2/v3、batch 五源与所有被用旧树均通过首尾核验。

## 终态与会计

准备和测量均 exit0。六成功与六失败案例均有独立 fresh，共十二个；实际 outer Job 的26个成员 HANDLE全部 signaled，TotalProcesses=26、active=0、final_pids空。逻辑角色数为13，物理成员数不能从它推定。外部 capture 的 owner、intent、日志及末端 timing 字节均独立绑定。

| 原始观察层 | selective calls | descriptions | P0 / raw / min / max |
|---|---:|---:|---|
| 准备 | 12 | 34 | 12 / 6 / 8 / 8 |
| parent worker | 94 | 260 | 94 / 30 / 68 / 68 |
| 十二 fresh | 92 | 254 | 92 / 30 / 66 / 66 |
| 测量合计 | 186 | 514 | 186 / 60 / 134 / 134 |
| 准备加测量 | 198 | 548 | 198 / 66 / 142 / 142 |

所有 observation 的 bindings_valid/complete 为 true，selective.started=selective.returned、selective.raised=0、forbidden_calls=0。预期故障注入另有prepare_hour.raised=4、publish.raised=2，均按失败合同保存。full compiler、构模、证据生成、native和solver调用为零。这里的 selective 是请求描述编译，不能解释为 solve 次数。

三方法 v2/v3 的完整 state、科学 digest、typed 根、逐对象 CAS bytes、summary、独立 audit 与准备 baseline 相同。成功案例只接受 h0/h1；原 observation_end=5 保持，finish 为 missing_input，有 terminal、state known，不把剩余观察期截短或认定完整服务。

unknown 的 writer 不采用已发布候选，fresh 确认一条 hour、incomplete_journal/committed、无 terminal；deletion 保存被移除 fixture 的原字节，writer 不采用，fresh 拒绝缺失可信闭包；reference_unresolved 保存零接受 row 的 committed attempt，ordinal1、无 terminal。两版本逐项失败语义相同，没有修复或回填被删对象。

## 绝对时间、内存与存储

| 计时范围 | 准备秒 | 测量秒 |
|---|---:|---:|
| 外部 PowerShell：Python 启动至返回、console capture完成 | 12.454271 | 156.945949 |
| controller preflight | 2.520025 | 2.606715 |
| owned monitor | 8.275576 | 130.970899 |
| quiet后处理/读回 | 1.379619 | 23.037932 |
| launcher入口至末记录前 | 12.175223 | 156.615548 |

guard 的测量 outer_seconds 为130.984，包含owner创建、worker/fresh、静默及终态扫描，未包含controller preflight和quiet后读回；不能称它为整个流程耗时。外部 Stopwatch 包含解释器启动及末端 controller 记录/console/退出，排除其后日志 flush/dispose、hash与外部 capture 自身出版。

worker 分组计费：pre 2.746693s、parent 70.605554s、fresh 54.884973s、post 1.838156s、report 0.012748s，均未超对应25/110/110/20/5s帽；组内包括按合同计入parent的阶段间工作。没有顺延任何预算。

以下仅列各case的命名parent阶段与fresh监控的绝对值，阶段间工作由上表parent组另计；顺序固定，每方法先v2再v3。

| 成功case | 命名parent阶段秒 | fresh秒 | case文件/bytes |
|---|---:|---:|---:|
| v2 instantaneous | 6.516500 | 3.945405 | 50 / 86426 |
| v3 instantaneous | 5.832002 | 4.060526 | 50 / 86532 |
| v2 fixed_headroom | 8.583204 | 5.087172 | 70 / 126618 |
| v3 fixed_headroom | 7.303171 | 5.314948 | 70 / 126729 |
| v2 full_temporal | 8.887801 | 5.218125 | 70 / 126671 |
| v3 full_temporal | 7.219420 | 5.341373 | 70 / 126770 |

测量 outer 采样tree peak RSS为298913792B，peak Job commit为235671552B；准备分别152330240B、118661120B。此采样不含外部controller进程，不是整机或全流程RAM峰值。测量core为571文件/1455342B；controller读回及晚写timing后的完整cost_probe_01为579文件/1660401B，未计外部观察、准备、注册、普通测试日志或Git体积。guard扫描的576文件/1556057B是更早终态位置，不能替换最后完整树大小。

parent observer 的inclusive read_bytes为58.193591s/23101成功调用/154997428逻辑bytes，inventory29.398000s/344次，runtime_v2为10.132496s/106次，runtime_v3为12.310679s/120次，selective0.042448s/94次。它们互相嵌套，不能求和或当作独立wall占比；logical bytes也不是OS物理IO。这些观测支持继续检查保留核验、目录和依赖身份计算的成本，但不许可省略原科学或保存核验。

## 后核验与后继

[verification.json](verification.json)保存第一次独立读回：全文件SHA、案例/科学/失败比较、198/548会计、旧绑定、外部timing字节均一致；普通后处理自身耗时22.210092s，独立于原诊断。随后的[verification_v2.json](verification_v2.json)增加精确core/controller map、逐case parent/fresh角色及完整时序断言，保留首次脚本与记录。原测量和所有绑定源未因后核验改写。

启动前46个不同普通检查及六轮日志见[开发记录](../development_checks_01/development_checks.json)。首轮14 passed/5 failed、后续修复及wrapper两项Medium的闭合均保存。只读sol_reviewer的结论属于PRE_SEAL findings，没有production候选、seal、official verdict或receipt。

单次固定顺序存在缓存/顺序偏差，本页不估计提速比、节省百分比或稳定优势。尚未知公共RTS-24数值点/g、真实dual/log/native失败、139节点完整F/X反事实时序、长cohort和前缀增长、真实坏盘/掉电/阻塞IO。现有实现仍有累计state/key编码和反复扫描的增长问题。下一步以这些保存观测补充整链审查，必要优化进入独立successor；不能据此给D/E点数或192h资源准入。

P1注册SHA仍为`23577e5d79d3284a260decbfe2258a3103252617953452565a9feeffafbd94e2`，十三源保持，p1_01不存在，专项授权仍待答复。用户已确认的公共网络方向不替代该权限。C整体性能与D/E资源门继续OPEN。
