# B_S import固定256前缀：有界性能定位

执行前复核补充：startup profile的writer、size记录、register核验和profile admission统一131072B；partial/early-return/无child-report/非空drain reason均显式拒绝。完整prefix逐帧要求九个bucket计数等于passed、start_clock同begin、cache_new等于cache_items减begin值且begin新增0；final machinery_stage须与child report一致。六节点内补齐这些漂移反例和observed0/1/2、auth0的pending正反例。

2026-10-28，DRAFT_NONAUTHORITATIVE。起点`d59889136b28103d84f6fc46ecc0148bce211191`，承接[完整导入失败交接](continuation_handoff_20261028_saved_fresh_full_import_timeout_v1.md)。上一轮是progress：保存了首次完整导入未返回、父端收尾与RSS证据。当前没有相关运行。root唯一writer，按agent.md第7节使用既有只读reviewer作PRE_SEAL，不生成official verdict、production seal或运行权限。

本轮问题：在相同8s阶段帽内，取得原64之后的真实guard分段耗时、cache增长、计数和失败关闭证据。现有full日志只有调用前stage，不能定位具体函数。保留所有旧root与失败bytes；独立AOC9 successor不重跑full CLI，也不顺延其预算。

实现边界：从image-pin census64 helper派生`bootstrap_import_census256_v1.py`；只改五个函数的body：emit将私有census schema升v2且limit256，observer/open_begin限256，open_end进度为1/32/64/96/128/160/192/224，diagnostic wrapper更新before256与stop消息。其余完整AST及这五个FunctionDef header必须相等，guard本体、checks、缓存策略、image pin与身份/defaults不改。第256次guard-passed观察后、physical open前主动停止；最多255个该窗口内的实际open。原clock/observer/IO/异常传播与held defaults保留，不加入watchdog/profile/trace。

core24由core22迁移aoc_v8→aoc_v9两处；probe21由probe19同迁移一处，原v1 child envelope保持。parent21采用新census v2计数/完整schedule并保留exact v1 envelope、guard/boundary keyset和全部false字段；真实报告必须failed/AuditCensusStop、runtime UNRESOLVED/boundary FAULTED/resource CLOSED、自HANDLE各close1、父端资源关闭、无census诊断错误、没有import返回。parent保存direct child RSS与drain reason原值，失败原始流始终保留。

完整DAG：前驱账/hash与Source49→size≤2→register/静态本地import inventory≤2→6项unit≤5→PRE_SEAL≤2→startup≤3→profile≤2→唯一prefix256≤8→saved≤2→checkpoint≤1。static≤22、unit≤5、总≤27s，互不借用；最多1个unit child+2个串行cold child。固定64曾在AOC8中0.1472941s窗口内通过，256需4倍selected event；cache/外部包/模块加载使真实成本非线性，故不以4倍外推为性能保证，8s到时保留partial/raw与metadata并停止，不重试。保留exit/checkpoint槽与关闭预留，编辑/审查/Git/既定Python启动/最终记录写入沿前驱口径不计capture。

复用已pin的60个本地模块1097959B import-time inventory，未知source/call/alias/computed变化拒绝；只证明本地显式模型/Highs/solver调用为0，external package/native行为未知，不授予科学/native权限。Source49 epoch继续acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875，原49份raw保持。没有模型实验、P1读取/hold/capture/replay、实际role/OwnedChild/Job/F或长运行。

6项unit覆盖：五body-only AST及held defaults；exact256、只发生255次physical open与10帧schedule；7→31→255等early-return边界及完整schedule；clock/IO失败和primary/cause保全；严格计数/schema/partial/未知字段拒绝；真实guard拒绝路径、RSS已知/unknown与权限字段漂移。合成方法测试不能替代真实prefix，更不能证明完整import。成功saved/checkpoint必须再次重放实际raw及exact256矩阵；partial、timeout、超帽、清理失败均拒绝。

root `results/tables/staged_rts24_saved_fresh_aoc_v9_non_authoritative`≤30文件/4MiB；census≤12帧、每帧2048B/共24576B；stdout131072/stderr32768，unit stdout65536/stderr16384，command30000 UTF16，decoded131072，startup profile131072，receipt1MiB。RSS沿已验证capture ABI测direct child peak，成功为非负int/error=None，失败为peak=None/有界error；不是整链RAM上限或资源准入。保留OMP/MKL/OpenBLAS线程1与8s硬终止，RSS不形成新运行门禁。

从全账static268.0192162000051、pytest366.48897970000326、unittest71.44163690000642，总705.9498328000147s、不接受28条续记。历史失败不退款，未用scope额度不重置总账。所有E/U、TCB/native、完整runtime/P1/role/permit/F/science/resource/formal/run authority保持false；完整F目标不缩减为prefix。
