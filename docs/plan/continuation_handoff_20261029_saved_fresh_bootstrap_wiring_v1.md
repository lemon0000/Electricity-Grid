# F：bootstrap 后继接线与 transport 检查点

2026-10-29，DRAFT_NONAUTHORITATIVE。宽goal“持续推进”保持active；完整目标仍是真实issuer → 同LIVE owner producer → 父端quiet/reopen采用及整链资源准入，完整F未完成。本轮承接[联合检查点](continuation_handoff_20261029_saved_fresh_project_bootstrap_bundle_v1.md)，root唯一writer，retained_lifecycle_review只读PRE_SEAL，没有official verdict、receipt、production seal或新增真实运行权限。

## 实际改动与证据范围

[Core40](../../experiments/staged_rts24_saved_fresh_pre_entry_lease_v40.py)、[Probe38](../../tests/staged_rts24_saved_fresh_runtime_handoff_probe_v38.py)、[Parent37](../../experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v37.py)由[exact transform](../../experiments/staged_rts24_saved_fresh_project_bootstrap_transform_v1.py)生成。Core增加8项闭合helper/前驱引用，原LocalRuntimeInputs全部方法在同虚拟filename下逐个CodeType等于Core39。Probe从namespace transfer取得ADOPTED后才[加载并认证helper](../../experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v1.py)、创建bridge，再向B_S4定义期注入exact桥。validator同步核bridge/defaults/namespace keyset。

真实P1 issuer cut仍未实现：旧profile/manifest/consumer accepted及本地object token均不构成该权限。[helper3](../../experiments/staged_rts24_saved_fresh_producer_bootstrap_v3.py)因此只接受None，公开bridge与bundle入口拒绝本地token，LC2 private `_P1_AUTHORITY=None`使prepare始终拒绝。它为未来真实37模块构造取证准备必要接线，不是完整producer的替代验收。初始OBSERVED owner的final/report现已覆盖；COLLECTING仍仅接受IMPORTING。Probe使用独立construction schema，不改写旧probe_v2语义。

新Parent只接受独立discovery/import_discovery case，拒绝旧normal。本轮没有真实启动；新Parent的terminal oracle目前明确抛出“remain open”，不能采用该case数据。真实issuer、P1 read-only guard、同LIVE owner producer、父端quiet后reopen和F保持OPEN。

[UTF-16 transport](../../experiments/staged_rts24_saved_fresh_utf16_transport_v1.py)用U+4E00至U+8DFF每字14bit承载原XZ bytes，解决静态命令超长。packed≤26214B为旧base85≤32768B的等价帽；原raw131072B、CRC64/eof/unused_data/hash、64MiB解码与30000命令帽保留。当前命令 **17970 UTF-16 units/30000**，raw transport **40669B**，SHA539bd9d2f4888ebbb09a56ed882d771bafaa466d5d0a7a593f49955369e981b2；这是mechanical/ordinary证据，实际Unicode CreateProcess、startup/import profile尚未验证。

初稿31475、外置后30960两次工程超帽、四个无损XZ候选、原source/transport及PRE_SEAL修正前快照保存在results/tables/staged_rts24_saved_fresh_project_bootstrap_development_v1_non_authoritative，6文件656470B。归档逐SHA核验02/03两份原transport exact bytes，全部15项snapshot payload比较通过。它们controlled_record=false，属于未登记机械准备，不计受控阶段账或46条受控拒绝，不声称受控验收。

## 唯一执行与冻结账源

[scope](staged_deliverability_c_saved_fresh_project_bootstrap_wiring_scope_v1.md)和[controller](../../results/tables/staged_rts24_saved_fresh_project_bootstrap_wiring_v1_non_authoritative/driver.py)首次register冻结所有own inputs，合同“未登记/自身0”为登记前快照。唯一 **39项ordinary测试/80 canonical帧**通过，0failure/error/skip：22个相关constructor测试、12个loader/manifest/B_S source validator测试、5个transport测试。旧graph18与LC2 abort2复用已接受v6；本包未再次执行它们。

Runner3.486s，外层unit8.08216029999312/10s，child49000 rc0、capture_error=null。HANDLE、pipes、reader threads均终态，无kill、截断、reader或cleanup错误。377次healthy sampled观测，parent peak89493504B、child peak110948352B，峰值字段和200441856B；未越256MiB/process及512MiB/pair停止帽，不证明continuous/descendant/128MiB retention或资源准入。

普通fixture只执行helper、独立synthetic source、metadata和孤立decoder；真实Source49 target module/P1/native owner/角色/模型/solver执行均0。冻结NF9 profile的项目路径37项与Source49选择集相等只是metadata复用，不是新37-module actual capture。所有scientific/resource/role/permit/formal/run/F字段false。

继承1265+self26−overlap8= **1283 inputs/64116791B**；archive205文件20936987B。完整inputs/archive与旧递归oracle逐项相等；机械重开input/archive/own/known/charged/Source49共1598次pin比较，mismatch=[]。Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875与NFC12 16文件、CP bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de保持，NFC12未重跑。

Root：results/tables/staged_rts24_saved_fresh_project_bootstrap_wiring_v1_non_authoritative，**6文件759552B**；checkpoint17774B，SHA **99672dc648f0677868ac4449b08d24c0d5d49a8f3d8056c50781992da5f399e4**。accepted、diagnostic_accepted、accounting_complete均true，acceptance_scope=unadmitted_bootstrap_wiring_and_transport_units_only；accounting_errors=[]、pin_errors=[]、本包不接受记录[]。

|阶段|charge秒|cap秒|
|---|---:|---:|
|register|1.3928252999903634|5|
|唯一39-node unit|8.08216029999312|10|
|PRE_SEAL|1.90925349999452|5|
|saved|1.9447001999942586|5|
|checkpoint|1.16914280000492|5|

本包static6.415921799984062/25、unit8.08216029999312/15、总 **14.498082099977182/40s**。累计static600.4670041000165、pytest366.48897970000326、unittest265.5664435000108，总 **1232.5224273000306s**，不接受仍 **46条record**。下一包必须从本CP及该账继承；旧预算/失败/费用不退款、重置或转用，所有已执行source/scope/input/result字节冻结。编辑、只读审查、额外机械准备和Git wall不冒充受控阶段费用；新增模拟跨度0h。

## 下一步

先完成新Parent terminal oracle及其保存原流/完整closed schema、graph调用账和旧40图帽的独立后继。构造路径追加多个owner.entry，不能借本包ordinary通过宣称该帽或全路径资源已够；不能直接沿用旧NF9 profile。再准备自有startup/import discovery/admission与实际37模块兼容性包，按agent.md第9节列完整调用量、wall/RAM/storage、停止条件及专项权限；本轮不授予该真实运行。

完整producer继续需要真实、外部授权且creating-thread-held的issuer→owner→token来源，以及B_S关闭后仍active的read-only P1 guard。后续完整producer应通过outer held bundle执行prepare/run/G2/G3/close，替代旧consume_once，保留失败primary与cleanup secondary；不把本无权限构造模式当作完整F结论。Source49闭合issuer/角色cut与父端真实采用仍须如实解决。

39项并行论文/图/文献dirty保持原字节；共享四导航仅index发布前置段加原HEAD正文，worktree保留并行内容。Git远端hash及终态以发布后的实测读回为准。宽goal保持active。
