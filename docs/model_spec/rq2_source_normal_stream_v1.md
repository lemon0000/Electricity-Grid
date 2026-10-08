# 流式来源组装后继与接入清单

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE。范围仅为来源组装候选和重建验证；没有接入任务准备、pair binding、solver、store 或 replay。

## 已实现边界

`source_normal_stream.py` 复用旧来源 manifest/file verifier、RTS loader、`ContinuousNormalInputs` 的快照和验证，使用 `identity_stream` 计算完整输入内容摘要。仍加载完整年度数据，不裁剪为请求窗口。raw-hour 连续性、incoming carry、时钟、需求和初值约束保持。

四种身份明确分开：

| 字段 | 含义 |
|---|---|
| `normal_identity` | 旧 normal 内容及依赖 payload 的流式摘要；与旧编码相同 |
| `legacy_content_assembly_identity` | 按旧 assembly schema 及旧 adapter 源码 hash 计算的内容对照；不表示旧实现执行过 |
| `implementation_identity` | 新 contract、新 adapter、流式原语、旧来源 helper 源码及旧 normal 全依赖/runtime 的独立摘要 |
| `assembly_identity` | 新 contract 绑定来源、小时、normal 内容、旧内容对照及新 implementation identity |

构造入口要求调用者独立保留 `expected_implementation_identity`，在加载前、返回前核对。它与旧 `assemble_source_normal` 一样构造候选，不宣称候选已满足某个外部实验输入声明；后续消费入口必须独立核对预先保留的内容及新 assembly pins。重建入口要求 exact 新类型和内置 SHA256 字符串，重建来源并检测内部可变内容漂移。新类型被旧 source validator 拒绝，不能把它塞入旧执行链继续运行。

磁盘源码 hash 不是运行内存代码的真实性认证；和旧实现一样，不防恶意 monkeypatch、并发写入或 ABA。输入遍历期间需稳定。年度数据 deepcopy、binding 快照和 mapping/set 的局部物化仍可能消耗大量内存；本层不承诺 H25 或整任务能在 768 MiB 内完成。

## 全链调用点与后继顺序

通过 `rg` 检查 `src/rq2_joint_deliverability_boundary_v1` 内全部 Python 文件；下表区分完整 normal 输入摘要和其他编码，避免只改第一次 prepare。

| 层 | 旧调用点 | 后继要求 |
|---|---|---|
| 来源 | `source_normal.assemble_source_normal/validate_source_assembly` | 独立流式候选已完成一次真实H25组装内容复现/资源观察，见probe2；validate重复重建仍待验证 |
| 对应关系 | `power_normal_binding` 调用旧 source validator；`pair_normal_binding` deepcopy 后调用 power binding | 新类型、新来源重建及新 binding provenance；旧 binding hash 只能作为旧内容对照 |
| 任务准备 | `normal_task_inputs.prepare_task_inputs` 组装、再次 normal hash、pair binding 重建 | 同时接通以上路径，独立绑定新 request/implementation；旧 build-only 记录只提供机制声明 |
| 数值入口 | `normal_execution`、`source_normal_execution`、`continuous_grid_candidate` 的 normal hash；`continuous_grid_normal.build_continuous_normal_model` 的内部 hash | 覆盖直接 import aliases 和内部检查；保留数学模型/solver 语义，单独测试模型规模、约束和 witness |
| 持久化和回放 | `normal_store`、`normal_replay` 的 normal hash | 新 execution/store/replay 身份贯通，不能沿用旧执行 pin；保留三态结果解释 |
| 下游连续执行 | `common_request_adapter`、`grid_information`（两处）、`outage_trajectory` | normal witness 到 incoming/current 的后继交接，不能把 terminal carry 当作 origin |
| 其他编码 | execution/result/witness 的 `_digest/_encode`；旧 `normal_worker` 整 assembly wire；task worker 的 compact/report wire | 按真实 payload 区分：小声明摘要不是年度输入；result/wire 大小另受预算约束，不能宣称已流式化 |

接入应逐层在显式后继中完成；不以运行时替换旧模块全局函数来复用旧执行身份。旧 `normal_worker` 的大对象传输不是当前 compact task 路径，不能将它的修复计入任务路径完成度。

## 验证与下一步

tiny synthetic 差分比较新旧输入对象、normal 内容和旧 assembly reference，验证新 assembly identity 不同、旧类型入口拒绝；禁止旧完整输入 `_digest/normal_input_identity` 被新路径调用。覆盖来源加载期间变化、实现前后变化、独立 pin 拒绝、可变输入漂移、调用者快照及参数不被修正。

