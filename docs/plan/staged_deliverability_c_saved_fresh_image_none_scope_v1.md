# image 内 None identity 的有限方法候选

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[512窗口交接](continuation_handoff_20261028_saved_fresh_parts512_v1.md)，起点273f96bf16b99b4545962afe9253fe5f4bba958c。该窗口image_digest占entry59.11%，但tuple、id、JSON、SHA尚未分项归因。本候选检验重复id(None)分发是否值得减少，不能预称它解释完整import超时。root唯一writer；既有独立reviewer只读PRE_SEAL；不seal、不授予运行权限。

仅新helper的_image签名/body变化：以default _id=id持有原native；本次调用内惰性缓存None的identity，首次None仍在原位置调用native，所有非None每次仍调用同一个native；原image_pin、字段读取和tuple顺序保持。没有跨event缓存。新probe只在validate_import_helper为_image新增显式native-id defaults校验，当前仅作方法proof工具，不执行probe。返回值等价不代表完整observable/异常轨迹等价：第二次以后的id(None) audit事件及其第三方hook副作用被有意减少；未知第三方hook、mid-call builtins变化和任意RAM不认证，all_unselected_events_verified=false。

本轮只做方法验证。真实_audit_entry当前只核identity，不核_image metadata；必须在后续真实接入前单独闭合入口code/defaults/native-id proof。本候选即使方法通过也不直接接入cold，不迁移core/parent，不启动1024或完整import。Source49原49份raw与epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875保持。

复用原image fixture，12项unit：完整允许AST变换；全image/canonical/digest；bytes及fallback；全部依赖变异；原异常；pin dict独立；pin顺序及per-call lifetime；held proof/metadata/classifier/finder；固定成本；native-id调用序列与字段getter顺序；default替换拒绝；首个None/非None异常primary及后续None事件减少。原9项中方法07改为两个已经pin去重的实现调用序列相等，方法09采用下述新预注册成本并覆盖独立metrics validator的20个反例，其他oracle复用。native调用序列必须恰为旧序列删除首个以后的None项。saved/checkpoint独立重算固定轮序、48/20调用量、有限时间、事件差额、三比例/阈值及hook/false门禁，不只信任测试的布尔位。

只允许一个fresh unit child内安装一个可deactivate gate的native sys.addaudithook。gate默认及退出时关闭，hook不可卸载、随child退出；trace/fault只看builtins.id，benchmark只将该事件分发到真实B_S _audit的nonselected早返分支（synthetic active state、真实固定event_sets、无owner/kernel）。三轮old/new、new/old、old/new，每variant每轮48次image+digest；另两variant各20次gate惰化调用，此时hook仍安装但不分发。仅解释这个固定synthetic dispatch环境。预设收益门槛：有分发总new/old和中位new/old均≤0.95，gate惰化总new/old≤1.20。任一失败即保存metrics和失败，不重试、不启动cold。

DAG：前驱checkpoint/root/input/Source49回读→register≤2s→12项unit≤6s→PRE_SEAL记录校验≤2s→saved元数据≤2s→checkpoint≤2s。static≤8、unit≤6、总≤14s；不互借、不退款、不重置历史余量。register或任一phase失败立即停止后续，仅做拒绝checkpoint。authorial编辑/审查/Git、Python初始启动与最终记录写入沿前驱口径不计capture，非总wall。root results/tables/staged_rts24_saved_fresh_image_none_v1_non_authoritative ≤20文件/2MiB；单文件caps：registration524288、snapshots524288、metrics65536、unit stdout65536/stderr16384、exit131072；写前预留checkpoint131072。capture沿原有bounded drain/kill/close，线程1，最多1个unit child、0 cold/adapter/model/solver/role/Job。

累计从static310.80556120004917、pytest366.48897970000326、unittest80.17350020000231、总757.4680411000547s、不接受30条续记，全部旧失败/快照与39项并行dirty保留。E/U、独立TCB/native、完整runtime/P1/role/permit/F/science/resource/formal/run authority均false；宽goal active，F未完成。
