# C/F：runtime owner 与 B_S 接线 WIP 检查点

2026-10-27，DRAFT_NONAUTHORITATIVE。接续[真实 ENTRY namespace](continuation_handoff_20261027_saved_fresh_entry_namespace_startup_v1.md)、[本轮范围预算](staged_deliverability_c_saved_fresh_runtime_handoff_scope_v1.md)和[唯一 unit 修复后继](staged_deliverability_c_saved_fresh_runtime_handoff_unit_repair_v1.md)。root唯一writer，独立只读PRE_SEAL；无official verdict、receipt、production seal或运行授权。宽goal继续active，本检查点不表示完成、暂停或formal blocked。

## 当前可确认的进度

已写出 namespace → LocalRuntimeInputs → B_S → adapter 的完整开发接线；本轮只完成逻辑unit及metadata/保全检查，**尚未运行任何cold child**。真实native runtime owner commitment、B_S实际import、B3→M→D动态顺序及两个profile admission均未观察，不把20项unit替代这些证据。此前namespace cold仅证明旧LocalPreEntryInputs的self资源与namespace初始化，不能反推本次runtime接线已成功。

当前修复后继为core `experiments/staged_rts24_saved_fresh_pre_entry_lease_v6.py`、import helper `experiments/staged_rts24_saved_fresh_bootstrap_import_v2.py`、runtime_handoff parent/probe/tests各v2；namespace helper复用entry_namespace_v2。原core v5、import helper/parent/probe/tests各v1、原driver、两份registration/snapshot/transport及全部执行字节冻结。不得原地编辑它们继续运行。

交接实现包含：唯一resource.owner commitment前准备target字段并在audit返回后重验原inputs/namespace/target；commit后保留exact target，失败不回滚owner；旧lease/inputs/namespace沿确切successor链close为no-op；runtime按boundary、namespace、native层分别清理并缓存UNRESOLVED与primary/secondary。普通构造/copy/pickle/通用_set关闭。Namespace消费后有独立held图/metadata verifier，不再调用已CONSUMED的inputs.entry。

B_S实现独立policy/schema、pending claim、同一helper context、原core reader、bootstrap生成并由runtime强持的expected-binding tuple。Factory/loader首次使用helper globals前核held proof；audit中使用无code-getter的identity reader避免重入；handoff token计数要求新hook实际观察。实际import函数尚未运行。Adapter设计核13个源函数、两个类的源码方法/bases、固定常量/GATES/Source49选择，并冻结强持整个直接global/class图；第三方module内部、finder registry内容及native行为仍OPEN。上述设计与unit通过不关闭下面三项新finding。

## 执行记录及费用

结果入口：`results/tables/staged_rts24_saved_fresh_runtime_handoff_v1_non_authoritative`，当前恰17文件/771,531B，canonical文件pin整集SHA `bc8b33b0dc2cb66436e4cc467cc65563866b8e636d85b817cb035d8aa55f5580`，在40文件/8MiB帽内。

| 执行 | 终态 | charge秒 |
|---|---|---:|
| 原registration | accepted | 0.1716148 |
| 原17-node unit | timeout；原stderr恰15个成功点，无完整report | 11.3429030 |
| repair registration | accepted；固定20 nodes | 0.2810581 |
| 唯一unit repair | 20/20；0 failure/error/skip，exit0 | 8.5838460 |
| WIP metadata/pin snapshot | accepted，仅保全/metadata | 0.0530783 |

首次unit费用不退款，原stdout/stderr、exit、admission、capture终态完整保留。两次unit parent process HANDLE均关闭，reader/pipes终态，无cleanup/truncation错误；首次child被timeout终止，不能补造缺失的unit report。repair峰值WS仅为capture观察，不是cold整链RAM准入。

本scope累计static **0.5057512/75**、unittest **19.9267490/35**、总 **20.4325002/110s**。本轮已用预先声明的唯一一次unit repair；**不能继续追加第三次unit或把现有剩余秒数视为新执行授权**。尚未使用的cold预算不是当前字节可启动cold的证明。若继续修复，先建立明确的新版本/有限后继验收范围与累计账，不修改这份历史范围、失败或结果。

