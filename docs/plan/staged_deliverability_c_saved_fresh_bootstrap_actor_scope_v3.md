# F：actor终态image与原子发布后继

2026-10-29，DRAFT_NONAUTHORITATIVE，登记前自身受控费用0。继承[v1完整合同](staged_deliverability_c_saved_fresh_bootstrap_actor_scope_v1.md)和[v2夹具修补](staged_deliverability_c_saved_fresh_bootstrap_actor_scope_v2.md)的科学、权限、Native/P1、Parent、stop caps与完整F边界。v1/v2所有source/test/scope/controller/input/result和原费保留，不在旧路径修补或重试。

v2唯一unit出现20组start/end，41 canonical帧而无最终report；stderr32KiB帽触发kill/truncation及output_limit_or_reader_error。outer4.170200900000054/12s，rc1，不能记整包或任何通过结论。夹具修补后暴露生产actor v1的image错误：_terminal/_permission_report被canonical为bytes后又放进待JSON序列化的image，TypeError遮蔽了prepare/finish/guard等原primary；成功释放字段时也可能在seal失败后留下半发布状态。

新BootstrapActor2只修该缺陷及相邻终态保全：image把terminal/permission数据绑定为byte/SHA pins；commit先用candidate values完整计算image/seal，成功后才写slot，失败不清原引用或改变phase；fail无论cleanup/commit seal再失败，都使用原始primitive保存FAILED、原primary、secondary及可形成的fallback seal，保留既有cause，禁止cleanup异常覆盖原始错误。consumer/import/permission/run语义、固定原close/revoke和DISABLED root保持。Loader5/Core44/Probe42仅同步actor2/helper路径与新的Native候选root v2，原runtime class完整CodeType保持；Namespace4、ParentQuietActor1及DRAIN2源原字节复用。真实Parent40和accepted profile关系仍OPEN。

唯一23项ordinary：保留v2原20方法/断言（12actor/loader、4wiring、4quiet及2个固定toy Popen），新增test21在candidate image不可序列化时确认slot/phase/seal不变，test22对terminal commit作private source-code fault injection，确认原guard primary、secondary、FAILED/sticky、fallback seal/observation及物理close一次、guard CLOSED，test23确认嵌套terminal observation为独立JSON副本，caller改动不改变原状态或seal。旧70项证据仍逐pin复用，不重跑；两个toy仍只读stdin、sleep0.12秒、输出release SHA并exit0/3，child drain1秒、join0.5/wait1秒，0项目/Source49目标/P1/项目Native owner/模型/solver调用，NFC12不重跑。

DAG：register → 唯一23项unit（48 canonical帧）→ 独立PRE_SEAL保存 → saved原流重开 → checkpoint → scoped Git，每阶段一次；拒绝后只保全账，登记后own输入冻结。阶段5/12/5/5/5秒、child10秒，static25/unit15/总40秒，unit stdout128KiB/stderr32KiB、256MiB/process/512MiB pair、root10文件/4MiB、单record1MiB并预留checkpoint1MiB全部保持。未来graph256/327681 stdout/131072 stderr仍只是候选stop caps，不是扩大本unit或真实F预算；旧剩余不转用，不退款/重置旧费用或拒绝。

账源固定v2 CP 6be9dd0a13e09d326903b55ea153c01403bed055c72107419932400860624be0，6360B，root4文件796797B。v2 register0.9969454999954905s、unit拒绝4.170200900000054s、checkpoint0.5986667999823112s，总5.765813199977856s；CP accepted/accounting_complete=true仅保全账，diagnostic_accepted=false。累计static627.3663061999644、pytest366.48897970000326、unittest305.9981803999581，总1299.8534662999257秒、51条拒绝。继承expanded1380加root4扣driver overlap1后1383 inputs；archive249文件27844582B。自身10、重叠2，精确union1391，完整历史源/归档逐pin。

root唯一writer，retained_lifecycle_review只读PRE_SEAL；没有official verdict/receipt/seal。原39项并行字节、Source49/NFC12全部16文件、B1–B3、原P2七输入和所有冻结/失败工件保持。真实outer grant、Parent40/P1逐SHA、真实profile/Native及whole-workflow成本/资源准入待完成，role/permit/science/resource/formal/run/F gates均false，宽goal保持active。
