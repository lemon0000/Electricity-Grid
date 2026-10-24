# 保存短前缀：独立 query、actual 与 accepted state 验证

2026-10-24，DRAFT_NONAUTHORITATIVE。起始HEAD为`367e9d55788ccad7098ce424c548f1566f8c3bcc`，工作区干净，只有VS Code语言服务Python，无科研run。按[合同](../../../docs/plan/staged_deliverability_c_saved_prefix_replay_contract_v1.md)连接原[DAG](../../../docs/plan/staged_deliverability_c_scientific_adoption_dag_v1.md)的B→C→B。

原P1五个模拟小时（-2..2）、21个已保存实际路径点已只读重建：原fixture/init→独立reference/raw/recovery→原政策actual query→原C双compile/raw snapshot/import/代数审计/精确typed证据SHA→原accept/独立execution audit→下一小时。actual位于4/8/12/17/21；21个query及证据SHA与原point一致，五个accepted state SHA与外部固定prefix记录一致，小时1有故障调用、小时2有恢复。只核state SHA，不运行journal reopen或采用其chain。终态仍为缺少后续输入的前缀，coveragefalse和两个条件null保留。

定向38个解析/失败/书挡检查和1个真实保存前缀检查通过，相关126个causal/reference/单点回归通过，共165个唯一nodeid。`checks_01`保存终态、source前后pins、collection与只读PRE_SEAL记录。独立审查发现的terminal成功锚矛盾、拒绝attempt摘要及同字节身份替换三项已修复并复核，剩余findings为空。三次初轮fixture失败保留：负小时设备尚未投运、错误地预期一个可接受政策会拒绝、单文件超过原8MiB pin帽的合成输入。修正解析fixture和断言后完成相应检查，没有改变原政策、原C或保存点。

保存前缀计数为compile42、snapshot/import各21，prepare/propose各10、execution audit16、历史row重审40、reference_requests55；source内容读取1912，185个point CAS对象对应2152次point内容读取（8M+32/点）。计数覆盖原accept内部prepare/propose和独立prefix审计，保留重复parent/KKT。普通pytest wrapper wall分别约18.04s、21.61s、50.43s；保存前缀单项测试call约18.85s。这些是普通测试观测，不能作为完整outer或十小时资源预算；RAM/storage峰值尚未测量。

原P1全部683文件、732旧发布路径、三导航原正文及前轮stdout精确保持。原七输入、packet、B1–B3、guard/outer/checker、原C/numeric/codec/journal均未改。仅新增版本化reader/test/合同、此证据目录、交接与导航头部记录；不生成P2/native/生产manifest/lease/seal。

访问slot的预期query来源已由独立政策前缀重算；全P2 expected provenance、scientific_evidence_adopted、trusted journal、完整139/F-X、resource/formal均为false。D firm/legal-X、E trusted genesis/head/state/CAS/failure及原read-only reopen、F fresh/最终父采用仍须分别连接；完整319数据、十小时增长/昂贵失败/full wall/RAM/storage、65s父端余量和C整体预算保持OPEN。下一步见[交接](../../../docs/plan/continuation_handoff_20261024_saved_prefix_replay.md)。
