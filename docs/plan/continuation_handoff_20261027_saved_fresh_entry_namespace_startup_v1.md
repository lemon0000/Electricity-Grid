# C/F：真实 ENTRY namespace、冷启动修复与保存检查点

2026-10-27，DRAFT_NONAUTHORITATIVE。接续[pre-ENTRY v2](continuation_handoff_20261027_saved_fresh_pre_entry_lease_v2.md)、[namespace范围](staged_deliverability_c_saved_fresh_entry_namespace_scope_v1.md)及[显式startup修复后继](staged_deliverability_c_saved_fresh_entry_namespace_startup_repair_v1.md)。root唯一writer、独立只读PRE_SEAL；无official verdict、review receipt、production seal或运行授权。宽goal继续active。

## 实际接线结果

当前bootstrap为 `experiments/staged_rts24_saved_fresh_pre_entry_lease_v4.py`，新parent/probe/tests为namespace各v2，组合持有组件为 `experiments/staged_rts24_saved_fresh_entry_namespace_v1.py`。先匹配独立startup画像、取得真实process/thread self query HANDLE、持有Source49 raw并转交LocalPreEntryInputs，再执行持有的完整ENTRY unit。Source49集合与原字节不变，epoch仍 `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`。

reference先在 `experiments.staged_rts24_saved_fresh_adoption_v1` 名称下初始化并冻结表示图，移除自己注册的校准alias后，actual以同名create-only注册并初始化。两个对象都用package=experiments、absolute原ENTRY路径、原builtins、spec/loader=None，globals/locals为同一dict。reference仅由owner强持，不留alias；REFERENCE_NAME保留为冲突检测项。该顺序让dataclass生成文档、annotations与原字符串常量保持精确，不改写模块名文本来掩盖差异。

这是实际ENTRY顶层exec，包括21个dataclass、contextmanager/classmethod/property、16次__init_subclass__及unit seal内省。它是固定名称下的held-byte namespace，bootstrap main/argv/path/env保持；没有运行ENTRY main/CLI、科学adapter、P1/科学replay、OwnedChild/Job或实际F。旧direct-main/self-anchor接口不能用于这个执行模式。

实际namespace与同raw/同条件性TCB产生的不可变参考图匹配，强持2,940个实际图对象并逐次核identity。图覆盖source/生成方法、class/bases/descriptor、closure/cell、defaults、dataclass元数据和常量容器/alias；未知类型、50,000节点或256深度超帽拒绝。图读取器及全部嵌套code的global读取/写入/删除opcode均为0，由held CodeType及原primitive/stdlib叶执行。loader先核helper原code/default/closure/native根，再给factory固定expected bindings；input entry/source返回、exec及清理后均有书挡。

LiveEntryNamespace以组合方式强持原LocalPreEntryInputs，**native resource.owner仍是该inputs**。字段普通写入关闭；namespace/global/alias不一致进入sticky FAULTED，close后保存UNRESOLVED和原分层failure，即使两个HANDLE已关也不洗成成功。foreign/额外alias保留，只移除自己注册且仍指向原module的canonical alias。对象、原异常和能力不跨进程序列化；报告时live=false。

## 原失败及修复

原namespace root为 `results/tables/staged_rts24_saved_fresh_entry_namespace_v1_non_authoritative`，恰16文件/394,673B，canonical整集SHA `0fa866ffc408114be70fb623cf498e2d54e49f6cfd7ab1b70bea7bd25098b24a`。原六helper/controller字节、23/23 unit成功、原discovery/admission、首次normal失败全部保持。

该normal在冷环境第一次import dataclasses→inspect→dis时，collections.namedtuple合法设置 `__new__.__defaults__` 被full guard拒绝；随后helper尚未定义NamespaceConstructionFailed，错误处理又发生AttributeError。原child exit1、stdout0、stderr1271B原样保留，parent HANDLE/stdin/writer/reader/pipe终态。有完整stderr而无child正常self清理报告，不能补造self-close见证。本轮新增这一条意外不接受记录，历史累计15条；四个按设计拒绝的cold不另算意外失败。

startup v4只将dataclasses预载移到early audit后、full guard前，作为明确条件性stdlib初始化纳入新画像；full guard安装后的metadata规则保持。probe v2支持部分helper的安全owner读取与固定alias报告，并加入helper_init_failure故障窗口。manifest/report分别版本化为 `staged_saved_F_pre_entry_manifest_v2` / `staged_saved_F_entry_namespace_probe_v2`；旧v1闭域保留。新startup profile独立discovery并admission，没有采用旧transport画像。

## 当前终态证据

以 `results/tables/staged_rts24_saved_fresh_entry_namespace_startup_repair_v1_non_authoritative` 为当前入口。26/26 unittest通过，无failure/error/skip，包含原图/身份/闭合/故障逻辑、部分helper错误与新schema拒绝旧v1的行为检查。unit只用逻辑inputs；真实self资源由下列cold证明。