全历史累计static **169.3218166**、pytest **366.4889797**、unittest **30.0358344**、合计 **565.8466307s**，累计意外不接受记录 **16**。旧static120/原540及import8MiB超帽原样保留。编辑、审查、Git、Python初始启动及最终报告序列化不在capture内，这些数值不是完整wall time；没有推进模拟物理小时。

`wip_snapshot.json`核了227个输入pins、两代helper snapshot、两份transport、两次raw streams/exit、全部原Source49和旧结果保全。该report为5,372B，SHA `1ff2bea60e5a119c1022c8cff051bbb72101767a36273b4a47ab23a211a823b9`。它不是要求全部cold完成的`driver.saved`包，不调用bootstrap/helper/science逻辑；`acceptance_scope=metadata_and_preserved_bytes_only`。

Source49集合与每个原字节未改，epoch仍 `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`。新helper都在49集合之外，不从当前源重造expected。旧pre-entry61、namespace16、startup23文件仍由原pins承接保全。

## cold 前必须先关闭的三项高风险

精确非权威记录见`pre_seal_open_findings.json`。该记录与snapshot均已保存；不是seal或official review。

1. **完整builtins expected bindings**：probe v2约41–57行只固定builtins dict身份及少量成员，遗漏set/next/map/zip/str/bytes/isinstance等fallback。下一版本应使用bootstrap已持有的完整native tuple固定全部keyset/逐value身份，增加“同dict内替换未列builtin”的拒绝反例。
2. **B_S同对象函数metadata改写**：import helper v2约437–445、500–518行的audit identity reader不读取code，但mutation classifier仅保护finder函数。下一版本须从held proof中metadata非None的rows强持全部B_S module/class函数，以对象身份立即拒绝__code__/__defaults__/__kwdefaults__事件，增加真实setter audit反例；audit分类不得为此重新读code造成重入。
3. **实例_req自校验绕过**：import helper v2约122、338、437、447行通过可变`self._req`断言自身commit。object.__setattr__换成no-op可吞掉拒绝。下一版本应由method defaults强持的原checker/native ValueError先核_req身份与实例image，再使用实例字段；或移除该槽。增加Python级_req槽改写反例，不能选择性称为排除的任意RAM行为。

已关闭的旧finding包括mixed helper contexts、fake pending boundary/reader、空finish证明输入、precommit audit后重验、runtime held checker、namespace snapshot漏项、cleanup控制异常、external读后的terminal bookend与final digest secondary丢失。先前“adapter普通函数清单确定失败”finding读错了experiments ENTRY，已撤销；实际src adapter是13个top-level FunctionDef和两个class，不能继续引用错误诊断。

## 恢复顺序与边界

先核Git/process及本root、两份registration、两次unit exit/report、findings和WIP snapshot。当前没有实验或测试子进程在运行；现场另有39项文稿/图件/文献dirty工作，继续保留。四导航只发布本轮新前置段，不暂存并行正文。当前后继代码均已经执行过unit，必须采用新的versioned successor关闭三项finding。

之后再做独立有限后继的完整成本/调用量准入，优先闭合这三项并跑有意义反例；通过独立PRE_SEAL后，才考虑startup discovery/admission、一次B_S import discovery/admission、正常及六个故障窗口的cold计划。**不可直接从当前repair_driver继续discovery/import/probes路由**。若将来需要native模型、solver、P1、OwnedChild/Job或实际F，仍按原规则另取具体授权。

E/U、独立Python/TCB/native认证、full runtime/P1、role/permit、F、科学/资源/正式/run authority均OPEN/false。20项unit只支持当前已测的开发行为；54根/76证据节点的冻结catalog及所有历史结果不改写。

发布时保持两份已执行import helper的原末尾空行；diff格式检查仅排除这项blank-at-eof提示，其余trailing-space/space-before-tab检查通过。所有暂存源码/结果逐blob等于原raw字节，四导航暂存内容仅为HEAD正文加本轮新段，不包含并行dirty正文。
