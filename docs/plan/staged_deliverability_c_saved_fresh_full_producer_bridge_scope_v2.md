# F：完整模块上下文中的prebound producer代码桥

2026-10-28，DRAFT_NONAUTHORITATIVE。root唯一writer，bridge_pre_seal只读独立PRE_SEAL。完整producer、父端采用与F仍OPEN；本轮仅标准库源读取、AST/CodeType编译与普通unit，不执行Source49目标模块、P1、actual owner/native校准、模型/solver或长实验。

## 固定前驱与本轮修复

[scope v1](staged_deliverability_c_saved_fresh_full_producer_bridge_scope_v1.md)首次register因`ValueError:full-module original CodeType differs`拒绝，unit未启动。原3文件28030B及全部执行source/scope/test bytes冻结。checkpoint SHA `2131ddcdadfab0ecc6bd0286bbd450555a8b4934694fd37d952ac0dc325bc4b2`，accepted=true、diagnostic=false、accounting_complete=true；register2.254955600001267s + checkpoint1.273546800002805s = static3.528502400004072s，unit0。不接受39+1=40条record。累计static533.4012776999982、pytest366.48897970000326、unittest192.63093869999648，总1092.521196099998s。原40s预算余量留在v1，不退款、不重置、不转用。

compile-only取证显示，同一原函数在孤立FunctionDef与完整冻结Module中的`json.loads`、`os.getpid`等调用产生不同LOAD_GLOBAL/LOAD_ATTR调用编码。本轮在完整冻结Module AST上下文中唯一替换目标函数，再提取目标CodeType；不执行module。原模块AST与raw编译、inverse完整module与raw编译必须完全相等；derived的其余顶层及嵌套code仅规范化显式derived filename后完全相等。不得忽略opcode、降低CodeType检查或修改Source49。

目标变换仍仅新增显式binding参数、移除唯一`binding = _expectation_adapter(source)`、改显式derived函数名。原函数/完整模块根、signature、source前置RHS、binding Store/Del、cell顺序、bookends freevars/完整代码、其余AST位置与inverse均保持原验收。新增导入上下文回归夹具只compile不exec。原ENTRY globals、同LIVE prepared binding及被移除preparation的Source49/原code/default/module/EXE/P1/SCOPE/final bookend替代仍须后续runtime plan闭合；此桥本身不产生capability。

## 精确输入、费用与失败协议

NFC12继承1157项canonical map pin、direct360项、effective_input_count=1167及union1167逐项核定；加入NFC12 root后1180。再合并v1已冻结own7（两项重叠）及其root3（driver已重叠），successor inherited1187。当前own7中sampled capture/memory两项已继承，最终精确1192；登记和check均重建集合，删项/换项/动态计数伪装必须拒绝。archive为历史155+v1 root3=158项14378195B；原路径、resolve后路径和dict cardinality唯一，与冻结map精确相等。

严格register → unittest → pre_seal → saved → checkpoint，每次仅accepted完整前缀进入payload。拒绝后只能封存连续失败前缀；终态及重复调用create-only。checkpoint previous/replay/canonical失败仍独立保存真实charge、raw/known pins及错误。可安全解析非canonical record的charge和不接受record名保留，同时accounting incomplete、累计null；不可解析/重复键/无效charge仅保存raw pin并明确未知。历史按record数续计40，不按package重写。

## 有界验证DAG与独立预算

本轮独立预算static25s、unit15s、总40s；register5、唯一unit10、PRE_SEAL5、saved5、checkpoint5，规划上限30s，其余static5/unit5仅本包失败封存。该预算不从v1或其他旧scope余量取得。仅普通unit与静态验证，新增模拟跨度0h。

16项unit为4项构造器（含完整模块导入上下文回归）+12项临时目录控制器故障测试，共34帧。控制器覆盖重复/别名、等尺寸换项、完整输入集合和前驱metadata计数、严格阶段阻断、previous/replay/canonical异常、非canonical成功/失败、不可解析/重复键、缺失历史账、未完成前缀、失败元数据及checkpoint自身超帽。故障测试使用system tmp、固定mock，不调用真实capture/P1/native child。

正常DAG：register previous1/builder1 → unit parent前后各check1、child前后各check1、原测试4次current/derive，共previous4/builder8 → PRE_SEAL前后check共previous2/builder2 → saved前后check共previous2/builder2并重开原流/memory guard → checkpoint check内previous1/builder1、saved canonical比较及独立accounting/pins。正常共previous10、builder14；各builder读49-source，显式共686次，ENTRY/AST直接读和previous旧链重读另计。新成功derive各编译原AST、inverse AST、完整raw、derived AST四个完整Module；外部bad bytes在pin检查后拒绝，不进入编译。Source49完整Module编译共12次成功derive×4=48次，另有导入上下文小夹具2次compile；两个bad derive保留49-source freshness读。不同阶段及parent/child前后全量freshness保留，不缓存跳过。

previous完整校验原冻结driver链、约56MB原前驱集合、v1 own7及root3，并核158项archive；不重跑NFC12、48项旧unit或旧失败registration。首次v1 previous/register观测约1.27/2.25s仅作同机器参考；v2增加完整Module编译和少量输入，10s unit能否通过由唯一终态决定，不承诺未测收益。child仍8s sampled capture、stdout128KiB/stderr32KiB、256MiB/process与512MiB/pair、10ms/4096采样停止帽；parent前后check计同一unit10s实际费用。失败/超帽停止，不自动延长或重试。

Root `results/tables/staged_rts24_saved_fresh_full_producer_bridge_v2_non_authoritative`最多10文件/4MiB、每record1MiB，每次写入预留checkpoint1MiB。所有原流、exit、input pins与失败create-only保留；费用不包含工程编辑、只读审查和Git全部wall。普通测试的采样停止帽不证明continuous/descendant/128MiB retention。所有producer/full-P1/full-runtime/role/permit/资源/科学/正式/run/F flags仍false；完整producer的expectation→context→hold→HeldInput→G2/G3→cleanup与父端reopen replay及全流程性能准入另行闭合。
