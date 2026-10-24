# F 只读 adapter 与启动前协议：组件开发核验

2026-10-25，DRAFT_NONAUTHORITATIVE。按[组件合同](../../../docs/plan/staged_deliverability_c_saved_fresh_adapter_development_contract_v1.md)和[原F预算](../../../docs/plan/staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)推进，交接见[本轮入口](../../../docs/plan/continuation_handoff_20261025_saved_fresh_adapter.md)。本轮实现完整F所需的只读B/C/E adapter和启动前协议组件；完整F进程/发布流程仍未实现。

原P1五模拟小时/21点的真实同进程parent adapter完成：19项metrics与原保存fresh完全一致，typed state根仍`29517379c102b40b0f0a0b77711db4d936357025e4f53283f5bdec04fcbc7a41`。query仍由原B政策与接受前缀生成，raw/snapshot/import/KKT和journal_v2.reopen未替换。完整metrics、21个request/result引用、六prefix和trusted tuple额外绑定外部原库存；历史fresh只是固定baseline，不能证明新增fresh。D四行未纳入本次科学重算。

最终collection有85新＋9原trusted-binding回归，共94唯一nodeid。最终采用protocol_03的70项及chain_bindings_04a/b各12项，三组互斥且覆盖全部94；均exit0/无timeout/源码书挡相同。wrapper wall分别67.25/53.734/39.813s，saved-parent的test-call约28.03s。chain_bindings_03在90.047s触帽，原始23 dots不计通过；当时操作者作过CIM检查，未将独立进程观察保存到仓库，不作为可复现的所有权/资源证据。随后冻结原24项顺序拆12＋12，各90s，不扩大帽。相同最终源码批次含该失败为250.844s；普通测试wall不作F或整体资源准入。

早期adapter_01有63项通过，protocol_02有68项通过，属于较早draft，仅保留原日志/pins，不计最终94。首轮和最终三源码另存snapshot；中间68项没有独立完整源码snapshot，不作为完整字节复现证据。`split_admission_04.json`保存拆组前nodeid、source pins及337.297s最坏测试预算核对。全部历史轮次和失败均保留，不把总执行次数当样本量或独立结论。

独立只读PRE_SEAL促成外部caller冻结、context输出/deadline/argv绑定、stdlib环境构造、实际ENTRY核验、metadata unknown标签/全局根、不可变token、pytest mode隔离及双方同错payload绑定。replay失败补最后书挡，primary/bookend双错独立保存。最终纯比较只返回payload byte equality，局部process/adoption及全局科学/资源/正式门禁false。审阅适用范围为本组件，不产生official verdict、receipt或seal。

ENTRY当前明确非零退出；普通短`--help`probe exit1且无科学导入/执行。原compute标准库保存检查exit0、stdout与前轮逐字节一致，复核原P1全部683。926旧发布路径/三导航原body及SF49原45来源保持。新输出会计仅做metadata安全扫描、四记录512KiB预留与8MiB/64预算检测，不是稳定库存或filesystem配额；没有新增full F调用计数、whole wall/RAM/storage、source/runtime全闭包或OS command-line证明。

最终证据见`checks_01/ordinary_check_summary.json`、`preseal_review.json`、`document_checks.json`与`tested_draft_snapshot.json`。raw日志按原bytes保存，空白格式例外仅适用于明确literal路径及pins；其余代码、文档、JSON严格检查。`checks_01/saved_checks.py`可用标准库重验历史与snapshot，并另外报告canonical draft是否仍匹配，不进行科学重放。

尚缺stage-aware owner/40/50/180s停止、nested Job完整历史成员/quiet、实际parent/fresh角色、publish/cleanup窗口、四记录长度及external trusted invocation。没有新增五小时F fresh、native/P2、production context/lease/receipt/seal或长实验；`F_launch_admitted=false`。原65s余量、完整319/139/F-X、整包科学采用、C整体和D/E现实输入/比较/选择/敏感性/冻结后留出继续OPEN。
