# F：标准exec事件过滤及ctypes基类后继

2026-10-29，DRAFT_NONAUTHORITATIVE，未登记。继承[整体合同](staged_deliverability_c_saved_fresh_producer_bootstrap_scope_v1.md)与[suite后继](staged_deliverability_c_saved_fresh_producer_bootstrap_scope_v2.md)的完整目标、pipeline、36节点矩阵、Source49/TCB/权限边界和全部false gates。root唯一writer，retained_lifecycle_review只读PRE_SEAL。

v2唯一unit已实际进入测试：旧graph的12项及若干typed/abort反例正常返回，但ctypes Structure的MRO中内部_CData没有module导出别名而被拒绝；合成audit夹具无前置event过滤，在构造held FunctionType时收到function.__new__又递归调度，产生多条traceback。capture按原stderr32KiB帽记录output_limit_or_reader_error；原流截断、不完整最终report不能视为36项通过，不能从start/end推断最终接受。所有原source/测试/输入/费用和root4文件735642B完整冻结，不改或重跑。

本后继仅两处行为修复：graph独立v3为exact ctypes.Structure.__base__提供显式conditional ctypes owner row，其余未知类仍拒绝；测试独立v2在调用held dispatcher之前过滤event!='exec'，与原B_S v3已存在的exec过滤相同。原bootstrap helper v1、B_S v3、lifecycle v2及旧graph/测试字节均保持。实际测试矩阵仍为GraphTypeTests18+LifecycleAbortTests2+ProducerBootstrapTests16=36；相关graph与constructor路径发生变化，全部36本包唯一执行，不拼接旧失败输出冒充接受。

前驱checkpoint SHA **78695a0173a0b55853647bbbf76bb6b1221f7a354e7532d8eacfe70db6fb99f1**，accounting accepted但diagnostic false。累计static575.5563558000242、pytest366.48897970000326、unittest237.77971869999965，总1179.8250542000271s，受控不接受43条。v1累计包8.26701830001548s、v2包9.955459400021937s与所有旧账不退款、不重置、不转用。新包自身0，未登记。

继承1238项、自有12、重叠8，精确1242 inputs；archive184+4=188文件/18400288B。每阶段重建完整expanded/own/root关系及逐文件pins，失败root和阶段prefix保持create-only/terminal规则。

完整DAG register→唯一unit→独立PRE_SEAL保存→saved→checkpoint→Git；每阶段一次，失败停止正常后续并保存。预算仍static25/unit15/40s，5/10/5/5/5s，不因上轮日志或失败扩帽。child≤8s、-B/-s/-S、stdout128KiB/stderr32KiB、256MiB/process/512MiB/pair sampled，root≤10文件/4MiB、record≤1MiB并预留checkpoint1MiB。其余停止及保全语义沿用原合同。

仍只执行system tmp synthetic标准loader及逻辑owner。没有真实Source49模块、P1、issuer/角色、native校准、模型/solver或长实验权限。真正37-module兼容性、Native Core/parent/probe及独立profile/40图帽后继接线、128MiB retention、父端reopen replay及完整workflow/F保持OPEN；不能把本包合成成功替代上述工作。
