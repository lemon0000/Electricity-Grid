# F：原builtin字典身份绑定后继

2026-10-29，DRAFT_NONAUTHORITATIVE，未登记。完整目标、pipeline、36-node矩阵、Source49/权限/TCB边界、停止条件均继承[整体合同](staged_deliverability_c_saved_fresh_producer_bootstrap_scope_v1.md)及[前驱](staged_deliverability_c_saved_fresh_producer_bootstrap_scope_v3.md)。root唯一writer，retained_lifecycle_review只读PRE_SEAL。

v3已按原帽拒绝并保存：stdout包含36项start/end及最终report，tests_run36、errors8、failures0、skipped0、accepted=false；stderr达到32768B且截断，capture_error=output_limit_or_reader_error。已编码的ctypes及既有graph/abort反例通过，仍不能据此称整包通过。可见constructor错误是source file/builtins identity differs：私有globals克隆了builtins模块，再用其复制dict去比较标准loader实际使用的原builtin字典，发生身份不等。原字节、截断原流及费用完整保留，不重跑/覆盖。

本后继bootstrap helper v2仅在克隆前持有原_BUILTIN_NAMESPACE=vars(builtins)，metadata以该同一对象核SourceFileLoader的__builtins__；不删除或放宽该身份要求。测试独立v3仅改指新helper，graph v3、lifecycle v2和B_S v3原实现继续复用。36项全部作为本包唯一测试，旧失败报告不能拼接为接受。

前驱checkpoint SHA **4ba6db1ee16e1e4ee068e60f258454440f74063dce46fae029b95ea4a14ac485**，root4文件740994B，只接受拒绝元数据与完整记账，diagnostic false。累计static579.4352447000376、pytest366.48897970000326、unittest246.0680770999934，总1191.9923015000343s，不接受44条。v3包12.167247300007148s及所有旧预算/失败不退款、不重置、不转用；新包自身0，未登记。

继承1245、自有12、重叠8，精确1249 inputs；archive188+4=192文件/19141282B。完整expanded/own/root精确集合与pins每阶段重建，前驱失败和严格phase prefix/create-only保持。

DAG register→唯一36-node unit→独立PRE_SEAL保存→saved→checkpoint→Git。预算仍static25/unit15/40s，5/10/5/5/5，不扩时长或输出帽；其余static5/unit5仅本包失败保全。child≤8s、-B/-s/-S、stdout128KiB/stderr32KiB、256MiB/process/512MiB/pair sampled；root≤10文件/4MiB、record≤1MiB并预留checkpoint1MiB。费用只计受控capture，编辑/审查/Git另计wall。

仅synthetic标准loader/逻辑owner和compile-only census；真实Source49模块/P1/issuer/角色/native校准/模型/solver及长实验均不执行。真实37模块兼容性、Core/probe/parent/manifest/profile/40图帽后继、父端reopen replay、128MiB retention及whole workflow/F仍OPEN，全部gate false。
