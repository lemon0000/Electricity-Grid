# C/F：缓存候选拒绝，pre-import真实接线与图成本已测

2026-10-27，DRAFT_NONAUTHORITATIVE。接续[guard/stack交接](continuation_handoff_20261027_saved_fresh_runtime_guard_stack_v1.md)。root唯一writer，独立只读PRE_SEAL；无official verdict/receipt/seal或运行授权，宽goal继续active。当前证据不证明完整B_S import、LIVE或实际F。

## 缓存调查的否定结果

[code cache范围](staged_deliverability_c_saved_fresh_namespace_code_cache_scope_v1.md)新增namespace v3，把immutable CodeType指纹memo下沉到递归函数，强持code、按identity区分、只在一次freeze内有效；seen/nodes/objects及每次完整图复核不变。34项全部完成，33通过/1 failure/0 error/0 skip，capture exit1且正常收尾，charge4.1633237/12s，无timeout。

唯一failure是实际完整ENTRY的收益条件：old/new SHA均**696**，`assertLess`失败。此前image逐值相等、objects等长/逐项is已通过；其余26项旧namespace回归及共享DAG、equal clone、位置、unsupported/fresh、跨freeze、零global、metadata audit序列通过。合成共享nested code为5→3，不代表实际收益。Actual用例在失败处结束，未执行后续三轮wall观察，不能补造benchmark。该scope`metrics.json`仅有合成数据；真实696来自完整保存的失败stderr。

**NSv3候选未采用，不接任何cold或core。** 原v2继续作为生产开发基线。新增失败/源码/快照及rejection_snapshot全部冻结，累计意外不接受**21**。该负结果排除本候选对真实ENTRY的SHA次数收益，不排除其他成本问题。

## 原reader外层时标与真实pre-import终态

[外层时标范围](staged_deliverability_c_saved_fresh_namespace_graph_timing_scope_v1.md)新增`entry_namespace_timing_v1.py`，从冻结NSv2复制。原reader源码AST含位置一致，CodeType除所属helper文件名外递归相等；仅由default-held wrapper发enter/exit，不跳过任何图、身份或可变字段检查。6/6逻辑unit通过，0 failure/error/skip，charge1.2541175/4s；独立只读复核无must-fix。

当前诊断组合：core v11、parent/probe v8、timing helper v1，BS v3原bytes。独立startup discovery/profile通过；唯一pre_import child在PATH6后主动抛`diagnostic_stop_before_adapter`，**adapter import0**。该case child exit1为预期stop，parent receipt accepted，未kill，计费1.7768287/6s；controller含前后检查计2.2026737s。

本次有完整child报告，且parent核PID/process creation/image/command line：

- 实际resource.owner为runtime，旧inputs/namespace successor均指向它，旧对象CONSUMED。
- 新B_S hook installation sentinel=1，audit handoff witness=1，实际path已准入到PATH6；没有M/D迁移或adapter调用。
- Source49 open计686，write/process/protected-open均0，early blocked/旧guard faults为空。
- 原异常保持主动stop；runtime最终UNRESOLVED，boundary FAULTED且hook inactive，secondary为未完成import policy，不能洗成B_S CLOSED。
- 两个self HANDLE各close一次，[1,1]；resource CLOSED，DLL cookie关闭，自有ENTRY alias移除。
- parent process HANDLE/stdin/writer/reader/pipes均终态，无cleanup/truncation。

这首次给当前接线提供完整的native owner→B_S安装/交接→PATH6→主动停止→分层清理的开发见证，仍不是角色permit、独立Python图认证或formal/run authority。

stderr共**16组完整enter/exit**、无未配对enter；外层时长合计**0.5314062s**，最小**0.0297430**、最大**0.0408129s**。时差包含enter JSON/write/flush、held FunctionType构造及完整reader，不含exit输出，属于外层上界观察，不是纯reader CPU。16次包括本诊断的正常阶段和cleanup；不得作为adapter或完整workflow调用数。源码静态的import前15次下界也不等同本次实测映射。

原9.516秒超时仍未解释。当前独立pre-import已在1.777秒内按计划停止，图包装合计0.531秒，且真实SHA计数不降；**不能再把单次1秒栈或合成cache收益称为原超时根因或解决方案。**

## 保存、累计账与恢复

Cache root `results/tables/staged_rts24_saved_fresh_namespace_code_cache_v1_non_authoritative`：原unit失败正常收尾，rejection_snapshot只作保全与不采用决策；不执行原driver的成功saved路由。

Timing root `results/tables/staged_rts24_saved_fresh_ngt_v1_non_authoritative`：unit、PRE_SEAL记录、discovery、profile、pre_import、saved均accepted。`saved_report.json`只保存metadata/原时标；之后新增`checkpoint.py/json`独立核源/结果/原streams并计费，不反称其已被原saved.exit绑定。该root恰24/24文件，不继续添加。

本scope timing含post-checkpoint累计static**4.7984572/20**、unittest**1.2541175/4**、合计**6.0525747/24s**。Cache scope static**0.1682309/8**、unittest**4.1633237/12**、合计**4.3315546/20s**，含失败，不退款。

全历史累计static**193.9487167**、pytest**366.4889797**、unittest**50.1812126**、合计**610.6189090s**，意外不接受21条；旧120/540/import8MiB超帽保持。编辑/审查/Git、Python初始启动和最终exit序列化不计capture，不是完整wall，无模拟小时推进。所有已执行源码/controller/profile/结果冻结，不原地修复或重跑。

Source49及每个原字节不变，epoch仍acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875。39项并行文稿/图件/文献dirty保持，只发布本轮范围及四导航新段。

恢复先读本交接、cache的rejection_snapshot/unit raw stderr、ngt checkpoint/saved_report/receipt及frame raw，核Git/process与source pins。下一项应针对实际adapter import内部阶段，复用本次pre-import成本和冻结reader/BS3证据，明确新的全路径调用量、一次次数和有限预算；可在B_S helper外层加阶段时标，在真正import开始后再安排一次stack采样，避免再次只采到前置图。不要采用无实际收益NSv3，不直接重跑原10秒import或扩帽等成功。

三项guard finding已有27项开发验证；实际B_S import的M/D、NumPy政策、closed profile和完整runtime、E/U/P1/role/permit/F/科学/资源/正式/run门禁均仍OPEN/false。