测试不提供真实源资源证据。本层审查完成后，下一必要验证是独立受限、零 solver 的真实 H25 内容对照；使用新入口/实现 pins 和新的 non-authoritative 诊断位置，保留旧 attempt/probe。其结果只评价本层，不能作为完整 prepare、normal/replay 或四臂资源通过。原始数据观测与 initial state、workload-power 映射等机制假设保持各自标签；科学注册、恢复右删失和正式启动门仍开放。

主验证命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_source_normal_stream_v1.py tests/test_rq2_source_normal_v1.py tests/test_rq2_identity_stream_v1.py tests/test_rq2_continuous_grid_normal_v1.py`，165 passed in17.91s，含33项新适配器测试。source SHA256 `4877815bcce25bd5793d852b6202469599956f365e13671582ab39b4b2b93821`；test SHA256 `6edd3d038490724ddae15fab864ae070546d614b7bbf9200cdc6e82055bb3097`。旧 attempt 22项和 probe 13项绑定文件的大小与SHA256均逐项匹配原索引。

独立 pre-seal 审查发现，输入完成 deepcopy 后仍持有 loader 原对象的局部引用。现已在hash前释放该引用，weakref测试验证原对象在编码前释放；输入内容及模型语义保持。重建验证时调用者原assembly与rebuilt仍可能并存，不承诺其资源上限已满足。

独立最终 targeted 33 passed in3.83s；限定来源候选层无开放实质finding，仅为pre-seal复核，不是official verdict/receipt。完整接入与真实资源证据缺口如上。

## 真实来源零 solver 探针

`experiments/diagnose_rq2_stream_source_v1.py` 使用旧 H25 开发 YAML 的 pinned source declaration 和768 MiB process/Job上限，单独限定117秒phase及3秒quiet；默认只读检查，显式 `--execute-development` 才运行。新实现pin绑定脚本、source stream实现及既有诊断/declaration helper，且旧controller声明仍须通过原hash核验。

探针在新non-authoritative sibling目录建立lease；`request.json`在spawn前持久化，担当此次诊断intent；`launch.json`在release前写入。child核验exact argv/environment/root、phase/host预算、process/PID/creation和实现pins。来源候选只从pinned build-only记录解码机制输入，核对声明角色、原normal/assembly/pair/binding内容pins及实际来源；solver入口设为拒绝。不会运行pair binding、model build、normal execution或replay。

parent检查exact进程观测类型、静默、exit、身份及所有非认证flags；对有界source输出重算旧内容reference和新assembly identity，核对25小时映射及8784小时原数据保留。记录elapsed/lifetime working set和Job commit观测；不把资源观测升级为完整prepare/整任务认证。异常只记录类型和最多8帧，不记录消息/locals；failure使用新schema，写入失败另存fallback标记，异常或缺失/畸形输出一律unresolved。每个JSON最大16KiB，write-once，保留原attempt/probe及所有失败工件。

主相关验证：`tests/test_diagnose_rq2_stream_source_v1.py tests/test_diagnose_rq2_normal_prepare_v1.py tests/test_rq2_source_normal_stream_v1.py`，113 passed in9.73s。55项新probe测试覆盖pinned机制解码、内容外部pin不一致、全部成功字段/类型和父进程观测故障判定，以及三个solver入口拒绝；直接调用新main/child验证request→spawn→launch→release顺序、launch上下文错配、已有root及nested root保留。实际运行记录待追加，测试不代替真实来源结果。

本次候选外部保留pin：probe implementation `0de286ae09289d3cd13b35409724f9049b4b589540b4934bd20eca1602fc79bd`，script SHA256 `bad1194172ad67dfb401a1e076b57eb75e112f757ed25078e2af963b28bb70f2`，test SHA256 `46a06004ef77be820f58f0487a1b0183c0d2ce1fc60f728d55a0d33af45d2d19`。原YAML SHA256 `9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6`保持。较早draft的默认只读入口已实际返回headroom sufficient=true、errors=[]；运行入口仍须重查，这不是预留资源，也不是运行结果。

### probe1 实际终态与 v2 修复

v1独立最终55 passed in5.55s，限定pre-seal findings闭合后执行一次真实来源探针。`results/tables/rq2_stream_source_probe1_non_authoritative` 保留request/launch/observation/summary/lease；PID26808，creation FILETIME134344429360752293，1.969秒exit1、Jobquiet=true、10 samples；process/Job commit峰值108838912/110145536 bytes，minimum runtime commit17294381056 bytes，无reserve/API error。无started/source/failure，因此直接观测只说明child在进入来源函数前失败；status为unresolved_probe，不能报告来源成功或实际异常类型。11个工件hash索引见 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_source_probe1_evidence.json`，原v1脚本/测试也保留。

