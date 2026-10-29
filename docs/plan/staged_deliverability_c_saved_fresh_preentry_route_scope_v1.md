# F：pre-entry 路线与 transport 静态准备 scope v1

2026-10-30，DRAFT_NONAUTHORITATIVE。依[接口设计](staged_deliverability_c_saved_fresh_full_role_preentry_design_v1.md)，验证[源码审计器](../../experiments/staged_rts24_saved_fresh_preentry_route_audit_v1.py)的实际来源节点、两组压缩基线与保存重放。此包不实现或宣称 FullRolePreEntryBinding 已连通。

唯一前序账源：cleanup_binding v4 CP，11886B / `8374da17a1a759ac94f48f9ca55e1479d59476a4256aeb1f799e7840d8ff896f`。继承1514文件/84266616B；archive310文件/37900515B；own21、overlap16、input1519。累计static684.9277867000303、pytest366.48897970000326、unittest414.9035574999798，总1466.3203239000134s，57条不接受记录完整保留。

顺序仅 `register → inspect → independent PRE_SEAL → saved → checkpoint`。首次register后own字节固定；首拒绝后仅checkpoint；修补进入独立successor，不覆盖失败、不退款。各阶段重新核全input/archive/own pins、原F合同、42项并行snapshot及冻结前序CP；PRE_SEAL绑定registration和inspect原始记录。saved对保存的两份transport原字节进行独立bit-string解码、CRC64、原payload编译等价及完整commandline UTF-16单位核算。

static包36秒，阶段帽6/12/6/6/6秒；root10files/4MiB、record1MiB、checkpoint预留1MiB/1slot。各阶段独立`-B -s -S`控制进程；阶段内不spawn child，不调用Capture1/DRAIN1或Native sampler。实际执行driver、route audit、contract snapshot控制模块；inspect还执行依赖仅为stdlib的仓库transport compiler，以及从Parent40单独提取的minify_prefix函数。Core/probe/完整Parent/Source49/native owner目标模块只读AST或compile，均不执行。P1内容读、项目Native/solver/角色/full F、NFC12重跑均0。

两组baseline为Core44+probe42、Core50+probe42。Parent40真实SOURCE_REFS只支持Core44；Core50拼装仅作transport大小/编译数据基线。argv字段预留值不构成可运行invocation，新增endpoint/薄入口/helper实现后的大小和启动profile必须重验。原source文件14、主节点23，另核三条source-span顺序关系及watch→release链；这些是静态顺序，未观察实际执行。保存16行Native failure/stop矩阵，全部OPEN。独立解码两份实际压缩transport并核生成loader的内嵌payload pin、解压帽、memlimit与CRC64 guard AST；普通测试方法0。静态阶段wall charge不作为完整F性能、RAM或硬停止证据。

验收范围只为`source_route_and_transport_preparation_only`。所有actual-entry、Native等价、source-effect接线、完整调用成本、资源准入、正式结论与运行门禁保持未完成。原180s/19metrics/17targets/12500/6500、两侧独立21点/五小时/130CAS及四份terminal记录预留保持。
