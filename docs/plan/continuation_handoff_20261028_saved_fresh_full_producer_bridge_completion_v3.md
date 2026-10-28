# F：控制器修复与完整Module代码桥验证完成

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[未执行WIP交接](continuation_handoff_20261028_saved_fresh_full_producer_bridge_wip_v1.md)。本轮已完成第5组控制器修复及第1—4组源码修补的普通验证；完整producer、父端科学采用与完整F仍OPEN。root唯一writer，bridge_pre_seal独立只读PRE_SEAL及终态重开；没有official verdict、receipt、production seal或新增运行权限。

## 当前可复用检查点

当前实现为[构造器v3](../../experiments/staged_rts24_saved_fresh_prebound_expectation_code_v3.py)、[构造器4项测试v3](../../tests/test_staged_rts24_saved_fresh_prebound_expectation_code_v3.py)、[控制器12项测试v3](../../tests/test_staged_rts24_saved_fresh_full_producer_bridge_controller_v3.py)、[driver v3](../../results/tables/staged_rts24_saved_fresh_full_producer_bridge_v3_non_authoritative/driver.py)，合同为[scope v3](staged_deliverability_c_saved_fresh_full_producer_bridge_scope_v3.md)。这些已执行source/scope/input/result bytes全部冻结，不在原路径修改或重跑。

Root `results/tables/staged_rts24_saved_fresh_full_producer_bridge_v3_non_authoritative`，**6文件653014B**。checkpoint SHA **71b32f62900411f30a985c7cb15b07733863037d6f3bbd0b39cd65d823e6f998**，accepted=true、diagnostic_accepted=true、accounting_complete=true，范围严格为`source_derived_prebound_capture_code_only`。register、唯一unit、PRE_SEAL、saved重开、checkpoint全部accepted；accounting_errors=[]、pin_errors=[]。

代码桥只在完整冻结ENTRY Module AST中唯一替换capture函数，新增显式binding参数、移除唯一第二次_expectation_adapter preparation、改显式derived函数名。完整raw Module为original权威，inverse完整Module CodeType逐字等于raw；derived中**292个非目标top-level roots及其嵌套code**仅规范化derived filename后逐字相等。target的signature、binding参数/cell顺序、bookends freevars/完整代码、source精确RHS、Store/Del禁止、其余AST位置及inverse均通过。代码生成未exec/import Source49目标模块或读P1；helper/tests自身正常执行。

完整前驱集合逐层重建，保留NFC12 inherited1157 canonical pin、direct360、metadata effective1167及union1167，拒绝删除已继承direct项后动态union仍1167的伪装。v1/v2全部旧输入、own和失败root继续继承；v3 inherited1195 + own7 - overlap2 = **1200**，archive精确为**162文件15020446B**。registration/check与独立只读重开均核完整set、pins、路径/resolve唯一、dict后count及bytes。

第5组控制器已覆盖严格accepted phase prefix、拒绝后停止payload、终态create-only；checkpoint previous/replay/canonical异常独立保存真实charge、known/raw pins与错误。可安全解析但非canonical的record保留已知charge及不接受record名，累计明确incomplete/null；不可解析、duplicate key或无效charge仅保留raw pin并明确未知。历史累计按**不接受record数**续计，不按package重写。

## 当前实际测试与费用

唯一v3 unit **16/16、34帧、0 failure/error/skip**；stdout5499B、stderr2752B、child rc0、capture_error=null。外层**8.920281500002602/10s**，stderr runner **1.771s**。原流pin、admission、16个唯一节点的start/end顺序、report及saved canonical关系均核验；HANDLE、pipes、reader threads全部终态，无kill/truncation/cleanup/reader错误。

Native sampled memory 328 healthy samples，peak working set parent94765056B、child103677952B，同次peak字段之和最大198443008B，未触发256MiB/process或512MiB/pair停止帽。该观测不证明continuous、descendants、独立TCB或128MiB combined retention。

|阶段|实际charge秒|cap秒|
|---|---:|---:|
|register|2.0917207000020426|5|
|唯一16-node unit|8.920281500002602|10|
|PRE_SEAL|3.429427900002338|5|
|saved|3.390836600010516|5|
|checkpoint|1.737507599988021|5|

本包static **10.649492800002918/25s**、unit **8.920281500002602/15s**，共 **19.56977430000552/40s**。各scope的剩余预算留原包，不退款、不重置、不转用。累计static **547.4402389000127s**、pytest **366.48897970000326s**、unittest **211.77721390000443s**，总 **1125.7064325000204s**；不接受仍 **41条record**。从本轮接手的1088.9926936999939s起，三包含全部失败实际新增36.71373880002648s；这不是三个scope预算合并或余量转用。费用为受控capture阶段，不包含工程编辑、只读审查和Git全部wall。新增模拟跨度0h。

