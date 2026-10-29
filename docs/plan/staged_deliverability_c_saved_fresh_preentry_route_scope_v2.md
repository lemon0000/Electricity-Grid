# F：pre-entry 路线与 transport 静态准备 scope v2

2026-10-30，DRAFT_NONAUTHORITATIVE。依[接口设计](staged_deliverability_c_saved_fresh_full_role_preentry_design_v2.md)，验证[源码审计器](../../experiments/staged_rts24_saved_fresh_preentry_route_audit_v2.py)的实际来源节点、两组压缩基线与保存重放。此包不实现或宣称 FullRolePreEntryBinding 已连通。

唯一前序账源：preentry_route v1 CP，13243B / `685569ed7930824f66736e48edda277c2a8f73b17a05d4427d63a6a1a10ab232`。v1 register接受，inspect在原encode14 XZ帽处拒绝，checkpoint会计完整；root4/852895B、费用5.51420180000423s、原空message AssertionError与绑定字节均保留。继承1522文件/85163306B；archive314文件/38753410B；own21、overlap17、input1526。累计static690.4419885000345、pytest366.48897970000326、unittest414.9035574999798，总1471.8345257000176s，58条不接受记录完整保留。

顺序仅 `register → inspect → independent PRE_SEAL → saved → checkpoint`。首次register后own字节固定；首拒绝后仅checkpoint；修补进入独立successor，不覆盖失败、不退款。各阶段重新核全input/archive/own pins、原F合同、42项并行snapshot及冻结前序CP；PRE_SEAL绑定registration和inspect原始记录，saved再核这两个绑定。Core44保存transport字节，独立bit-string解码、CRC64、原payload编译等价及完整commandline UTF-16单位核算；Core50保存实际超帽XZ字节，独立解压、原payload编译等价、98B超额及冻结encode14拒绝源核对。意外异常保存最多20帧source trace。

static包36秒，阶段帽6/12/6/6/6秒；root10files/4MiB、record1MiB、checkpoint预留1MiB/1slot。各阶段独立`-B -s -S`控制进程；阶段内不spawn child，不调用Capture1/DRAIN1或Native sampler。实际执行driver、route audit、contract snapshot控制模块；inspect还执行依赖仅为stdlib的仓库transport compiler，以及从Parent40单独提取的minify_prefix函数。Core/probe/完整Parent/Source49/native owner目标模块只读AST或compile，均不执行。P1内容读、项目Native/solver/角色/full F、NFC12重跑均0。

两组baseline为Core44+probe42、Core50+probe42，原始payload分别97429/125987B，XZ分别21136/26312B。Core44状态built_baseline；Core50状态xz_cap_rejected，固定26214B帽超98B。v2实际调用原builder，并要求该容量拒绝来自原encode14的原assert CodeType/行号；Core50没有生成transport或commandline。Parent40真实SOURCE_REFS只支持Core44。argv字段预留值不构成可运行invocation，新增endpoint/薄入口/helper实现后的大小和启动profile必须重验。原source文件14、主节点23，另核三条source-span顺序关系及watch→release链；这些是静态顺序，未观察实际执行。保存16行Native failure/stop矩阵，全部OPEN。Core44核生成loader内嵌payload pin、解压帽、memlimit与CRC64 guard AST；普通测试方法0。静态阶段wall charge不作为完整F性能、RAM或硬停止证据。

验收范围只为`source_route_and_transport_preparation_only`。所有actual-entry、Native等价、source-effect接线、完整调用成本、资源准入、正式结论与运行门禁保持未完成。原180s/19metrics/17targets/12500/6500、两侧独立21点/五小时/130CAS及四份terminal记录预留保持。
