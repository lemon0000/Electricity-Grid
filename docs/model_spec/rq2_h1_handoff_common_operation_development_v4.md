# H1 成功 Handoff 的 common 操作内复用草案

2026-10-18 当前后继（优先于下文历史状态）：成功Handoff使用Parent source-window v2，
25窗口/2408 logical source requests/50 original prepares；不再把2408写作当前physical prepares。
新增 `h1_selector_post_negative_validation_development_v1.py` 已接到三轮missing-Actual后的复验：
每轮Rref7+三Actual各1个retained主体保留，160 original prepares→2，三轮480→6。
它独立获取/释放四Parent guards和三引用标记，registry原子占有，全部清理后仅返回plain JSON。
公开guard调度、内部source I/O和失败顺序改变；首尾freshness与完整typed field/type检查保留，
不宣称top-level之间/窗口内ABA或完整动态closure覆盖，不跨Job/回调，也不跨窗口复用source。
136项回归通过；当前完整v4仅collection。独立完成输入的真实source单窗44.465935s，
2prepare/160borrowed/10retained，outer58.781s/exit0；完整typed projection SHA与保存oracle一致，
134输入/10锁/907源码/135保存pins/旧36pins及PID清理补检通过。Parent transport仍显式fake。
四Parent构造/run/oracle尚有712次条件prepare；genuine Parent/Handoff、paired/reopen、
configured entry闭包和完整预算未完成。DRAFT、M2及全部正式门状态不变。
具体代码绑定、终态和失败历史见hour0根`validation_n0_operation_01/performance_report.md`当前首节。

2026-10-18 最新证据：当前 Parent/common 回归为93 passed。保存 source 的完整字段 differential
已在 oracle03 通过，但其 host/activation 是显式 fake；严格导入范围由 profile03 及 fresh-owned03
后继核验。fresh-owned03 完成一个合成 N0 的真实登记/关闭及原 source，outer352.297s，
N0 complete295.572059s、原source17.801640s；它没有 common/Parent/Rref/Actual。
reader04 同输入单对为22.423639→23.217933s，未达到5%采用限，停止v3分支并保留v2入口。
131项 reader/monitor 检查通过不改变该采用决定。完整证据及失败 attempt 见 hour0 根
`validation_n0_operation_01/performance_report.md`；genuine Parent/Handoff、paired/reopen 和全链预算仍缺。

状态：`DRAFT_NONAUTHORITATIVE`。这是校验执行路径的版本后继；模型、输入映射、科学输出、阈值、
power/service balance、F/X、非预见性、共享灵活性预算、恢复债务和右删失保持原合同。
M2、整体性能/资源准入、封存、official review 和正式运行门禁保持 OPEN。

## 要消除的重复工作

成功三 Actual Handoff 的 22 个 common 观察位置保留。原每次 common 有两轮、每轮三个 arm，
合计 528 次完整 numerical hour replay。本草案第一次完整 common 返回后才激活三个独立 arm 的证明；
其后 21 次 common 仍执行原 source/registry/context/return bookends，复用已验证的数值结果。

| 范围 | full numerical | within-prefix | cross-common | 原 context | source prepare | registry prepare |
|---|---:|---:|---:|---:|---:|---:|
| 第一完整 common | 24 | 24 | 0 | 96 | 6 | 12 |
| 后续 21 次 | 0 | 0 | 1008 | 2016 | 126 | 252 |
| 合计 | 24 | 24 | 1008 | 2112 | 132 | 264 |

这些是执行路径及单元状态机的计数，不能换算为墙钟提速或完整链通过。

## 实现边界

- `h1_common_validation_operation_development_v2.py` 没有 Handoff 顶层 import。
  只有 Handoff anchor 能绑定私有 `verify/operation/validation_finalized`；bridge 借用原 token、
  bundle、guards 和 marks，不执行 BEGIN/END，不获取或释放外层资源。
  固定 sibling 路由逐边界核对 module/package/origin/spec/loader、源码 SHA 和函数定义。
