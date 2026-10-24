# C：F 只读 adapter／启动前协议组件交接

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[F设计交接](continuation_handoff_20261025_saved_fresh_scope_budget.md)。起始HEAD为`7610583dc1dab691a2617e9c89b5f0c41b583dad`；本轮发布hash以提交后远端读回为准。目标仍是完整F，不把本组件当成F完成。

按[原范围/预算](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)及[组件合同](staged_deliverability_c_saved_fresh_adapter_development_contract_v1.md)，实现三个原预留路径的provisional draft：src只读adapter、experiments启动前协议、对应测试。SF49仍是原45＋原定四路径；原scope页中“文件未创建”是设计检查点当时状态，原页hash保持，现状由本页补充。三个draft尚未seal，可在本候选内迭代；每次必须保留已测snapshot并重新验证受影响字节，不能沿用旧结果证明新代码。

adapter实际调用原B/C/E，保持原P1 h=-2..2五模拟小时/21点、五accepted/一个terminal/130CAS。最终parent普通检查的test-call约28.03s；完整19项metrics与保存值相同，21 refs、六prefix和完整trusted tuple逐域绑定到外部caller image。历史fresh只作额外固定baseline，尚无新增五小时fresh进程。missing_input/committed/known、coverage=false/双null、余额0/resume=false与原D四行边界均保持。

trusted initial capture冻结锚原字节/pin/identity/祖先、P1全部683 pins/metadata/directories、fixture/query/state预期及source；角色hold必须消费同一外部image，双方同步改caller标签或同改payload域仍拒绝。context绑定compute exe/env/source、固定输出或严格pytest临时mode、父链与started+180；argv从同一raw/SHA生成，实际entry/argv核对，production角色拒绝test mode。metadata安全会计只收不可变创建进程token，固定全局O/identity，返回safety_only/unknown，四份128KiB预留不漏算。replay异常仍做末次书挡，双错分别保留。

最终85新＋9原trusted-binding回归，共94唯一nodeid，按70＋12＋12互斥组终态通过；wrapper wall约67.25/53.734/39.813s。原24项组合在90s帽超时的原始日志保留，不计通过；split前已固定nodeid和不扩时预算。相同最终源码批次含失败实际约250.844s，低于360s普通检查预算；这不是F资源实测。早期63/68项仅列历史，不重复计数；首轮和最终源码snapshot、raw日志与完整pins均保存。详见[报告](../../results/tables/staged_rts24_saved_fresh_adapter_v1_non_authoritative/validation_report.md)。

当前ENTRY作为脚本只会显式非零退出，实际短`--help`探针exit1；stage supervisor、两层owner/quiet、parent/fresh CLI编排、真实候选/观察发布和external trusted invocation尚未实现。纯payload比较明确保持两个局部fresh/process/adoption字段false；全P2科学采用/journal/expected provenance、完整139/F-X、resource/formal均false，`F_launch_admitted=false`。没有新native、公共P2、production context/lease/receipt/seal或长实验。

下一步继续完整F：先实现并普通测试stage-aware retained-owner 40/50s及180s整链停止、nested Job成员完整性、启动capture/cleanup、独立fresh_parent目录、失败/发布窗口及四记录长度；补足controller自身资源和同步I/O的外部trusted invocation能力。然后才判断一次真实F的已有授权/安全条件。不能把原guard的单wall直接解释成40+5+5，也不能用本组件的test wall关闭原65s余量或C整体预算。

926旧发布路径、三导航原body、P1全部683及原七输入/packet/B1–B3/guard/outer/B/C/D/E/journal保持。恢复先核Git/进程、读本页/合同/原预算与blocker顶部；运行新证据`checks_01/saved_checks.py`及原E保存检查器，均用`D:\Miniconda3\envs\compute\python.exe -B`。新checker区分冻结测试snapshot与可继续修改的canonical draft；若draft不匹配，不得把本轮通过当作当前代码证据。只读PRE_SEAL仅为组件审阅，没有official verdict或运行授权。昂贵失败/十小时增长/full wall/RAM/storage、C整体及D/E现实输入/比较/选择/敏感性/冻结后留出继续OPEN。