## 本轮两次拒绝原样保存

1. **v1 register拒绝**：原第1组补丁要求完整raw模块root CodeType等于孤立FunctionDef编译结果，实际因模块编译上下文导致json.loads、os.getpid等LOAD_GLOBAL/LOAD_ATTR调用编码不同而拒绝。register2.254955600001267s，unit0；metadata checkpoint accepted=true（仅封存拒绝元数据，diagnostic_accepted=false、accounting_complete=true），费用1.273546800002805s，共3.528502400004072s。不接受39→40。Root3文件28030B，checkpoint SHA `2131ddcdadfab0ecc6bd0286bbd450555a8b4934694fd37d952ac0dc325bc4b2`。v1 source/scope/tests及原失败字节全部冻结。
2. **v2 unit外层超帽**：[scope v2](staged_deliverability_c_saved_fresh_full_producer_bridge_scope_v2.md)改为完整Module上下文，register通过；内部16/16、34帧、runner3.087s、childrc0及资源收尾通过，但外层10.225993700005347s超过10s，保持accepted=false、error=phase_cap_exceeded，未进入PRE_SEAL/saved。metadata checkpoint accepted=true、diagnostic_accepted=false、accounting_complete=true；register+unit+metadata checkpoint共13.615462100016885s，不接受40→41。Root4文件642251B，checkpoint SHA `2f3b0532882f8050bdf2e3f236f0a9cb61b3250710c602d1da7e4e64c571b843`。v2 source/scope/tests及原流完整冻结。

v3保留原10s阶段帽，仅删除与inverse相同的original AST重复编译，并将hostile AST的12次全模块parse改为一次冻结模板加逐反例deepcopy。正常全包成功derive完整Module编译48→36次，小夹具另2次；14次builder.current/derive显式49-source freshness读仍686，前后和parent/child全量checks均保留。当前内部测试通过与资源停止帽满足仅属于v3冻结epoch；不把v2外层拒绝改写为通过。

## 下一步从哪里继续

本轮验证的是source-derived prebound代码连接，尚未实例化或执行真实producer。后续必须在新的合法bootstrap内、同一真实LIVE owner中闭合：

`expectation53 → context/check_context → adapter.hold(source, expectation.image) → 精确HeldInput/caller-image join → 强持G2/G3 → cleanup → parent quiet后reopen replay`。

先固定完整producer的runtime closure、实际global/module/class/default/dataclass方法边和生命周期设计；使用原ENTRY globals及同owner强持binding。被移除preparation的Source49 freshness、原code/default/module、EXE/P1/SCOPE与final source bookend须明确由runtime plan替代。现有consume_once已关闭runtime，不能用其摘要承担G2/G3 retention或从JSON重发能力；adapter.capture自建image也不能代替外部expected truth。保留固定literal数据验证根、projection raw SHA与独立能力image分开连接的既有两项高风险修复。

再写context、HeldInput、失败primary/secondary、sticky reject、exact-once close、父端独立采用及关闭后重开replay的具体代码和反例。不要将本轮CodeType测试计为真实53/P1读取或producer执行。expectation+G0为736次P1内容读，+一次full bookend为1419，原G0/G2/G3为2102；Source49、fixture、外部case、runtime/replay自带bookends另计。任何真实P1/角色/native校准/模型/solver/长实验继续遵守既有明确授权与agent.md §7–9；先形成可审实现、全路径调用量与wall/RAM/storage准入。

[NFC12同LIVE owner消费交接](continuation_handoff_20261028_saved_fresh_live_consumer_connected_v1.md)仍是最近真实binding消费证据，Source49 epoch `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`及其checkpoint `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`不变。**不重跑NFC11/NFC12/v1/v2/v3、不恢复旧PID**。所有producer/full-P1/full-runtime/role/permit/OwnedChild/Job/独立TCB/资源/科学/正式/run/F权限仍false或OPEN。

## 工作区与同步边界

接手时39项并行论文/插图/文献dirty（35 tracked、4 untracked）须保持原字节。本轮仅同步已审源码、scope、全部失败和成功结果及本交接。四共享导航如需发布新前置段，仅在Git index中构造“本轮前置段＋原HEAD正文”；不改写这39项工作区bytes。最终以Git remote读回hash、index为空、仍有原39项dirty且哈希相等为准；本轮自有范围clean不表示全局worktree clean。当前无研究任务运行，历史PID仅作冻结证据。