- `h1_operation_historical_witness_development_v3.py` 沿用已有分 arm/prefix proof 机制，严格限制
  ordinal 1–22。第一完整 common 未返回、任何失败、跨 arm/会话、额外或缺失调用都不能形成成功证明。
  关闭时固定 clock/copy/schema 依赖；proof 清除、guard 释放和 live registry 移除不依赖报告构造成功。
- `h1_phase_exact_source_current_development_v4.py` 保留 predecessor `_prepare` core 及原两次 prefix、
  两次 registry、source/dispatch/return 观察。
- `h1_group_n0_common_input_binding_development_v4.py` 返回独立的 `predecessor_report_payload`、
  `validation_report_payload` 和真实 execution receipt。旧科学 bytes 继续用于消费对应；旧 `4/4`
  只作为明确标记的 compatibility projection，不描述当前实际执行次数。
- `h1_selector_phase_handoff_development_v4.py` 保留 v3 negative-only precheck，原位接入 22 个 common
  位置。packet/declaration 绑定 route、session、三个 authenticated N0 slots 及 Handoff source/implementation。

## 编码与证据绑定

三个 encoder 不能混用：旧 exact-source audit 用 `source.io.encode`，旧 historical audit 用
`bootstrap.historical.io.encode`，最终 group report 用原 group `encode`。后者带 LF；前两者不带。
当前纯逆投影 oracle 来自只读复制的 chain07 完整 common report，canonical 长度 115311 bytes，
SHA256 `a23f37589d049cdba62959cd4cb0546d50079174ae9e6973fa99e35eacf26798`。
chain06 同 schema 早期草稿没有 `verification_execution` 字段，不能当当前完整 report 的 byte oracle。

初始 declaration 保存在原 packet/header；最终 receipt 返回完整 operation execution preimage、
validation report preimage、predecessor report SHA、每次 common receipt SHA 和明确 encoder，
可以从保存内容重新计算关联，而不是只保存不透明摘要。

成功分成三个连续步骤：

1. 第 22 次 common 和两次 paired readback 完成后，关闭 private proofs，保存 pending receipt：
   `validation_checks_complete=True, outer_cleanup_complete=False, complete=False`。
2. 尝试释放全部 common/Parent/outer guards、marks、bundle 状态和原 token；任何失败保留首错并尝试后续清理。
3. 原 anchor 的 `validation_finalized` 核对实际资源释放后，唯一 commit 将 `complete=True`。

bridge 的终态只保留 weak owner reference 和 immutable JSON bytes，移除所有 live rows。
异常、部分构造和报告失败也清除 proof/registry；abort 自身失败不能跳过其他清理。

## 已有证据和未关闭出口

hour0 evidence 根 `validation_n0_operation_01/` 保存当前检查：

- `negative_handoff_matrix_unit_02`：6 passed；这是显式 fake Parent 的缺失/业务未决分类检查。
- `handoff_common_bridge_v2_unit_03`：53 passed；包含 route、tuple identity、pending/commit、
  外层清理及 abort 失败矩阵；使用明确的 fake session/finalized 或真实 finally AST。
- `common_v4_projection_unit_04`：10 passed，真实保存 report 的纯 inverse projection 与 mutation 拒绝。
  它不是当前 common 的真实数值 prepare。
- `common_handoff_v4_definition_unit_01`：五个 canonical 实际模块 cold definition 和固定 route SHA 通过，
  owner/lease/common/native 数量均为 0。
- `group_common_22_v3_unit_03`：13 passed；真实 grouped witness 状态机、显式 fake numerical/context/
  lease 与 prior-verifier identity，核对24full、2112context、1008cross，以及全局漂移/报告失败时的清理。
- `hour0_v4_collection_unit_01`：完整v4 target仅collection exit0，未执行整个target。

