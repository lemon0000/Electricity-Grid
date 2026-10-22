# 保存H1 constructor窗口依赖诊断

2026-10-21，R3 / DRAFT_NONAUTHORITATIVE，根代理唯一writer。主目标仍为完整正式实验准备，当前优先整链预算→168h/≤24h真实phase/episode终结。复用前轮110项、H3保存身份重构、H1净对照和全部旧hour0/2h/3h主体，不重跑它们。前轮final SHA=f6680d1110a9525e3727ccad49a3b0bdf131763923bd1b49d21ad6d8c564e0e7，164bindings fresh匹配。

问题：静态probe证明continuous_grid_normal._dependencies alias未被候选historical guard/implementation identity观察，但未执行Reader。现固定旧historical batch v1和候选v2各一次H1/M5 replay_prefixes，在真实HistoricalSnapshot.__init__正常返回的profile事件注入该alias变化。此时构造器内部完整self.inspect及accepted-state检查已完成，caller的第二inspect或take尚未执行。wrapper在原runtime tuple追加明确probe条目，不改文件、科学阈值、输入或原函数code；每个call finally关闭profile并恢复alias，最后fixture恢复。

完整路径：继承pins/465case/444owned SHA→保存synthetic source/catalog/manifest-pin resolver seam→导入后继→old H1 Reader（profile记录实际ReadView、constructor accepted状态及inspect次数；窗口注入依赖alias；捕获return/拒绝）→恢复profile/alias、清空返回frames、核Reader/ReadView关闭→同样new H1 Reader一次→恢复fixture→case/owned/source SHA→报告/进程尾核。无static identity memo；保留saved manifest resolver，不重审真实manifest来源。不能把本诊断时间当真实manifest或生产成本。

固定两次historical Reader call，old至多两次parent遍历/new一次，共至多3parent/6inspect_job/30toy stage replays，0新N/selector/normal Job/native。两次返回或拒绝均保留事实，不预设结果；diagnostic_complete仅表示观察闭合。即使old拒绝而new返回，也只证明这个historical Reader窗口检测不同，不证明完整source batch双Reader或科学结果被接受。full source batch、owner接线、完整依赖闭包/ABA仍未获证。

只读保存root为D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0，audit hook拒绝文件修改并每10s记录case read-open活动（非科学进展）；所有输出用全新attempt目录。wall120s、无case-read活动45s、sampled tree RSS1GiB、输出logical64MiB，2s采样/30s心跳；超限仅终止PID/create-time匹配的owned树、保留原件并独立after核验，不扩时或自动重试。预估依据是前轮H1完整双Reader old57.131s/new27.815s，本次各一个Reader且有profile开销；120s是硬诊断额度，不是可完成上界。

资源与清理证据只覆盖实际捕获ReadView、Reader的_closed/journal/anchor/root fields和case/source bytes；无writer lease、atomic-live或crash认证。候选与旧原件不改，formal/resource/native/full192/seal/official各门false。并行paper文档/图修改属于其他工作，保留。

注入判据固定exact constructor code、dis正常RETURN偏移、exact Reader bases、accepted completed/attempted/status/head；v2还要求私有capture原对象及constructing/taken状态。每call injection_count恰1。profile保持只读观察以记录实际parent/Job/stage及cleanup调用，成本不作性能推断；原profile必须None并恢复。cleanup predicates为独立观察，即使false也不是诊断基础设施失败。

实际HistoricalTimedSnapshot MRO插入timed_job_parent.SourceParent，故有效parent close为该类第222行，会尝试journal/anchor/root并设None；它与前轮stand-in借用的直接HistoricalSnapshot.close（bounded_file_parent:144）不同。该区别在本次实际Reader/profile中记录；不能把前轮窄cleanup测试称实际Reader相同MRO关闭证明。

probe_01已完整观察：old以parent intent differs from pinned source拒绝，窗口wrapper实际调用3次；new在0次wrapper调用下返回。两边均10stage/2inspect_job，old/new parent为2/1；actual SourceParent.close各一次，9/11个ReadView全closed，3个owner字段None，新capture清空。outer69.391s/1308pins未变/465case+444owned SHA一致，0Job/native。只证明单Reader窗口差异，未执行full source batch，未证明科学输出漂移。该版callback在异常判据有raise风险（本次未触发），原tested_bytes保留。

针对修复仅关闭这个named gap：historical v2观察normal模型直接函数/不可变常量、_dependencies的Path/__file__/sha256/platform/version槽位与platform版本函数；constructor前及原全部postbookends后重新读取source SHA/runtime tuples，要求exact tuple/str与names/hash结构、一致才返回。仅保存operation内不可变值，不跨operation缓存；source/validator强制normal_model_dependency_bookends_verified。完整外部依赖闭包、Path方法、同字节非确定性/ABA仍OPEN。

model_units_01固定152项（原110+42个named模型/metadata/metric拒绝），wall180s/RSS1GiB/输出64MiB、2s采样/30s心跳/0Job/native；普通窄回归。probe_02随后固定与probe_01相同两H1 Reader和120s/45s活动/1GiB/64MiB预算；callback改为instrumentation_errors后验无效，不抛异常到被观察代码。预期old消费变化后拒绝，new在take前识别alias拒绝；实际结果单独保存，不以诊断exit0称全部等价。修复前三源码及测试保存在before_edit，旧scope164 binding按原快照解析。

代码变化后另以一个H3/M5完整新batch重新执行保存identity绑定正例及21辅助拒绝（旧正常输出按SHA复用，无旧Reader重跑），wall240s/90s无case-read活动/RSS1GiB/输出128MiB；仍保留saved manifest resolver seam且无static identity memo。随后H1 fixed old→new各一次完整batch重测净路径，wall240s/90s活动/RSS1GiB/128MiB，不用旧51.3%替代新测量。两包分别登记request并串行执行，0新Job/native，不扩预算、不外推192h。
