# F：固定权限核验、贯穿清理的只读guard与bootstrap接线

2026-10-29，DRAFT_NONAUTHORITATIVE，登记前自身费用0。完整目标仍为真实外部授权issuer → 同LIVE owner完整producer → parent quiet/reopen采用及whole-workflow资源准入；本包是该路径必要的权限/失败窗口实现，不把DISABLED或机械正例当作完整F。

## 源码边界与实际接线

新增固定源码permission program；外部root固定None，导出dispatcher对issue/verify/claim硬编码拒绝，不调用consumer callback，不从bool/dict/object/manifest/release数据产生权限。内部mechanical kernel只供明确的private ordinary fixture验证状态机；它不证明真实outer。信任边界为creating-bootstrap持有的源码/私有program，不声称抵御任意同解释器恶意代码、native副作用或RAM ABA。

LC4要求源码pin与Native builtins闭合的held program：prepare在P1读取和claim前核验、每次entry重新核验，permission claim后才执行runtime slot claim。claim成功后commit/claim-lock失败走同一production claim_runtime_slot，未占槽时先撤销、retire、清exact锁行并保留原primary，owner保持PREPARED。cleanup第一步使用创建时保存的原CodeType/state/native put包置DENY，再校验可能已损坏的verifier/raw；失败作为secondary，不阻断Native关闭。成功末尾才清revoke包，失败保留sticky证据。guard物理关闭后释放owner/plan/snapshot/registry大引用，不由此宣称128MiB retention通过。

Loader3只创建DISABLED program并绑定ADOPTED owner，无external-cut参数。Helper5把原held program/raw注入LC4；原bridge仍只接受None admission。Core42/Parent39闭集增加该helper，Probe40在B_S hook已注册后、handoff_audit前安装新hook，保持原NumPy optional Popen先由B_S原逻辑拦截。原Core runtime全部方法、Namespace3与B_S4不改。B_S关闭后新guard继续到runtime/resource物理清理，再close/report；Validation2只接受零P1 permission的独立construction数据。当前未启动该真实37模块路线。

## 读域与停止边界

construction域由原49 source、固定helpers和namespace/import/profile引用形成，最多128项；runtime域允许compute发行环境内只读open/listdir/scandir，属于条件化TCB，不是全局最小文件白名单。EXE不走runtime豁免。P1、anchor、EXE、INHERITED及core.load_fixture实际需要的3个固定YAML属于permission-only域：仅READ_WINDOW及exact allowed集合可读，最大689=683 P1+6 context/fixture文件；source bookend继续走construction域。3个YAML已在继承输入，不修改B1–B3或原P2七输入。

P1目录枚举也须在窗口内且为授权文件祖先。未知读、fd/opaque open、所有写/进程创建/文件突变均拒绝；选中事件上限16384，最多4条短fault。拒绝是sticky，先DENY。以上是停止帽与实现合同，不是实际P1/Native兼容性、完整调用量或wall/RAM/storage准入；未授权root始终不打开窗口。

## 唯一普通验证

矩阵48项：31项原生命周期相关回归加17项权限/失败/接线测试。原fixture仅适配LC4新slot、真实CONSUMED namespace清理与显式private mechanical permission row，原31测试方法不改；Source49 raw只读/hash/compile，不执行其目标模块。新增验证固定program对伪callback/mode始终拒绝、完整private G0/G2/G3/close、过期/撤销、错误owner/plan/snapshot/thread、阶段读域及目录/写/process、proof/raw损坏仍先撤销、primary/secondary、pre-slot commit与claim-lock实故障、Native终态前close拒绝、hook顺序和成功释放；3个YAML逐项覆盖，变异raw须在副作用前拒绝。所有机械正例均非真实P1许可。

DAG：register → 唯一unit → 独立PRE_SEAL保存 → saved原流重开 → checkpoint → scoped Git。失败终止正常后续并保全账/源，登记后own字节冻结，修补另建successor。static25、unit15、总40秒；阶段5/12/5/5/5秒，unit child10秒。原31-node保存证据runner1.612秒、outer7.778219999978319秒；新增17项及两份源码变换按更宽矩阵留出外层12秒并预留收尾2秒，不因观察失败扩大帽。stdout128KiB/stderr32KiB、sampled256MiB/process、512MiB/pair；root10文件/4MiB、单record1MiB并预留checkpoint1MiB。不重跑NFC12，不执行真实Source49 target、P1、Native owner、角色、模型、solver或长实验。

账源固定CP 0bc1887e3de8a9dbb49c180a97bd5ff7077fee01149f49789f92a68f7caa3240；累计static611.9632506000155、pytest366.48897970000326、unittest269.8382803000168，总1248.2905106000355秒、47条拒绝。旧预算剩余不转用、不退款或重置。继承expanded1307与root5扣driver重叠1后1311 inputs，archive221文件23124646B；自身15、overlap2，精确union1324，逐pin核完整源/归档集合。原39项并行dirty、Source49/NFC12和全部旧source/scope/input/result保持。

root唯一writer；retained_lifecycle_review独立只读PRE_SEAL，没有official verdict、receipt或seal。role/permit/science/resource/formal/run/F门仍false，新增模拟跨度0h。后续必须由具体获批、独立versioned outer提供真实授权切点，再建立实际P1 read-window、full producer及parent adoption证据；本包不发行该权限，也不启动真实校准。
