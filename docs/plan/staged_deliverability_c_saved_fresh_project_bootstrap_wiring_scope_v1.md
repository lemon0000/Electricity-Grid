# F：bootstrap 后继接线与无权限构造验证

2026-10-29，DRAFT_NONAUTHORITATIVE，登记前草稿。root 唯一 writer；retained_lifecycle_review 只读 PRE_SEAL。本包沿[联合检查点](continuation_handoff_20261029_saved_fresh_project_bootstrap_bundle_v1.md)推进完整F所需的真实 bootstrap 加载路径。完整目标保持不变；本组件不发行P1/角色权限，不完成完整F。

## 实际缺口与实现

独立只读审查确认：Core39/Probe37/Parent36 没有可复用的真实 P1 issuer cut；profile/manifest/consumer accepted 都不是该权限来源。原 `_SavedLaunchIssuer` 仍关闭。新 helper3 因而只接受 admission=None，拒绝本地 object token；其 bundle 中 LC2 `_P1_AUTHORITY=None`，prepare 始终拒绝。真正 issuer、同LIVE owner producer、read-only P1 guard、父端quiet后reopen仍待完整后继实施，不以无权限模式替代这些要求。

Core40新增闭集8引用：bootstrap loader、Construction3、Graph3、LC2、LC1 utilities、Prebound3及其NFC12 checkpoint/complete registration。只支持独立 discovery/import_discovery schema，保留 Source49 epoch 与旧Core所有 runtime class/method CodeType。Probe38顺序改为 namespace → transfer ADOPTED → 持原Core reader/compile/exec加载并认证 helper → 创建None-admission bridge → 定义期向B_S4注入该桥 → before_import/exec/after_import → 取同bundle/report → 原Core关闭。B_S validator 增加exact bridge/defaults/keyset检查；旧consume路径在该独立case不执行。

loader 从 compiled raw 的 CodeType调用 source_program，先以固定LC1源码工具验证源定义，再构造helper私有dispatcher；Capture3所读前驱CP/registration与manifest持有原流逐pin一致。没有真实 Source49 target module exec，普通fixture只执行helper代码/标准loader的独立源码及metadata操作。冻结NF9 profile的project路径恰37项，与Source49选择集逐项相等；这只复用metadata，不证明新链实际capture。

新Parent37绑定该Core/Probe/helper集合并拒绝旧normal case。新startup/import profile、exact graph调用账与旧40图帽后继、父端terminal oracle及whole workflow wall/RAM/storage仍OPEN；Parent明确拒绝采用当前新case的terminal数据。当前只证明新source/manifest/loader/validator连接，不是可执行真实包。

## 命令长度修补与保全

未登记工程测量保存在 results/tables/staged_rts24_saved_fresh_project_bootstrap_development_v1_non_authoritative（6文件，≤2MiB）：初稿31475 UTF-16 units，helper外置后30960，均超过原30000；四个预先固定的无损XZ参数没有解决。原source/transport快照和测量全部保留；04归档还重建并逐SHA核验02/03两份原transport的exact bytes，05记录PRE_SEAL修正后的当前source。它们是额外机械准备，controlled_record=false，不计入受控阶段账或其46条拒绝；不称其受控验收证据。

新UTF-16 transport用固定BMP区间U+4E00至U+8DFF承载每字14bit的原XZ压缩字节，拒绝非法字符/长度/非零padding。压缩二进制仍≤26214B（原base85 ≤32768B的等价帽），原raw≤131072B、XZ CRC64/eof/unused_data/hash、64MiB解码帽及native actor/30000命令帽保留。初步机械结果17970 UTF-16 units，raw transport40669B；实际Unicode CreateProcess/启动profile没有验证，继续OPEN。Source payload变换保持原AST/CodeType等价规则；新decoder只处理数据，不执行Source49。

## 唯一普通验证与资源

矩阵为39项：ProducerBootstrap22项（旧16相关行为+6个None-admission/report反例），BootstrapWiring12项（实际helper loader、Core/Parent字段/pin、B_S4 validator、顺序与缺失/漂移拒绝），Utf16Transport5项（bit边界/最大值、padding/字符/长度、XZ完整性、emitted decoder和payload AST）。Graph原18与LC2 abort原2复用已接受v6，未变字节不再执行。新39项在唯一child运行，strict admission/start/end/report，0skip；实际是否通过以原流/终态为准。

DAG：register → 唯一unit → 独立PRE_SEAL保存 → saved canonical replay → checkpoint → Git。每项一次；失败终止正常后续并保全checkpoint，所有已登记输入冻结，修补须独立后继。预算仍static25/unit15/总40s；阶段5/10/5/5/5s，child8s、-B/-s/-S、stdout128KiB/stderr32KiB、256MiB/process与512MiB/pair sampled、root10文件/4MiB、record1MiB并预留checkpoint1MiB，均不扩大。编辑、只读审查、额外机械准备和Git不冒充受控费用。

新账源固定checkpoint bad043eeae43dcfba7c7dd0c65d33e81271a29f6099e79e23f7a2700879891c8：累计static594.0510823000325、pytest366.48897970000326、unittest257.48428320001767，总1218.0243452000534s，不接受46条。本包自身0，未登记；旧预算/费用/失败不退款、重置或转用。

全部Source49/NFC12、旧执行source/scope/inputs/results、39项并行论文/插图/文献dirty原字节保持。继承v6 expanded1260与root6后为1265 inputs；archive205文件20936987B。自身26、重叠8，精确union1283；独立旧递归oracle对inputs/archive逐项相等，新previous机械耗时0.515674s。所有role/permit/native/science/resource/formal/run/F gates false，新增模拟跨度0h。
