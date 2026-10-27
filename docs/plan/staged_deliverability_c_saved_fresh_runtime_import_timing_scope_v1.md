# actual adapter import：阶段时标与定点stack诊断

2026-10-27，DRAFT_NONAUTHORITATIVE，起点178aec30cb58ea6a3e41f626257c51c073cae7e0。root唯一writer、独立只读PRE_SEAL；冻结所有前驱源码/结果。复用NGT实测pre-import父端1.7768287s、16图包装0.5314062s及完整self-close见证，不采用真实SHA次数未减少的NSv3。

新增core12、parent/probe9和BS import timing v1，namespace timing1原bytes复用。BS所有原class与非loader top-level函数AST不改；loader仅插入阶段事件并将原import调用交给单次诊断函数。后者的importer、faulthandler arm/cancel、BaseException/ExceptionGroup均default强持并由bootstrap validator核验；trace仅借runtime namespace graph-plan中已绑定clock/write/flush/dumps。完整helper proof绑定新增faulthandler module keyset/成员。所有原policy/Source49/manifest schema/清理/角色门禁不放宽。

完整路径：登记 → 4项逻辑unit（原AST/loader单次结构、trace、成功与import/cancel/trace failure顺序、mixed stderr parser与validator）→ PRE_SEAL → 独立startup discovery/profile → 唯一actual import child → metadata保存。Loader阶段覆盖ready、import前后、machinery auth、adapter直接图前后、boundary close前后。只有真正import前启动一次2s native watchdog，repeat=False，同一finally取消，无重试；已有import primary不得被cancel/trace错误替代，secondary保存在cause/group。Watchdog为显式条件性CPython native观察叶，可能绕过Python audit写stderr，不由零process/thread/write计数推成“无额外native效果”。

每个cold child最多2次ENTRY exec，只有第二child最多1次adapter import；并发1。import包括既有NumPy/SciPy/Pyomo/PYPOWER/Highspy extension依赖，不构造模型/Highs()/solver，不调用hold/capture/replay/P1/OwnedChild/Job/F。2s采样从import开始计算，避免再次只采到前置图；单样本不证明整个8秒或旧9秒耗时归因。

stage间隔含写帧/flush和对应步骤，不是纯CPU。Parent保留完整raw stderr，只解析完整且形状/阶段白名单/finite float正确的JSON行；其余行单独保留及pin，包括可能交错行，不补造缺失stage。Timeout/部分trace只支持诊断partial，不能称adapter完成、closed profile、self-close或cold验收。若完整child报告则保留原flags与核kernel PID/creation/image/command line。

static≤18s、unittest≤4s、总≤22s；登记≤2s、unit≤4s、PRE_SEAL≤1s、startup≤3s、profile≤1s、actual import≤8s、saved≤2s，留static1s失败余量。最多2个cold child与1个unit capture child；单例/阶段超帽保存并停，不延长原10s帽或重试同一child。root results/tables/staged_rts24_saved_fresh_rti_v1_non_authoritative ≤24文件/4MiB，command30000UTF16、payload131072、stdout131072/stderr32768、raw import profile1MiB、module/cache各4096维持。RAM只观察。

前驱累计static193.94871670001817、pytest366.48897970000326、unittest50.181212600000435、总610.6189090000219s，不接受21条；全部失败、旧120/540/import8MiB超帽保持。Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875及原49字节不变。新独立帽不是全累计帽，编辑/审查/Git、Python初始启动和最终exit序列化不计capture，无模拟小时推进。

E/U、独立TCB/native/完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false。完整B_S import/admission及后续故障矩阵仍须独立证据；本次只形成有限诊断，不授予后续运行权限。保留39项并行dirty，发布只含本scope及导航新段。
