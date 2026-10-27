# 优化helper的有限512/自然返回观察窗口

2026-10-28，DRAFT_NONAUTHORITATIVE。起点`4dc626abb4e3197e5b5020289fa546e6b809370d`，承接[cache方法与full超时交接](continuation_handoff_20261028_saved_fresh_cache_parts_full_timeout_v1.md)。上一goal turn为progress：cache等价与方法门槛通过、真实full仍timeout，全部已冻结发布。现场只有语言服务器Python，无相关运行。root唯一writer，既有reviewer只读PRE_SEAL，非official、不seal、不授予运行权限。

问题是优化后真实import的256之后计数与成本未知。独立`bootstrap_import_census512_parts_v1.py`从census256派生：_check_cache完整AST取已验证cache_parts_full_v1；五个census函数body仅做limit512、私有schema v3、进度1/64/128/192/256/320/384/448及before512/complete512消息变换；_census_finish另在原active终止分支从held boundary刷新machinery stage，连接自然返回时最后状态。其余完整AST、全部header、identity/defaults/ownership/image pin、source checks保持，无跨event缓存、FS resolve、watchdog或新trace/profile。

唯一观察窗口在两者先发生时终止：第512次guard-passed观察（该次physical open之前，最多511次窗口内physical open），或importer在512前自然返回（wrapper仍主动抛出诊断stop，尚不执行M/D认证和adapter root采用）。自然返回必须有adapter_import_returned stage、完整schedule与terminal frame、真实child异常/资源关闭证据；两种mode的primary/secondary都按冻结消息机械oracle验证，不能将自然返回称完整B_S或OBSERVED。import error、partial、timeout、错误计数/阶段、缺report或关闭未知均不接受。

私有census v3保持原字段集，limit512、≤12帧、每帧≤2048B/共24576B；全部计数exact int、clock有限单调、进度完整、九bucket count等于passed、固定start、cache_new=items-begin且begin新增0、machinery非降并与child report相等。prefix mode固定passed0,1,64,...448,512；return mode按实际K<512采用0、所有≤K的进度、terminal K（允许terminal与最后进度同计数）。只有选定open计时，不补称全部事件/全部外部加载的覆盖。

完整DAG：前驱root/ledger/输入831回读→size≤2→register/60本地module inventory≤2→8项unit≤6→PRE_SEAL≤2→startup≤3→profile≤2→唯一512/return诊断≤8→saved≤2→checkpoint≤1。static≤22、unit≤6、总≤28s，互不借用；最多1个unit child+2个串行cold child。8s保持；真实optimized窗口成本未知，旧256仅提供阶段/收尾依据，不以方法0.199比例或512/256外推保证wall。超限保存partial/raw并停止，不重试、不延长。

core27/probe24由core24/probe21只迁移aoc_v9→pfc_v1两处/一处；v1 child envelope保留。parent24以parent21为基线，只允许四路径（helper path+pin2次）和显式census/mode validators变化，纯source transform绑定size/registration，不能以自选当前pin代替允许变换。8项unit覆盖：允许AST/header与已验cache方法相等；held roots/零全局census函数与metadata变异；exact512与511 physical；0/1/63/64/256/511自然返回及finish phase刷新；clock/IO/primary保全；schema/counter/bucket/start/cache/phase/partial反例；两mode的child与父端接受矩阵；有限输出/重复终止故障，fake selected-open总量≤4096。所有unit均为合成开发验证，复用原10项cache与full协议证据，不把它们重复计为本轮实际测试。

root `results/tables/staged_rts24_saved_fresh_pfc_v1_non_authoritative`≤30文件/4MiB；command≤30000 UTF16、decoded≤131072、stdout131072/stderr32768，unit stdout65536/stderr16384；startup profile writer/size/register/admission统一131072B，receipt1MiB。每phase预留exit16KiB/checkpoint64KiB，线程1，父端固定drain deadline/kill与完整关闭，保留原drain reason；RSS仅direct child peak，失败unknown，不构成完整RAM/资源准入。

Source49 epoch仍acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875，49份raw与全部失败/快照保留。60本地module exact source/call inventory复用；本地显式模型/Highs/solver调用0，external package/native与live Path descriptor均未认证。不启动模型实验、P1 hold/capture/replay、真实role/OwnedChild/Job/F或长/native运行。E/U、独立TCB/native、完整runtime/P1/role/permit/F/science/resource/formal/run authority均false。

全账static297.2437945000304、pytest366.48897970000326、unittest76.99093709999943，总740.7237113000331s、不接受30条续记，旧费用不退款、旧scope余量不重置。编辑/审查/Git、Python初始启动和最终记录写入沿前驱口径不计capture，非总wall、无模拟小时推进。完整F目标保持。
