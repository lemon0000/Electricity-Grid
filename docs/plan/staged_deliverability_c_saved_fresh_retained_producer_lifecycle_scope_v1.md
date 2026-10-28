# F：同owner retained producer生命周期开发合同

2026-10-29，DRAFT_NONAUTHORITATIVE。承接[project graph终态](continuation_handoff_20261028_saved_fresh_producer_project_graph_v1.md)。root唯一writer，retained_lifecycle_review只读PRE_SEAL；本合同实现producer操作顺序和逻辑持有状态，不改变Source49、NFC12及已执行v1–v3和graph字节，不授予P1/actual owner/角色/科学/资源/正式/F权限。

## 必须实现的路径

同一LIVE owner的原consumer plan/binding → 固定v3 prebound capture CodeType配原ENTRY globals → SavedCallerExpectation → context_from_saved_expectation及check_expectation_context → 原adapter.hold(source, expectation.image) → 精确HeldInput/caller-image/完整raw map join → 同一对象强持G2、G3 → 清理并关闭。不得使用capture自建image替代外部expected truth，不调用_probe接口，不重新_expectation_adapter，不使用会立即close的consume_once。

本合同当前仍为未登记草稿。[跨项目图依赖组件](staged_deliverability_c_saved_fresh_producer_project_graph_scope_v1.md)已有独立检查点，该组件unit不视为本合同producer/lifecycle测试或执行。[生命周期实现](../../experiments/staged_rts24_saved_fresh_retained_producer_v1.py)、[31项普通合成测试](../../tests/test_staged_rts24_saved_fresh_retained_producer_v1.py)及[controller](../../results/tables/staged_rts24_saved_fresh_retained_producer_v1_non_authoritative/driver.py)已准备，下述真实bootstrap接线仍未完成。

新增helper仅固定调度以上原函数，不接收任意callback。实际bootstrap需注入精确runtime类型和独立持有的本包P1操作token；缺少时拒绝调用。当前仍没有该bootstrap/许可接线，普通unit不发行此token给真实owner。新增项目依赖闭包须包含ENTRY expectation/context/helper/class、adapter HeldInput及dataclass方法、core/codec/mechanical/point跨模块边与固定constants；旧十binding或adapter单图不能称为完整producer闭包。全37项目模块图的初始来源、unsupported节点和原40次图调用帽的后继资源准入继续单列，不能靠单次snapshot自证最初正确性或绕过旧帽。

## 生命周期及失败不变量

状态严格为PREPARED → RUNNING → HELD → G2 → G3 → CLOSED；异常固定FAILED/UNRESOLVED。expectation、context、HeldInput、binding和runtime同对象在HELD/G2/G3之间强持，不经JSON重建或跨进程转移。操作前先置busy状态；重入、重复、乱序和失败后调用都拒绝。每阶段仍核owner entry/source、固定函数code/default/globals、expectation和context、HeldInput image/caller-image及全部raw pins。full hold为G0一次683内容读，G2/G3各一次683内容读；三个阶段不互相替代。

PREPARED提交时排他占用原owner._consume_state：以原runtime_seal语义从PREPARED置RUNNING并重封，阻止第二consumer；成功G3后置CONSUMED，失败置FAILED，再唯一close。当前新增helper复用该slot，尚无真实issuer，不原位修改Core39。

唯一可信调度形式为bootstrap预先持有的(CodeType, isolated globals, state)，逐次重建原dispatch函数。公开producer方法不充当该入口。source_dispatch在回调前按完整source编译核helper与graph全部source-owned函数/类方法、常量、direct imported attributes和实际builtin targets；helper及graph顶层函数提前复制到private globals，检测公开绑定漂移后仍以private roots收尾。此机制只覆盖调用前、阶段bookend和终态可检测漂移，不宣称防御任意两个Python bytecode间篡改整个解释器的敌对代码。

capture/context/hold/验证失败均保留primary原对象；各独立final checks与close错误逐项存secondary原对象。任一失败sticky，不能返回成功或退用53-read projection。即使初始化只完成一部分也关闭owned runtime；close尝试exactly once、重复close只重抛原failure，不重试资源释放。保留source/rawimage分离的数据协议，gate字段全false。

只有成功G3且final graph/source/context bookend与runtime/resource/boundary关闭确定成功才可CLOSED；提前abort须FAILED，任何bookend/cleanup/terminal不确定为UNRESOLVED。failure在cleanup及operation_owner reset完成后一次性发布完整seal，之后逐次重抛同对象。foreign thread仅拒绝，不改状态或清理；同线程重入保留exact pending error，即使回调吞错也在阶段成功提交或close前拒绝。held operation lock通过finally释放。成功关闭后释放live owner/binding/HeldInput/rawmap能力，仅保留有界数据证据，报告返回独立数据副本；UNRESOLVED可取证但不可序列化或重试。

