> 后续终态：见[联合检查点](continuation_handoff_20261029_saved_fresh_project_bootstrap_bundle_v1.md)。v5失败和v6的36项合成接受均已保存；累计1218.0243452000534s、46条不接受。下文保留v5执行前的WIP快照，最新账源以该后续交接为准。

# F：构造来源、typed graph与lifecycle联合接线WIP

2026-10-29，DRAFT_NONAUTHORITATIVE，宽goal“持续推进”active，完整F未完成。承接[已发布的逻辑生命周期检查点](continuation_handoff_20261029_saved_fresh_retained_producer_lifecycle_v1.md)。root唯一writer，retained_lifecycle_review只读PRE_SEAL；没有official verdict/receipt/seal或真实运行扩权。

## 实际实现与边界

已有固定Source49(raw epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875)和ENTRY reference/actual双初始化证明；其余36个src模块此前只有import returned后的retention/metadata，旧graph不能补造construction。静态census为37模块、500顶层函数、146 class；源码的Fraction/regex/typing/Protocol/ctypes等确定超出graph v1域。

新链为标准SourceFileLoader实际exec CodeType与held raw编译结果相等、原loader/call frame的真实globals参数、每模块恰一次及returned身份 → construction certificate → source manifest核验的typed graph capture/check → 同modules/raw/registry bundle → held lifecycle dispatcher。ENTRY继续用原namespace raw/unit/2次exec/same module证明；不换loader、不用profile/trace、不触碰真实P1。所有这些目前只有草稿和普通合成尝试，没有真实37-module取证。

当前实现为[bootstrap helper v2](../../experiments/staged_rts24_saved_fresh_producer_bootstrap_v2.py)、[graph v3](../../experiments/staged_rts24_saved_fresh_producer_project_graph_v3.py)、[B_S v3](../../experiments/staged_rts24_saved_fresh_bootstrap_post_return_v3.py)、[lifecycle v2](../../experiments/staged_rts24_saved_fresh_retained_producer_v2.py)和[tests v3](../../tests/test_staged_rts24_saved_fresh_producer_bootstrap_v3.py)。已登记绑定的原路径全部冻结，后续修复只进独立successor。

B_S三个接点使用definition-time held CodeType/defaults/spec；outer bundle失败在producer已开始时经bootstrap_abort保留原primary并唯一cleanup。graph新增显式Fraction/Pattern/typing/Protocol/ctypes/Enum等编码及conditional stdlib/native边界，未知值仍拒绝；它还没有证明真实37模块可以capture。实际Core/probe/parent/manifest/profile与旧40图帽接线仍未完成。

## 受控失败完整保留

|包|观测结果|本包费用s|累计s|不接受record|checkpoint|
|---|---|---:|---:|---:|---|
|bootstrap v1|嵌套TestSuite在admission前.id失败，0项测试开始|8.26701830001548|1169.8695948000052|42|187f56ae2328c2508c25355bdd2c5bcda6928f959ec04499f1a3b04ff5c4fcce|
|bootstrap v2|已进入36项，ctypes内部基类未编码及审计夹具非exec递归；stderr32KiB截断，无最终report|9.955459400021937|1179.8250542000271|43|78695a0173a0b55853647bbbf76bb6b1221f7a354e7532d8eacfe70db6fb99f1|
|bootstrap v3|最终report36项/8errors/0fail/0skip，builtin复制字典与原字典身份不等；stderr截断|12.167247300007148|1191.9923015000343|44|4ba6db1ee16e1e4ee068e60f258454440f74063dce46fae029b95ea4a14ac485|
|bootstrap v4|register5.557246700016549>5s拒绝，unit未启动|7.366585600015242|1199.3588871000495|45|1f4b84d2ace32a072b9407c021aae7503f3f211ec90b59ef55eec28b13236325|

当前账为static586.8018303000529、pytest366.48897970000326、unittest246.0680770999934，总1199.3588871000495s，不接受45条。v4 root3文件354753B，checkpoint8278B；diagnostic false，accounting accepted。所有旧预算/余量/失败保留，不退款、重置、转用；没有完整联合suite接受结果。

## 正在准备的下一包

[controller v5](../../results/tables/staged_rts24_saved_fresh_producer_bootstrap_v5_non_authoritative/driver.py)与[scope v5](staged_deliverability_c_saved_fresh_producer_bootstrap_scope_v5.md)为未登记草稿，自身0。实现和测试完全复用已冻结字节。唯一优化是用固定SHA checkpoint绑定的完整expanded registration maps显式重建即时前驱关系，所有live文件仍hash一次，避免反复递归历代controller。同原递归map逐项相等的独立机械核对已完成，drop/extra/pin副本均改变完整map及canonical pin，实测previous约0.8842542s；这些额外机械核对不是受控阶段费用。

新关系为继承1251、自有12、重叠10、精确1253 inputs；archive195文件19496035B。预算仍40s(static25/unit15)，阶段5/10/5/5/5不变；child8s、-B/-s/-S、stdout128KiB/stderr32KiB、256MiB/process和512MiB/pair sampled、root10文件/4MiB保持。需独立PRE_SEAL后才登记并唯一执行36项，失败原样保存。

## 恢复与未完成工作

先核Git/进程和上述最新账源；若v5已有记录，以真实create-only root/checkpoint为准，不重跑。仍不得重跑NFC12或改Source49、所有失败和已执行输入。39项并行论文/图/文献dirty须保持原字节；导航只做index-only前置段加原HEAD正文。

先取得完整construction→graph→lifecycle合成接受，再补真正37-module兼容性/初始取证与真实bootstrap issuer、Core/probe/parent/manifest/profile和40图帽后继、父端quiet后reopen replay、实际P1许可及whole workflow wall/RAM/storage准入。真实角色/native校准/模型/solver/长实验仍无新权限，128MiB retention与科学/正式/run/F均OPEN或false。新增模拟跨度0h。
