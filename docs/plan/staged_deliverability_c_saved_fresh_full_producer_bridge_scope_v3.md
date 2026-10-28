# F：完整Module代码桥的重复编译优化

2026-10-28，DRAFT_NONAUTHORITATIVE。root唯一writer，bridge_pre_seal只读PRE_SEAL。承接[scope v2](staged_deliverability_c_saved_fresh_full_producer_bridge_scope_v2.md)，科学协议、Source49、P1、NFC12及已执行v1/v2字节全部冻结，完整F仍OPEN。

## 已观察失败与当前改动

v1首次register因孤立AST与完整模块CodeType不等拒绝，unit0；费用3.528502400004072s、40条不接受完整保留。v2完整Module上下文修复后，register accepted2.089993300003698s；唯一unit内部16/16通过、34帧、child rc0、capture_error=null、runner3.087s、原流/HANDLE/pipes/readers终态，但外层10.225993700005347s超过10s阶段帽，仍为rejected，未进入PRE_SEAL/saved。checkpoint仅封存拒绝元数据，1.2994751000078395s。v2 package13.615462100016885s、root4文件642251B，checkpoint SHA `2f3b0532882f8050bdf2e3f236f0a9cb61b3250710c602d1da7e4e64c571b843`。

累计static536.7907461000098、pytest366.48897970000326、unittest202.85693240000182，总1106.1366582000148s；不接受41条record。v1/v2原预算和未用余量各留原包，不退款、不重置、不转用；内部测试通过不能改写v2外层拒绝。

本轮保持10s unit阶段帽和全部校验，仅删除等价重复工作：完整raw Module编译直接作为original权威；transform已证明inverse函数AST逐属性等于原函数，module_code只替换唯一node identity，其余body/type_ignores同对象，因此原AST Module与inverse AST Module结构相同。独立inverse完整Module仍编译，并要求整体CodeType等于raw完整Module；derived完整Module及非目标顶层/嵌套code仍逐字比较。无需再重复编译与inverse相同的original AST Module。每成功derive完整Module编译4→3，未忽略opcode、未放松binding arg/cell、bookends freevars/代码、signature、source RHS、Store/Del及失败bookend。

hostile-AST测试只读取/parse一次冻结模板，每个既有12反例deepcopy后独立变异；每个变体仍完整transform验证。child测试前后各full check原Source49，模板优化不提供runtime缓存或能力；原read/parse12次降至1次。其他测试与目标代码保持原语义。导入上下文小夹具仍独立raw/AST compile两次。

## 精确继承与失败协议

固定v2 checkpoint及其完整root4，再调用已pin冻结v2.previous，重建全部v1/NFC12/Source49继承1187和archive158。当前connected_inputs与该冻结v2实际调用的函数CodeType仅规范化filename/firstlineno后相等，仍核NFC12 inherited1157 canonical pin、direct360、metadata effective1167及union1167。合并v2 own7（两项重叠）和root4（driver已在own）得1195，再加v3 own7减重叠2，最终精确1200。登记与check不可使用动态删减集合。archive旧158+v2 root4=162项15020446B，原路径、resolve路径和dict后count/pins/bytes/set均唯一且精确。

阶段仍register → unittest → pre_seal → saved → checkpoint，仅完整accepted前缀可执行payload。拒绝后仅metadata checkpoint封存；不得延帽、重试或将旧内部通过改为整包接受。previous/replay/canonical异常均保存真实charge/raw/known pins；非canonical可解析charge与不接受record名保留，但累计incomplete/null；不可解析/duplicate key/无效charge明确未知。历史41按record数续计。

## 独立有界预算与验证DAG

本轮独立static25s、unit15s、总40s，register5/unit10/PRE_SEAL5/saved5/checkpoint5，规划上限30s，static5/unit5仅本包失败保存；不借用旧余量。unit仍唯一16项（4构造器+12控制器）、34帧。child上限8s、stdout128KiB/stderr32KiB、256MiB/process、512MiB/pair、10ms/4096采样；parent前后检查全部计unit10s真实费用。未实测收益不宣称达标，超帽原样封存。

正常DAG：register previous1/builder1 → unit parent前后与child前后共previous4/builder4、测试另4 derive，合计builder8 → PRE_SEAL previous2/builder2 → saved previous2/builder2、完整原流/memory guard重开 → checkpoint previous1/builder1、saved canonical比较及独立accounting/pins。全包previous10/builder14；12成功derive×3=36次Source49完整Module compile，相比v2减少12次；另小夹具2次compile。两个bad derive先核49-source再在pin检查拒绝，显式source读取仍14×49=686；ENTRY/AST读取和previous旧链重读另计。不同阶段/进程的完整freshness读不省略。previous新增一层pin冻结v2.previous及其own/root验证，不执行旧unit或NFC12。

Root `results/tables/staged_rts24_saved_fresh_full_producer_bridge_v3_non_authoritative`最多10文件/4MiB，每record≤1MiB，并预留checkpoint1MiB。所有失败、原流、exit与输入字节create-only保留。新增模拟跨度0h；不运行Source49目标模块、P1、actual owner、模型、solver/native校准或长实验。helper/tests正常执行；采样内存观测不证明continuous/descendant/128MiB retention。producer/full-P1/full-runtime/role/permit/资源/科学/正式/run/F仍false或OPEN。完整同owner expectation→context→hold→HeldInput→G2/G3→cleanup、父端reopen replay与全流程准入仍需后续闭合。
