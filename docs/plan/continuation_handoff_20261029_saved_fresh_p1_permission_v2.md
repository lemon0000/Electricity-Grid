# F：权限核验、持续guard与失败清理接线检查点

2026-10-29，DRAFT_NONAUTHORITATIVE。宽goal“持续推进”保持active，完整F未完成。本轮承接[构造终态交接](continuation_handoff_20261029_saved_fresh_construction_terminal_v2.md)，完成必要的permission/guard/LC4机械实现与bootstrap接线；没有真实outer授权、真实P1读取或新Native校准。root唯一writer，retained_lifecycle_review独立只读PRE_SEAL，未产生official verdict、review receipt或seal。

## 实际实现与权限边界

[permission helper](../../experiments/staged_rts24_saved_fresh_p1_permission_v1.py)的外部root固定None，导出dispatcher对issue/verify/claim硬编码拒绝；consumer参数、bool/dict/object、任意callback或伪mode不能升级权限。source_program先核exact raw和固定LC1 utilities，再compile/exec。内部mechanical kernel有完整issued/claimed/retire状态机，普通正例明确由private fixture手工构造，不是实际外部授权。

[LC4](../../experiments/staged_rts24_saved_fresh_retained_producer_v4.py)由[精确变换](../../experiments/staged_rts24_saved_fresh_permission_lifecycle_transform_v1.py)生成：首次P1读取/占槽前核固定源码held program，每次entry再核；permission claim成功后才执行runtime slot claim。prepare末尾唯一委托claim_runtime_slot，首个commit或claim-lock失败保持owner PREPARED、Native close0、撤销窗口并清exact锁行。claim与retire双失败仍抛原primary，secondary保存在cause group。

创建时保存的原revoke CodeType/state/native put包使cleanup第一步先DENY，不依赖可能已漂移的raw/verifier/proof；retire失败只进入secondary，不阻断exactly-once Native cleanup。成功关闭完成全部postcheck/reset后才清_permission_revoke=None，失败保留sticky证据。guard在物理owner终态后安全CLOSED并清owner/plan/snapshot/registry等大引用；这只是释放合同，不证明128MiB retention。

[bootstrap变换](../../experiments/staged_rts24_saved_fresh_permission_bootstrap_transform_v1.py)生成Helper5、Loader3、Core42、Probe40、Parent39、Validation2。Loader只创建DISABLED program并绑定ADOPTED owner，没有external-cut参数；Helper将原held program/raw注入LC4，bridge仍只接受None。Probe在B_S hook已注册后、handoff_audit前装独立hook，保持原NumPy optional Popen先由B_S拦截。B_S关闭后新guard继续，直到runtime/resource物理清理才close/report。原Core runtime所有方法CodeType不变，Namespace3/B_S4不改，原43图合同未扩大。真实37模块兼容性尚未执行；新Parent仍只支持独立construction discovery/import_discovery，不是完整producer采用路径。

读取域明确区分：49 source及helpers/namespace/import/profile为construction集合；compute发行环境为条件化runtime只读域，不能称全局最小白名单；EXE不走该豁免。P1、anchor、EXE、INHERITED及core.load_fixture需要的3个固定YAML只在READ_WINDOW与exact allowed集合内可读，上限689=683 P1+6 context/fixture。P1目录枚举也受限；未知读、fd/opaque open、所有写/process/mutation拒绝，selected上限16384、最多4条短fault。实际窗口始终关闭，本轮这些是机械实现与停止帽，不是Native/P1 admission。

## 唯一失败与独立测试后继

[v1合同](staged_deliverability_c_saved_fresh_p1_permission_scope_v1.md)唯一48项实际跑完，46pass、1failure、1error，runner2.559s、outer4.580765499995323s、rc1/capture_error=null。test35改写registry-bound deadline，正确先被row一致性拒绝，未达到所测expiry分支；test44 fake B_S boundary缺真实对象的_creator。原生产代码、测试v1、controller/scope及原流全部冻结，没有在v1重试。

v1 root：results/tables/staged_rts24_saved_fresh_p1_permission_v1_non_authoritative，4文件761684B，CP10476B，SHA **b6f841643bb0484c5b970b21ed9eb22e15cf8412fbc53ea86b711aa7ef4f0227**。register1.1481916999910027s、unit拒绝4.580765499995323s、checkpoint0.5615727000113111s，总6.290529899997637/40s。accounting_complete=true、diagnostic_accepted=false；checkpoint accepted仅表示账务保全。累计1254.5810405000332s、拒绝48条。