只读复算定位了启动核验的顺序缺陷：旧 `task_process_identity` 使用未排序的环境dict JSON；parent按YAML插入序算得 `f45c2193211f60f3ea76e734419ff1559f4e52dccc983b73bb91cf8328899965`，与实际packet一致；相同键值按Windows环境块排序后，child重算为 `7cd65a03f6c9eb87196f133acaa88c4726d12f7b4978d2f0c286dd89fc16d7a6`。这是代码及复算支持的机制定位，不是child traceback直接证实的异常。

后继 `experiments/diagnose_rq2_stream_source_v2.py` 保留旧进程模块，child从固定declaration环境重建parent的插入顺序计算指纹，同时继续精确核对实际环境键值。新测试直接模拟Windows环境排序，55 passed in5.63s。后继外部保留implementation pin `8dd435735c77a5a8a954919af18bd7feeda25ce4a47401eb3874e790accf3960`，script SHA `216c8e4a19368aee0d20f0692ca003f9cf6f7bd71a5340c0a2c0e4fc69e9fd17`，test SHA `8028827315f87727d0ffc818ce603c642a8e593e14e23c88685c6a422cc3dd8d`。相同来源/预算下的新probe只用于验证这一修复及来源内容，不重写或恢复probe1。

### probe2 实际来源内容复现

v2独立targeted55 passed in5.56s，限定pre-seal findings闭合后运行一次：命令为 `D:/Miniconda3/envs/compute/python.exe -B experiments/diagnose_rq2_stream_source_v2.py --declaration configs/rq2_normal_task_h25_development_v1.DRAFT.yaml --expected-sha256 9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6 --expected-implementation 8dd435735c77a5a8a954919af18bd7feeda25ce4a47401eb3874e790accf3960 --diagnostic-root results/tables/rq2_stream_source_probe2_non_authoritative --execute-development`。

终态 `source_content_reproduced`，errors=[]、failure=null，solver_calls=0。PID12732，creation FILETIME134344432158121646，process identity `b388558b03d2e2366921a2677f786af6b9605425aeea2b165ee7aeea93701015`。进程10.89秒exit0、Jobquiet=true，51次采样，无reserve/API error；最低host commit余量17068761088 bytes。source阶段8.8620142秒，process/Job commit峰值339828736/341061632 bytes，lifetime working-set峰值362663936 bytes。两种内存口径不互换，均是本次进程观察。

完整8784小时data保留；raw0..24映射source1..25。normal内容 `d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c`、旧assembly内容对照 `626f7dbe49772302d35da13bb05f2ffb69f1f599e35310484177c00711b32e7a` 与既存记录一致；新implementation `7dc920bd3ef0bba3bf7bc59e0ebe01535045ae64c43429fa99f67aa1ff1d247c`，新assembly `689ac1bc2d2a527b1a0efbe75e51d4f2a44cddb27cca7a1c623b5a0a6cabbe9e`。旧内容reference不是旧实现执行证明。

summary绑定observation SHA `27353d584a8505834175546ba0e1ae0c5169965cd45a2a3b45c9269d49750c04` 及source SHA `c8967812e4c78aac36b003c66d3ea5211ad1743b36eabc327485d0b2ec9383c1`；13项证据索引 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_source_probe2_evidence.json`，SHA `3f60cf71257c98c5456057ecf5369292add47b52fbc080b92b47b13f377c2f15`。原22+13+11项及新13项文件大小/哈希逐项一致。

下一必要工作为后继power/pair binding与prepare完整路径，尤其重复来源重建/快照的内存；再接normal执行/store/replay及current交接。本次没有求解模型，不关闭这些门；`formal_result=false`、`whole_task_resources_verified=false` 保持。

独立只读复核确认probe2的13项bytes/hash、summary→source/observation绑定、PID/creation/root一致及process identity重算匹配；旧22+13+11项也逐项保持。限定证据核验无实质差异，仅为pre-seal复核，不生成official verdict/receipt。

后续开发更新：power/pair binding及prepare整链后继已实现，详见 `rq2_normal_task_inputs_stream_v1.md`。相关140项通过、独立新binder/prepare45项通过；真实H25完整prepare重复重建的资源表现仍待验证，旧执行链保持原样。
