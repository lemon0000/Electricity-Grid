# P2收尾记录预算与guard v3开发核验

2026-10-24，DRAFT_NONAUTHORITATIVE。适用[开发合同](../../../docs/plan/staged_deliverability_c_p2_terminal_budget_contract_v1.md)。唯一writer为root，独立领域审阅及保存字节核对为只读。原P2七输入、guard v1/v2、parent observation v1、prepared packet、注册与已发布绑定不变；公共P2、native及长实验均未启动。

## 完成范围

新增[guard v3](../../../src/staged_rts24_process_guard_v3.py)沿用原OwnedChild的累计1024 identity/HANDLE上界（包含owner），为worker launcher和独立parent记录分别预留128KiB/一个文件，合计262144B/两个文件计入原64MiB/8192总帽。每轮及terminal均检查reserve，quiesce后、close前再次取得Job peak commit；返回前实际编码核launcher cap。RSS仍为离散采样，不代表收束期间的完整RSS峰值。

新增[parent observation v2](../../../src/staged_rts24_p2_outer_observation_v2.py)限制process字段域、两种完整/部分witness及错误文本；context显式绑定两个cap和文件槽。quiet未知不读或扫描worker。quiet已知时核launcher原字节、完整有界metadata会计、worker祖先identity和父目录；文件path/fstat/metadata及全树末次书挡覆盖stat后变化。callback和publication前后重验worker identity/launcher，发布后重新核worker和parent原字节/唯一库存，返回worker＋两份实际记录总量。范围/书挡失败保持会计unknown或publication unresolved，不报告包成功。

异常文本不可打印时保存固定标记；过长文本有truncated标记。原codec的create-only pending/fsync/no-overwrite rename/readback及失败阶段保留，所有科学采用、139独立核验、F/X、resource/formal字段仍false。没有生产launcher/registration/lease/CLI；测试中的launcher只位于pytest tmp。

## 验证与长度边界

最终同一组五来源pins下，`checks_01/units_06`为122项通过，`related_03`为91项旧guard v1/v2/parent v1回归通过，均exit0、无超时、首尾pins相同。测试包括小型真实Python Job→quiet→fixture launcher→parent实际最终会计；1024历史身份（同PID不同FILETIME分开计数）和原owner对1025 HANDLE拒绝；两个reserve字节/文件边界；错误文本二次抛错；post-quiesce commit；stat变化、同计数root替换、等长launcher漂移及发布后parent变化；七个发布阶段和不可覆盖pending/final。普通测试wall不作为P2预算。

独立[标准库长度oracle](checks_01/length_budget.py)不导入科研代码，以uint32 PID、uint64 FILETIME、1024 members/final PIDs、最大计数、有限binary64、最大非BMP错误文本及闭合claims构造最大形状，再按float≤32B/bool≤5B逐字段给出保守编码界。`length_03`保存执行命令、exit、script/输出SHA及当前来源pins：

| 对象 | 最大形状规范字节 | 保守编码上界 | 独立硬帽 |
|---|---:|---:|---:|
| 1024 member数组 | 61441 | 61441 | 属于各自记录 |
| process/launcher | 92020 | 92033 | 131072 |
| parent observation | 101064 | 101080 | 131072 |

这是当前封闭字段域的空间证明，不是实际P2记录测量。实际发布仍单独核字节上限。独立PRE_SEAL首轮3 High/3 Medium/1 Low及复轮1 Low均已修复并保留于审查记录；没有official verdict、receipt或seal。最早两次测试失败原样保留：实际Python Job有两成员但fixture误断言为1；旧测试的错误消息matcher未适配专用空父目录规则。`units_01/02`仍为exit1，不混入最终通过统计。

## 旧证据与剩余工作

[保存核验](checks_01/saved_checks.py)重新复现上一检查点stdout原字节，核547个旧发布文件及三导航完整旧尾部；旧P1的683个文件、B1–B3的118文件及685个早期路径的原核验结果复现不变。原P1 outer66/known inner64/两个residual不重新归因，条件642仅保留原条件结构含义。

`prior_01`在追加导航前直接复现旧检查；追加后原检查的整文件文档pins按预期拒绝，`prior_after_01`的exit1保留。随后`prior_projection_01`仅对三导航采用经原SHA验证的历史header/尾部视图，其余输入全部读取当前原字节，旧stdout再次逐字节相等；没有修改旧脚本或临时回写工作区。当前导航用独立尾部/链接核验。最初文档脚本的PowerShell Unicode编码失败也已留档并用UTF-8 patch纠正。

该候选空间合同已完成有界开发检查，原P2仍绑定guard v2；不能在原七输入闭合注册中替换v3或加键。实际outer必须另用新来源闭包，绑定真实启动事实及两份记录，接后继机械检查和受控独立raw→snapshot/KKT/point/合法X与journal重放。

完整outer尚未实现。父端遍历、fsync、回调/采用和失败收尾时间未准入；fresh60s＋最多5s收束相对65s无进展帽仍无父端余量。还需昂贵失败、十小时CAS/摘要增长、完整wall/RAM/storage及代表成本。RTS-24公共主比较与两母线机制方向保持，C整体、139/F-X、D/E现实输入/方案/选择/敏感性/冻结后留出和总预算继续OPEN。新native仍须具体包与专项授权。
