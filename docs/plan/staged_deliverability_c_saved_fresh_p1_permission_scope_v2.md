# F：权限测试夹具后继与完整回归

2026-10-29，DRAFT_NONAUTHORITATIVE，登记前自身费用0。继承[v1实现合同](staged_deliverability_c_saved_fresh_p1_permission_scope_v1.md)全部科学、权限、held-bootstrap TCB、读域、cleanup/retention及完整F边界；本包只修测试夹具，不更改生产源码或旧测试字节。

v1唯一48项运行完毕，46通过、1failure、1error、0skip；runner2.559s、outer4.580765499995323/12s，rc1/capture_error=null。test35改写了registry-bound deadline，所以在到达expiry分支前正确被row identity拒绝；test44逻辑B_S boundary漏了真实对象具有的_creator。原失败原流、48帧对及report、所有源和费用均保留，未在v1重试。checkpoint accepted仅表示账务保存，diagnostic_accepted=false。

新独立test_v2仅改两处：test35推进测试时钟到deadline之后，不改state/admission/registry期限；test44 fake boundary补与owner相同的(pid,tid)。其余31回归和17新增测试方法/检查保持。单次完整重跑48项，保留public DISABLED、伪callback/raw拒绝、private G0/G2/G3/close、阶段读域、revoke独立性、primary/secondary、commit/claim-lock实故障和引用释放的全部要求。ordinary正例不代表真实outer，Source49目标模块/P1/Native owner/角色/模型/solver不执行。

DAG：register → 唯一unit → PRE_SEAL保存 → saved原流重开 → checkpoint → Git；各一次，失败正常后续终止，只保全checkpoint。登记后own输入冻结，修补另建successor。阶段5/12/5/5/5秒、child10秒；static25/unit15/总40秒，未扩大旧帽。stdout128KiB/stderr32KiB，sampled256MiB/process、512MiB/pair；root10文件/4MiB、单record1MiB并预留checkpoint1MiB。旧剩余不转用、旧费/失败不退款或重置。

账源固定v1 CP b6f841643bb0484c5b970b21ed9eb22e15cf8412fbc53ea86b711aa7ef4f0227，10476B；root4文件761684B。v1 package6.290529899997637s；累计static613.6730150000178、pytest366.48897970000326、unittest274.4190458000121，总1254.5810405000332s，不接受48条。完整继承v1 expanded1324加root4扣driver重叠1后1327；archive225文件23886330B。自身5、重叠2，精确union1330 inputs，所有源/归档逐pin验证，不能只核Source49或NFC12子集。

root唯一writer，retained_lifecycle_review独立只读PRE_SEAL。未形成official verdict/receipt/seal。原39项并行dirty、Source49/NFC12、B1–B3、原P2七输入、v1生产实现及所有旧source/scope/input/result原字节保持。NFC12不重跑，新增模拟跨度0h，role/permit/science/resource/formal/run/F门仍false。真实外部授权、实际37-module guard兼容性、真实P1窗口、完整producer/parent adoption与whole-workflow资源准入仍OPEN；本测试后继不替代这些要求。
