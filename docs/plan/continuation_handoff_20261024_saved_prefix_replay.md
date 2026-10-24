# C：保存短前缀的独立 query 与 accepted state 交接

2026-10-24，DRAFT_NONAUTHORITATIVE。接续[单点交接](continuation_handoff_20261024_saved_point_replay.md)。起始HEAD/origin为`367e9d55788ccad7098ce424c548f1566f8c3bcc`；最终发布hash以提交后远端读回为准。

本轮按[前缀合同](staged_deliverability_c_saved_prefix_replay_contract_v1.md)接通[DAG](staged_deliverability_c_scientific_adoption_dag_v1.md)的B→C→B：独立fixture/init、原reference compiler与原prepare/propose生成actual query，只有重建且接受的actual推动下小时state。原C逐点raw→snapshot/import→独立KKT/primal及精确typed SHA保持不变。新增reader只支持P1的on_time/early/full_temporal，从-2开始最多五小时/21点，保留失败停止和visited-point/source/fixture/caller末次书挡。

39个定向检查（38解析/失败/漂移＋1保存前缀）和126个相关causal/reference/单点回归通过，共165唯一nodeid。原P1五小时21点query/证据SHA、五次accepted state SHA均重建相同；actual slot4/8/12/17/21，覆盖故障调用和恢复。compile42/import21、execution audit16/历史重审40、reference_requests55、source读取1912/point读取2152已计数；完整identity书挡为8M+32/点。测试wrapper wall约18.04/21.61/50.43s，五模拟小时不等于wall；RAM/峰值storage/full outer尚无测量。独立PRE_SEAL三项findings已闭合：terminal成功锚矛盾、拒绝attempt摘要、同字节身份替换；初轮三个fixture失败与日志保持。详见[报告](../../results/tables/staged_rts24_saved_prefix_replay_v1_non_authoritative/validation_report.md)和checks_01。

732旧发布路径、三导航旧正文、旧postcheck stdout和P1全部683文件保持；原P2七输入/packet/B1–B3/guard3/outer/原C/numeric/codec/journal没有修改。1024含owner历史identity上界、launcher和parent各128KiB收尾合同仍适用。PRE_SEAL仅作只读开发审查，未生成official verdict/receipt/seal。没有新native、公共P2、journal写入或长实验。

下一步优先D：固定原P1四个F/X代表row（小时1、2各branch_0/generator_0）、对应points22..31，先列独立normal/firm/raw DAG及调用预算，再复用C重建后调用原audit_legal_x，逐行对照保存audit；独立firm与raw KKT及legal-X=false都须保留，不能由actual轨迹替代。不得把合法/非法代表行提升为完整139/F-X时序、minimum或工程安全。保持原合同定义和数据，按原规则只做有界保存重放与解析检查。

E随后使用外部先持有的trusted genesis/head/state/CAS/failure绑定和原read-only journal.reopen，验证完整政策/余额/期限、accepted/pending/unaccepted/failure，不调用任何writer/resume；本轮state SHA一致不能替代E。F仍需fresh与最终父采用/失败发布。全P2 expected provenance、scientific_evidence_adopted、journal_replayed、139/F-X、resource/formal均false；原missing_input、coveragefalse、双null保持。完整319、十小时增长/昂贵失败/full wall/RAM/storage、65s父端余量、C整体与D/E现实输入/方案/选择/敏感性/冻结后留出仍OPEN。

恢复先读本页/合同/DAG与C计划/blocker，刷新Git与进程，并运行本证据目录的`checks_01/saved_checks.py`。root唯一writer；R3按agent.md §7独立只读PRE_SEAL，不分叉。新范围只用successor路径和显式预算，继续遵守零新native/不开长实验边界。