[test_v2](../../tests/test_staged_rts24_saved_fresh_p1_permission_v2.py)仅修两处夹具：推进时钟到deadline+1而不改row/state期限；补与owner相同的(pid,tid)。生产源码不改，48项标准和caps不减。新controller还修正了历史driver加载顺序：直接使用先经CP pin/canonical核验的registration own map，不在校验live pin之前执行历史driver。

[v2合同](staged_deliverability_c_saved_fresh_p1_permission_scope_v2.md)唯一完整48项通过：31项相关生命周期回归+17项权限/失败/接线测试，0failure/error/skip，98个canonical帧、runner **2.568s**、外层 **5.413173999986611/12s**，rc0/capture_error=null。涵盖public DISABLED、伪dispatcher/builtins/raw无副作用拒绝、private G0/G2/G3/close、过期/撤销、错误owner/plan/snapshot/thread、3YAML阶段读域、revoke独立性、primary/secondary、真实production slot helper的commit/claim-lock故障、B_S先序拦截、引用释放和Core方法等值。

handle/pipes/readers均终态，无kill、截断、reader/cleanup error；255个native sampler样本，parent peak35753984B、child peak64606208B，sampled峰值字段和100360192B，低于原256MiB/process及512MiB/pair停止帽。此处是ordinary unit child的采样，绝不是Native owner、continuous/descendant/128MiB retention或完整资源准入证据。

## 当前账源与冻结范围

v2 root：results/tables/staged_rts24_saved_fresh_p1_permission_v2_non_authoritative，6文件756489B；CP8188B，SHA **f4a933bb82a15473df9624941d8fe83baecd443e43fa1dc45b681121a4e50c9f**。accepted、diagnostic_accepted、accounting_complete均true，acceptance_scope=permission_verification_cleanup_and_bootstrap_units_only，accounting_errors=[]、pin_errors=[]、本包拒绝[]。v1拒绝原样保留。

|阶段|charge秒|cap秒|
|---|---:|---:|
|register|1.5140968000050634|5|
|唯一48项unit|5.413173999986611|12|
|PRE_SEAL保存|1.2132820999831893|5|
|saved原流重开|1.43543710000813|5|
|checkpoint|0.6319659999862779|5|

v2 static4.794781999982661/25、unit5.413173999986611/15，总 **10.207955999969272/40s**。本轮两包新增16.49848589996691s；累计static **618.4677970000005**、pytest **366.48897970000326**、unittest **279.8322197999987**，总 **1264.7889965000024s**，不接受 **48条**。下一包从本CP与全账继承；旧预算/失败不退款、不重置或转用。编辑、只读审查、机械准备和Git墙钟不计为受控阶段费。

v1 expanded1324加root4扣driver重叠1后1327；v2自身5、overlap2，精确union **1330 inputs/67785927B**；archive **225文件23886330B**。v1 own15及v2 own5已登记冻结。当前v2 registration687543B/SHA c99dc51773ab6d5ed9cc62ead44de0eb0125c2284d5e15d8138ecc0787d599ff；unit exit35731B/SHA 5f90c69131031f137a7e1fb828aff12e87969d991ec0f5dd56d0c2c4eee2e73c。

最终机械重开input/archive/own/known/charged/Source49/NFC12共 **1639次pin比较**，1422个独立文件，mismatch=[]。原39项并行dirty逐SHA相同；Source49全部49文件和epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875保持；NFC12全部16文件和CP bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de保持。NFC12未重跑，新增真实Source49 target/P1/Native owner/角色/模型/solver执行0，新增模拟跨度0h。

## 完整F下一步

完整目标不变：实际获批outer提供真实授权切点 → 同LIVE owner完整prepare/run/G2/G3/close → parent quiet后独立重开采用 → whole-workflow wall/RAM/storage准入。当前program硬关闭且Helper仍None admission，所以本轮没有完成真实issuer或完整producer。eligibility、source pins、profile、consumer binding、release数据均不能自行变成permission，Source49的closed SavedLaunchIssuer也不能复活为诊断许可。

优先准备具体外层受控调用的独立source/scope、授权创建点及child/bootstrap绑定，再使用versioned loader/permission successor填入真实root；当前生产源码不能就地升级。随后补实际37-module guard兼容性与独立startup/import profiles，再接IMPORTING下prepare_consumer、profile-matched LIVE后的genuine issuance、完整LC dispatcher及parent终态采用。新guard没有增加逐文件Core.entry图遍历；完整producer旧107静态基线仍缺outer activation、P1 I/O/fault/parent成本，不能用43构造图或ordinary时间当整链预算。按agent.md第9节完成真实校准包DAG/预算与专项授权后才能执行。

所有role/permit/science/resource/formal/run/F门仍false，宽goal保持active。四个共享导航只在index发布前置段加旧HEAD正文，worktree并行字节不改；remote hash/index/39项保留终态以发布后现场读回为准。