独立 PRE_SEAL 静态 findings B1–B5 已对应修复；不是 official verdict。当前仍缺真实 Handoff、
真实 bridge、22 次 common、成功 paired commit、完整清理与 reopen replay 的串联及耗时分解。
grouped witness 的计数单元、纯投影和 cold definition 不能代替这一出口。

## 下一个瓶颈：Parent 递归

静态成功路径有60次直接Parent validate，加上Actual在两个reference边界引出的90次递归，
共150次完整 `_retained → _inspect`，另有4次records自身rebuild/inspect。
单个非递归主体包含8次snapshot rebuild、16次source prepare、64full N0 audit，
合计9,600full N0 audit及约19,200次source-window load；这是静态条件展开，未测全链墙钟。
独立PRE_SEAL设计审查拒绝仅凭首次Parent成功、archive hash或operation lock缓存整个
`_source/_inspect`。registry/current-source、RTS namespace、全部transport/archive/lock、
process/env/clock和reference依赖的有序closure必须完整覆盖。Bootstrap的970个phase pins
不在该路径，不能用来补闭包。

优先边界是新的source reconstruction witness。原source/registry/current/join与Parent
观察仍须保留，historical prefix可复用的只能是经完整上下文确认的数值恢复。
需要新active receipt；旧4/4仅作compatibility projection。首轮prefix结束不能激活，
需独立confirmation与所属完整Parent site成功；不能复用已关闭 `_HourScope` 的私有结果。
依赖漂移或异常必须poison，无full fallback，解锁前销毁proof/bytes并关闭handles。
窄数值后继现已实现draft接线：`h1_selector_parent_validation_operation_development_v1.py`
及`h1_parent_source_n0_witness_development_v1.py`。每Parent首个完整validation中的16次source仍full，
尾检成功才激活独立proof；后续保留原观察，只复用numerical result，不缓存整个Parent。
13 bundle/150 Parent/4 records rebuild对应2408 source、256full、19008复用、38528原context。
89项分范围回归已通过（`parent_common_regression_unit_01`），含fake functional路由、真实finally AST、
替换callable零执行、proof清理、pending→aborted/committed与首错稳定；不是genuine Parent science验收。
source guard机械保留原`_guard_prepare`全部own/verifier/direct/code/default检查，调用捕获原函数；
Handoff从bind获取私有pair/declaration入口，不能先执行被替换的module slot。
parent proof先清理，外层资源全部释放后唯一commit；abort不可再commit，重复abort保留首错/receipt bytes。

真实保存source首轮oracle01仅完成旧source35.564281s与new firstfull34.017138s的decision/audit字节对照，
随后按540s投影规则停止，outer86.094s/exit1；未激活proof，也未比较全部source字段。
输入183/source/old36及所见PID退出已核验。它没有full-target test-only code identity cache，
故不能视作当前全链成本。后继必须匹配原fixture scope、覆盖完整source字段及真实Parent/Handoff出口。
本段不声称4full+146reuses、256full实际整链发生或M2通过。

保存检查01在17.672s因chain06旧实现身份不匹配退出，未进入数值重放。
03换为匹配当前身份的chain07已完成只读输入，120.391s触发wall cap，未完成inspection。
04为一次20秒可观测前缀，20.007879s后受控停止、outer33.016s，348个GIL样本和open前缀已保存。
165代码写方式重开无写、183非锁保存文件/source/old36及所见PID清理核验闭合。
样本与open记录不证明完整dependency closure或耗时占比；两次检查均非完整inspection通过。
更正记录见 `validation_n0_operation_01/parent_bottleneck_postcheck_01_non_authoritative/terminal.json`：
内部原verifier观察了worker lock字节（7次只读open），不能把外层“未触input locks”字段理解为未打开。
未获取writer lock；不声称access time不变。没有启动新Job/native或产生live Parent credential。
