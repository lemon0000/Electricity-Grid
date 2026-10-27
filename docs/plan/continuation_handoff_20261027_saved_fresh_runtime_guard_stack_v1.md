# C/F：三项guard修复闭合，导入超时已有实际栈

2026-10-27，DRAFT_NONAUTHORITATIVE，接续[runtime handoff WIP](continuation_handoff_20261027_saved_fresh_runtime_handoff_wip_v1.md)与[runtime guard范围](staged_deliverability_c_saved_fresh_runtime_guard_scope_v1.md)。root唯一writer，独立只读PRE_SEAL；无official verdict/receipt、production seal或运行授权。宽goal继续active，完整C/F尚未完成。

## 已闭合的开发行为

当前guard主实现为core v7、B_S v3、runtime_handoff parent/probe/tests各v3；namespace v2复用。新27/27 unit通过，0 failure/error/skip，capture exit0，charge14.727937/18s。原runtime_handoff17文件、旧timeout及20/20修复字节全部保留。本轮不再有三项指定PRE_SEAL must-fix：

1. Bootstrap native tuple固定完整builtins keyset/逐value身份，proof构造前后书挡；替换遗漏成员时不调用替换函数。
2. 原audit函数与proof由callback强持；B_S module/class函数、callback及finder的code/default/kwdefault setter按对象身份立即拒绝。四项真实setter反例验证变更未生效、FAULTED一次、busy中无敏感getter。
3. 删除_req槽，注入no-op直接AttributeError；入口用defaults强持的full/identity verifier与checker。Root失败由zero-global原生failure factory创建异常，tuple漂移跨两次close仍惰化hook并重抛同一缓存failure，primary/secondary保留。

七个新增反例使用exact-type stage0逻辑boundary、真实callback/installation sentinel，不stub_entry/_audit_entry/_ownership/_image。当前unit machinery不是factory B3/flags或native验收。两个旧close控制分支只在明确的logical context中验证，不冒充production guard。Unit峰值WS137478144B仅观察，非RAM硬准入。

## 实际冷路径与未完成项

guard的独立startup discovery/admission通过。但首次实际import_discovery在9.516213/10s超时，child被kill、stdout/stderr均0。父process HANDLE/stdin/reader/pipes终态，无cleanup/truncation；没有child self-close或runtime owner报告，不能补造。原链停止，import admission、normal与六故障窗口、整包saved均未执行，不能直接继续旧driver路由。

为定位耗时先建立[phase trace](staged_deliverability_c_saved_fresh_runtime_trace_scope_v1.md)，原/后继登记均被30000UTF16帽拦，无child；[command repair](staged_deliverability_c_saved_fresh_runtime_trace_command_repair_v1.md)也按约停止。六组无损zlib参数最短原command30093UTF16；两份登记失败及0.2622036s比对保留。曾怀疑marker分隔为字面反斜线，实际AST均为bytes[10]，该只读判断撤销，probe4原字节保留。

随后建立[单次stack观察](staged_deliverability_c_saved_fresh_runtime_stack_scope_v1.md)：原core9/probe6/parent6在import case启动watchdog，discovery没有启动，导致SELF阶段conditional TCB profile mismatch。source_open=0、self资源未构造、DLL cookie关闭、父端终态。该拒绝是诊断自身条件不一致，不是原超时根因。原字节与费用保留。

[统一watchdog后继](staged_deliverability_c_saved_fresh_runtime_stack_repair_scope_v1.md)使用core v10、probe/parent v7，两case在同一入口启动一次1s watchdog，独立discovery/profile/stack/saved全部accepted。command29914UTF16，子进程上限3s。stack child在2.2038205s父端收尾、被预期kill，stdout0、stderr1410B、无截断；没有child self-close报告。CPython native watchdog是声明的条件性观察叶，不把Python current_frames单线程当作所有native线程认证。

真实1秒采样的调用关系为：`B_S open_bootstrap_import_boundary → runtime.entry → verify_runtime_namespace → freeze_namespace_graph → visit → early audit`。**采样时尚未进入adapter import**，位置在B_S factory首次runtime入口的namespace图复核。单样本不能证明原9秒全部耗在此，也不是父端独立认证的Python对象图或native owner成功报告。原始stack和命令/源码pins都在receipt，不依赖聊天回忆。

## 保存入口、账与留存

| result root尾段 | 实际终态 | static / unittest秒 | 文件 / bytes |
|---|---|---:|---:|
| runtime_guard_v1_non_authoritative | 27 unit成功；startup成功；import timeout | 11.6225126 / 14.7279370 | 20 / 605697 |
| runtime_trace_v1_non_authoritative | 两次command登记拒绝，无child | 0.8299769 / 0 | 8 / 323696 |
| runtime_stack_v1_non_authoritative | startup成功；SELF profile拒绝 | 2.4523477 / 0 | 14 / 414527 |
| runtime_stk_v1_non_authoritative | 独立stack诊断及metadata saved成功 | 4.6741671 / 0 | 16 / 423384 |

各root均在独立声明的文件/bytes/时间帽内，原失败不退款；组合不声称落任何单root帽。上述scope都只执行已登记的有限动作，没有把先前scope剩余秒数充作新授权。旧static120/总540/import8MiB超帽保持。

保全总入口为`results/tables/staged_rts24_saved_fresh_runtime_guard_checkpoint_v1_non_authoritative/snapshot.json`。该metadata-only检查核305个input pins、四root文件map、各代helper snapshot、raw stdout/stderr、exit、Source49和账；charge0.0812077/2s，不启动任何child/helper/science逻辑。它不是原guard整链saved。

全历史累计static **188.9820286**、pytest **366.4889797**、unittest **44.7637714**、合计 **600.2347797s**。累计意外不接受记录 **20**：旧16 + guard import timeout + trace两次登记失败 + stack首版SELF拒绝；最终stack预期kill诊断accepted不另算意外失败。编辑、审查、Git、Python初始启动和最终exit序列化不计capture，不是完整wall time；无模拟物理小时推进。

Source49集合及每个原字节不变，epoch仍acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875。所有已执行源码、controller、snapshot、profile、admission和结果冻结；新修复必须另建后继，不覆写失败。stk root恰16/16文件，不再向其内添加文件。

## 下一项工作

先读本交接、checkpoint snapshot、guard import_discovery.exit/receipt与stk stack/saved.exit及原stderr，再核Git/process。当前无测试或实验子进程在运行，仅VSCode Jedi常驻；39项并行文稿/文献/图件改动保留。四导航仅修复本任务上一段的中文编码并增加本轮前置段，不暂存并行正文。

下一步先核namespace图重复CodeType fingerprint成本：当前code_token递归const(CodeType)未在函数自身复用code_cache，外层visitor才缓存。候选优化仅把每次freeze本地的immutable CodeType指纹缓存下沉到递归函数，保留每次全图/身份/别名/可变字段复核；不能直接跳过图或跨entry复用认证。先用冻结v2 reader作独立输出/对象顺序oracle，覆盖共享nested CodeType与失败路径，计数hash调用，再做独立有限成本准入。该优化目前**未实现、未测试、未计入完成**；单栈只给调查方向，优化收益仍待测。不要直接重复原长一点的import以等待成功。

E/U、独立TCB/native认证、完整runtime/P1/role/permit/F、科学/资源/正式/run authority仍OPEN/false。27/27只关闭指定开发finding；实际B_S import验收、native owner终态及完整C/F门禁继续未完成。
