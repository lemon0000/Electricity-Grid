# F：同owner retained producer生命周期开发合同

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[代码桥v3终态](continuation_handoff_20261028_saved_fresh_full_producer_bridge_completion_v3.md)。root唯一writer，bridge_pre_seal只读PRE_SEAL；本合同拟实现完整producer操作顺序和持有状态，不改变Source49、NFC12及已执行v1–v3字节，不授予P1/actual owner/角色/科学/资源/正式/F权限。

## 必须实现的路径

同一LIVE owner的原consumer plan/binding → 固定v3 prebound capture CodeType配原ENTRY globals → SavedCallerExpectation → context_from_saved_expectation及check_expectation_context → 原adapter.hold(source, expectation.image) → 精确HeldInput/caller-image/完整raw map join → 同一对象强持G2、G3 → 清理并关闭。不得使用capture自建image替代外部expected truth，不调用_probe接口，不重新_expectation_adapter，不使用会立即close的consume_once。

本合同当前仍为未登记的整体开发草稿。先实现其[跨项目图依赖组件](staged_deliverability_c_saved_fresh_producer_project_graph_scope_v1.md)，该组件unit不视为本合同producer/lifecycle测试或执行。完整生命周期代码与下述bootstrap接线尚未完成。

新增helper仅固定调度以上原函数，不接收任意callback。实际bootstrap需注入精确runtime类型和独立持有的本包P1操作token；缺少时拒绝调用。当前仍没有该bootstrap/许可接线，普通unit不发行此token给真实owner。新增项目依赖闭包须包含ENTRY expectation/context/helper/class、adapter HeldInput及dataclass方法、core/codec/mechanical/point跨模块边与固定constants；旧十binding或adapter单图不能称为完整producer闭包。全37项目模块图的初始来源、unsupported节点和原40次图调用帽的后继资源准入继续单列，不能靠单次snapshot自证最初正确性或绕过旧帽。

## 生命周期及失败不变量

状态严格为PREPARED → RUNNING → HELD → G2 → G3 → CLOSED；异常固定FAILED/UNRESOLVED。expectation、context、HeldInput、binding和runtime同对象在HELD/G2/G3之间强持，不经JSON重建或跨进程转移。操作前先置busy状态；重入、重复、乱序和失败后调用都拒绝。每阶段仍核owner entry/source、固定函数code/default/globals、expectation和context、HeldInput image/caller-image及全部raw pins。full hold为G0一次683内容读，G2/G3各一次683内容读；三个阶段不互相替代。

PREPARED提交时须排他占用原owner._consume_state：以原runtime_seal语义从PREPARED置RUNNING并重封，阻止第二consumer；不能只持owner引用。成功G3后置CONSUMED，失败置FAILED，再唯一close。若不复用该slot，必须独立Core successor实现producer lease，不原位修改Core39。尚无该issuer/slot实现。

capture/context/hold/验证失败均保留primary原对象；各独立final checks与close错误逐项存secondary原对象。任一失败sticky，不能返回成功或退用53-read projection。即使初始化只完成一部分也关闭owned runtime；close尝试exactly once、重复close只重抛原failure，不重试资源释放。保留source/rawimage分离的数据协议，gate字段全false。

只有成功G3且final graph/source/context bookend与runtime/resource/boundary关闭确定成功才可CLOSED；提前abort须FAILED，任何bookend/cleanup/terminal不确定为UNRESOLVED。首次failure wrapper后续逐次重抛同对象。成功关闭后释放live owner/binding/HeldInput/rawmap能力，仅保留有界数据证据；UNRESOLVED可取证但不可序列化或重试。

## 本轮验证和预算

普通unit仅用system tmp和逻辑runtime、固定named函数夹具；测试真实生命周期调度、强引用identity、有序G2/G3、完整raw/image/content反例、每一partial stage错误、post-bookend+close并发错误及重复/重入。固定source/CodeType绑定另用compile-only oracle验证，不import/exec Source49目标模块，不读真实P1，不启动真实native owner或solver。

原context_from_saved_expectation即使使用pytest输出也会读source/EXE/INHERITED/P1 anchor；因此实际ENTRY globals路径在普通unit中只核identity/静态code，不调用。逻辑数据链须在独立synthetic globals中运行AST-extracted代码，并以拒绝型P1 reader计数。snapshot初始来源认证须独立source/module/class/default oracle，当前依赖组件的continuity snapshot永不代替该oracle。

本包拟定static25s/unit15s/总40s，register5、唯一unit10、PRE_SEAL5、saved5、checkpoint5，其余static5/unit5只用于同包失败保全；旧scope余量不转用。执行前必须固定实际节点清单与完整controller DAG、独立PRE_SEAL，再登记冻结字节。unit child≤8s、stdout128KiB/stderr32KiB、256MiB/process、512MiB/pair sampled停止帽；root≤10文件/4MiB、record≤1MiB且预留checkpoint1MiB。当前继承累计1144.4288945000255s、不接受41条，本lifecycle包尚未登记、自身费用0；graph独立包18.72246200000518s已固定、不退款或转用。下一包账源必须为graph checkpoint SHA 7fd488b14a7c1e4a8171bebb37b81944a9c95f026116f16e2a79c5fee344a6b2。所有失败原样保留，模拟跨度新增0h。

本轮完成不表示完整producer已在真实LIVE owner上运行。后续仍须bootstrap issuer/完整初始closure oracle、37-module图预算与新图帽接线、真实P1读取许可、父端quiet后reopen replay及全workflow wall/RAM/storage准入。目标仍为完整F，不以本轮逻辑测试替代任何开放门槛。
