# F：构造终态元数据收尾后继

2026-10-29，DRAFT_NONAUTHORITATIVE，登记前自身费用0。本包完成v1普通组件的审查保存与重开，不改变完整F目标，也不新增测试或真实运行权限。

v1的唯一29项普通测试已通过，60规范帧、0failure/error/skip，runner1.670s、外层4.271836800005985s，所有15项自身输入已冻结。保存PRE_SEAL时，调用端PowerShell管道将canonical JSON追加CRLF，导致该阶段被拒绝，charge0.6252245000214316s。机械复现输入确为带CRLF；v1未重试、未改写，已保存完整失败checkpoint。其checkpoint accepted仅表示账务保存，diagnostic_accepted=false，不能写成v1包验收通过。

本独立后继只重开原29项测试原流、同一15项源/测试/合同输入、完整继承集合和原句柄/管道/线程/内存观察。不会再执行unit_child或目标模块。保留LC3真实CONSUMED终态修补、Parent38失败记账/quiet replay/profile失败移存、43图合同及全部反例；这些组件仍须实际37模块和真实issuer/P1验证。PRE_SEAL通过Python subprocess.run(input=canonical bytes)传递，不经PowerShell文本管道。

严格DAG：register → PRE_SEAL保存 → saved原流重开 → checkpoint。每阶段一次、各5秒，独立static总20秒、unit费用0；失败只保存checkpoint并终止正常后续，登记后自身输入冻结。旧40秒包的剩余不转用，旧费用/失败不退款或重置。stdout/stderr旧原流及sampled256MiB/process、512MiB/pair仍按原合同核验；本包不做新的采样或资源准入。root≤10文件/4MiB、单record≤1MiB，预留checkpoint1MiB。

账源固定v1 CP 33714000c4827e628cf6b8129131da247a3835250207fc2bd23330a62a2dac7c，账务完整，诊断拒绝：累计static603.4666847000001、pytest366.48897970000326、unittest269.8382803000168，总1239.7939447000201s，不接受47条。v1 root5文件732049B永久保留。继承expanded1301与root5后1305 inputs；archive216文件22428588B。自身scope/controller2项，overlap0，精确union1307。重开须逐pin核验完整继承与archive，不能用NFC12子集替代。

root唯一writer；retained_lifecycle_review只读PRE_SEAL，禁止official verdict/receipt/seal。原39项论文/图/文献dirty字节、Source49/NFC12与全部旧source/scope/inputs/results保留。NFC12不重跑；新增Source49 target/P1/native owner/角色/模型/solver执行0，新增模拟跨度0h。role/permit/science/resource/formal/run/F门仍false，full F、genuine issuer、同LIVE owner完整producer及whole-workflow wall/RAM/storage仍OPEN。