| cold | child | namespace与初始化 | Source49 open | self close |
|---|---:|---|---:|---|
| normal | 0 | CLOSED；reference/actual共2次完成；2,940 objects | 539 | [1,1] |
| global_rebind | 1 | 精确graph拒绝，UNRESOLVED；共2次 | 490 | [1,1] |
| alias_replace | 1 | 精确alias拒绝，UNRESOLVED；共2次；foreign保留 | 490 | [1,1] |
| partial_namespace | 1 | actual注册后、exec前拒绝；reference完成1次，actual未初始化；UNRESOLVED | 392 | [1,1] |
| helper_init_failure | 1 | helper ModuleType已建、定义未执行；namespace=null，exec0次 | 294 | [1,1] |

五个parent诊断receipt均accepted；四个child exit1为预期拒绝。五例原source均CONSUMED、inputs均CLOSED；P1/write/process计数0，early blocked及sticky guard faults为空。所有parent process HANDLE、stdin/writer、reader/pipe终态，无cleanup/error/truncation；最高单例0.963837/2s。原失败child未提供的self清理见证不由这些后继反推。

新discovery包含dataclasses/inspect/dis，实际观察107个runtime disk文件、16,013,493B，符合128文件/32MiB census范围。profile33,196B / `860bccf83954779389e8fdb79a55ca77d10c8e4dc6c1e685e82bfad15f55a982`；transport21,947B / `3a6bbd2c834ba09a411020ba395a5667df8bffda5605e217590a2c430f633b50`；五行raw journal34,732B / `721da7aef11394f24736c27aa7314de1ae5084872a9c4a6a6a71330138b16d93`。184个input pins、Source49、helper6、profile pins、plan/raw和各exit控制链已核无漂移。fresh saved只重核metadata/原bytes/pins，不重跑bootstrap或科学逻辑。

独立只读PRE_SEAL终态无must-fix。新增 `pre_seal_findings.json` 是非权威摘要，**不在原saved.exit已绑定字节内**，不是seal/receipt。direct discovery/profile/probes的外层exit0仅在本次tool终态观察，不存在独立terminal capture字段，证据只支持draft milestone。unit/saved峰值WS分别99,913,728 / 29,720,576B，仅观察，未证明cold整链RAM或硬停止。

## 预算、留存及恢复

原/新namespace共用static40、unittest20、总60。含原失败最终static7.4546367/40、unittest7.6323899/20、总15.0870266/60s；原23-unit3.6822834、新26-unit3.9501065/repair8；两次登记合计0.2904292/2。原失败probes0.6066815＋后继五例4.488248＝5.0949295/12s，不退款。余量不是新运行授权。

全历史累计static168.8160654、pytest366.4889797、unittest10.1090854、总545.4141305s。旧static120/原540与import8MiB超帽保持；独立后继不把全累计重新算作旧帽通过。计费排除编辑/审查/Git、Python初始启动和最终exit序列化，不等于本轮完整wall time；没有推进模拟物理小时。

旧namespace16文件/394,673B保持在其32/4MiB帽内；当前后继新增findings后23文件/516,840B，在独立24/4MiB内。组合39文件/911,513B仅如实报告，不称组合在原32文件内通过。更早pre-entry61文件/1,034,019B原样保持。

恢复先读本交接及当前root的 `registration.json`、`probes.exit.json`、`saved.exit.json`、`saved_report.json`、`probe_cases.receipts.jsonl`、`pre_seal_findings.json`，核Git/进程、原16及更早61整集、184 pins与账。已执行controller/helper/record均固定，create-only动作不能直接重跑覆盖。当前namespace graph不是catalog的official witness，旧54根/76节点的冻结记录不改。

## 下一项连接

下一scope须实现versioned namespace/input → composite runtime owner handoff，在改变path或finder之前一次性移交真实self资源及实际namespace，保留原source的CONSUMED、pre/post-commit失败和原cleanup根。当前L控制像固定path/meta_path，当前namespace entry还会调用L；不能跨adapter import直接继续使用、改control或外部直接赋resource.owner，也不能只强持旧L后宣称runtime owner已建立。

接着以新的B_S schema/class/factory拆开open active boundary → installation sentinel → early/full guard交接 → path4到path4+ROOT+site-packages → adapter import → M/D认证 → finish。新profile须明确只允许当前exact ENTRY namespace，同时要求其余项目/科学依赖cold；旧v3硬编码policy/baseline4和封装open/import/close的API均不能复用为此模式。先登记完整调用DAG、Source49/外部代码、规模、成功/失败窗口与时间/留存预算，复用本轮证据后再做短诊断。

整个compute VM/compiler/stdlib/native/kernel仍为条件性TCB；profile只是路径/文件观察，P/D/L不证明E/U。transitive live runtime、finder registry内容/callback、上游owner、request/context、broker ACK、issuer/permit、完整quiet/return/G0/G2/G3/H3仍OPEN；runtime v2 UNDECIDED、旧v3 proposal inadmissible。全部TCB/native/独立根/parent Python图认证、完整runtime/P1、角色/F/科学/资源/正式/运行权限维持false。

Git仅同步本轮新source/tests、两scope/交接、原失败及后继结果与四导航短prefix；并行论文/文献/绘图和导航旧body保持。发布后回读远端hash及检查scope/worktree；整个工作区不宣称clean。