## 本轮验证和预算

普通unit仅用system tmp和逻辑runtime、固定named函数夹具；测试真实生命周期调度、强引用identity、有序G2/G3、完整raw/image/content反例、每一partial stage错误、post-bookend+close并发错误及重复/重入。固定source/CodeType绑定另用compile-only oracle验证，不import/exec Source49目标模块，不读真实P1，不启动真实native owner或solver。

原context_from_saved_expectation即使使用pytest输出也会读source/EXE/INHERITED/P1 anchor；因此实际ENTRY globals路径在普通unit中只核identity/静态code，不调用。逻辑链在独立synthetic globals内执行固定named函数夹具与实际生命周期程序；inventory为独立生成的683项/2950863B逻辑内容，读取49个原source文件只作hash/模块集合核对，不执行其目标模块。逻辑plan通过私有夹具建立，public prepare必须拒绝其函数，不能视为真实issuer。AST root oracle独立列举代码根；initial Source49 source/module/class/default oracle仍OPEN，continuity snapshot永不代替它。

完整受控DAG固定为register → 唯一31-node unittest → 只读PRE_SEAL保存 → saved canonical replay → checkpoint，失败立即停止后续正常阶段并保存checkpoint；不重跑同包unit。31项覆盖阶段顺序与强持同对象、capture exact CodeType、capture/context/hold局部失败、primary/final/close独立原错误、raw内容/集合与context join、吞错重入/foreign thread/terminal重入、helper/graph隐藏函数漂移、owner slot排他、sticky failure篡改拒绝、synthetic public prepare拒绝与独立AST/Source49 pins。

前驱完整继承为1214项，自有8项与其重叠4项，最终精确1218 inputs；archive174文件/16327041B。自有为program/test/scope/controller、v3 prebound构造器、冻结graph组件、sampled capture及memory drain。register/check每次重建前驱完整关系并核精确路径集合及pins，不以直接registration map替代继承。控制器复用冻结graph包的严格phase prefix、失败计费fallback和create-only规则，所有gate字段false。

本包拟定static25s/unit15s/总40s，register5、唯一unit10、PRE_SEAL5、saved5、checkpoint5，其余static5/unit5只用于同包失败保全；旧scope余量不转用。执行前必须固定实际节点清单与完整controller DAG、独立PRE_SEAL，再登记冻结字节。unit child≤8s、stdout128KiB/stderr32KiB、256MiB/process、512MiB/pair sampled停止帽；root≤10文件/4MiB、record≤1MiB且预留checkpoint1MiB。当前继承累计1144.4288945000255s、不接受41条，本lifecycle包尚未登记、自身费用0；graph独立包18.72246200000518s已固定、不退款或转用。下一包账源必须为graph checkpoint SHA 7fd488b14a7c1e4a8171bebb37b81944a9c95f026116f16e2a79c5fee344a6b2。所有失败原样保留，模拟跨度新增0h。

本轮完成不表示完整producer已在真实LIVE owner上运行。后续仍须bootstrap issuer/完整初始closure oracle、37-module图预算与新图帽接线、真实P1读取许可、父端quiet后reopen replay及全workflow wall/RAM/storage准入。目标仍为完整F，不以本轮逻辑测试替代任何开放门槛。

锁仅接受bootstrap预先登记的同一个exact builtin Lock，调用任何acquire前先核type/identity；foreign/fake lock拒绝不清理。exact lock在本dispatcher持有期间不允许外部直接release或破坏，其正常release为确定性实现边界。verifier由held CodeType和isolated globals逐次重建，不依赖动态guard callable。31项还包括guard替换、伪锁及三处terminal发布fault。terminal reset、failure seal及最终publish错误按label保留，bootstrap-held终态registry提供不可重试记录。

close在cleanup前保存retained data witness，cleanup后释放前重核expectation/完整HeldInput raw结构、原caller-image投影、context与source；此检查不调用owner.entry、不读取文件。callback改动数据须保留原引用并sticky UNRESOLVED。close的operation_owner reset在释放live refs和形成CLOSED前完成，其fault仍保留原owner/binding/expectation/HeldInput。runtime公开close绑定漂移时，清理仍调用bootstrap预持的原close CodeType。追加反例覆盖raw/expectation close mutation、close reset fault及runtime close绑定漂移。
