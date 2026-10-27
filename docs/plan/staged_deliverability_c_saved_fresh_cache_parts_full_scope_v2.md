# Cache词法校验等价优化与一次完整B_S导入诊断

本文件为独立ful_v3后继。ful_v2首次size在parent helper路径needle计数处拒绝：同一行的path与pin读取各引用一次，共2次，原清单误写1次。原size_failure与rejection checkpoint冻结，static0.8620716000004904s全计，不接受28→29，unit/cold均0。8份当时输入的raw/pin在失败后、后继编辑前保存于`staged_rts24_saved_fresh_ful_v2_inputs_non_authoritative/inputs_snapshot.json`，明确不是prerun绑定。新parent迁移只把这一个needle的允许计数设为2，完整raw/AST相等仍强制，其余路径按当前独立版本号机械迁移。

本后继size/register各收紧为1.5s（前驱实测1.10/1.10s），static21、unit6、合计27s；连同本包ful_v2失败0.8620716s，最坏27.8620716≤原28s，8s完整import帽不变。归档失败root4文件与输入snapshot1文件共367070B；新root≤30文件、两者合计≤35文件/4MiB，writer每次预留时扣除此367070B，不借删除旧失败释放空间。

2026-10-28，DRAFT_NONAUTHORITATIVE。起点`d725b1c6b2ca2a81fa15c3b263157d0e55bfcf97`，承接[固定256交接](continuation_handoff_20261028_saved_fresh_prefix256_v1.md)。上一goal turn为progress：真实256前缀通过，cache占entry51.24%，已发布全量证据。先核Git与process：39项并行dirty保持，相关实验均终态。root唯一writer；既有只读reviewer作PRE_SEAL，无official verdict、production seal或运行权限。

本轮目标是降低每个event重复词法路径校验的成本并推进完整import。独立`bootstrap_import_cache_parts_full_v1.py`从full helper v1派生，**仅改变BootstrapImportBoundary._check_cache的body**；signature/header、其余完整AST、full-return wrapper、所有guard/identity/defaults/ownership/image pin/source checks保持。每次仍重读实际cache、逐个核全部predecessor identity及新增key/type/isabs、finder kind与finder.path；在同一调用内把两个root与每个key的Path.parts按当前Windows词法口径lower后比较前缀，代替反复构造ancestor。没有跨event状态、文件系统解析或省略检查。

条件信任边界是当前已pin Windows runtime及pathlib源码；不声称任意RAM/native/TCB行为。独立oracle采用原_check_cache与Path.relative_to，明确原有`.`/`..`、大小写、分隔符、盘符/UNC、相邻目录前缀、relative/rooted/drive-relative等口径与第一失败顺序；不把词法关系升级为实际filesystem alias证明。真实Source49 epoch仍为acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875，49份raw和所有旧失败/root不变。

有限DAG：前驱账/bytes→size≤1.5→register/60本地module exact inventory≤1.5→10项unit与方法benchmark≤6→PRE_SEAL≤2→startup≤3→profile≤2→唯一完整import≤8→saved≤2→checkpoint≤1。static≤21、unit≤6、总≤27s，互不借用。最多1个unit child+2个串行cold child；unit或benchmark不接受即停止，不启动cold；完整import仍8s，到时保留raw并停止，不重试或延长。core26由core23迁移ful_v1→ful_v3两处，probe23由probe20同迁移一处，v2 envelope及runtime_preclose保留。

10项unit包括继承并绑定原full六项（首项改为cache-only AST/header/proof），新增四项：独立词法oracle和旧/新完整错误对照；每event mutation与predecessor/finder/failure-order回归；helper metadata变异、无跨event状态；有界三轮真实_check_cache方法对照。benchmark固定11个predecessor+37个new条目（取真实256计数规模）、每arm每轮32次、3轮，order old/new、new/old、old/new，共192个benchmark方法调用；128个词法case与其他unit中的旧/新方法调用合计另≤320，整个unit≤512次。预定总new/old与三轮中位数new/old均≤0.90才接受收益；逐次结果一致、前后map/identity保持，metrics与失败均保存。合成方法收益不替代真实完整import或整个F性能结论。

完整child不启用census，也不新增watchdog/sys.settrace/sys.setprofile；保留原guard hook、9个stage与graph。必须exit0/status completed、primary=None/secondary=[]、runtime_preclose OBSERVED、was_live=false、最终runtime/boundary/resource CLOSED、自HANDLE close[1,1]、父端全部资源终态；M/D observed/auth2、optional/blocked Popen1、NumPy SVE fallback确认、13个adapter函数roots、retention与Source书挡、固定完整schema/false gates均按原full矩阵检查。成功也只产生OBSERVED诊断profile，不授予LIVE或role。

root `results/tables/staged_rts24_saved_fresh_ful_v3_non_authoritative`≤30文件/4MiB；command≤30000 UTF16、decoded≤131072、stdout131072/stderr32768，unit stdout65536/stderr16384，startup profile writer/size/register/admission统一131072B，import profile≤1MiB，full receipt≤1.5MiB，method metrics≤65536B。预留exit16KiB/checkpoint64KiB与关闭预算；RSS用已验证ABI测direct child peak，失败unknown，不形成整链RAM上限。保留线程1、原固定drain与硬停止；parent保存drain reason原值。

库import只使用已pin的60个本地项目module exact source/call inventory；本地显式模型/Highs/solver调用0，外部package/native行为未认证。不启动模型实验、P1 hold/capture/replay、实际角色/OwnedChild/Job/F、long/native校准或外部下载。所有E/U、独立TCB/native、完整runtime/P1/role/permit/F/science/resource/formal/run authority保持false。

全账从static282.00589910002896、pytest366.48897970000326、unittest74.28716270000223，总722.7820415000344s、不接受29条续记。失败费用不退款，旧scope余量不重置；编辑/审查/Git、既定Python启动和最终记录写入沿前驱口径不计capture，非完整wall。实现、方法收益、真实完整import与整个F的完成状态分别据各自证据判断。
