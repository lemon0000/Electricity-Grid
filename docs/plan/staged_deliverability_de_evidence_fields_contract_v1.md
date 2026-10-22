# D/E开发字段与保存报告投影合同

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT。接续[C业务必要条件交接](continuation_handoff_20261023_business.md)，复用[A规格](../model_spec/staged_deliverability_minimum_spec_v1.md)与[原D/E顺序](staged_deliverability_b3_c_next_steps_v1.md)。root唯一writer；本包只实施开发字段和已有报告的只读投影，不创建D/E正式预注册、候选seal、freeze/receipt或运行权限。成功保存后五项新源保持字节；修复另建successor，当前状态写新交接。

## 保留的D/E范围及缺口

D仍为每一业务情景内的少量给定计划比较：业务快/慢×电网按期/延期×瞬时MW/固定恢复余量/完整时序。12只是分类槽，既非12个已定义数值方案，也非执行数或预算；cost报告恰有12个保存case，与它们没有映射。fast/slow任务数值、最终设备/工程清单、D点与选择/排序/平局规则、主时域/尾观察、必要敏感性轴与水平和总资源未定，所有对应值null，public_main_executed_cells为空。

同一业务情景内各计划共享任务到达/工作量/可延期比例/期限、外部Y、核算/服务规则、安全标准和功耗映射；设备安排差异与电网安排差异分别保存，K和待机同步变化。不同快慢业务不能归因为纯建设效应。方法共享请求生成规则；受历史动作影响时，从自己的连续物理状态生成g，不能强制复制相同g。简化安排仍需在完整约束回放，保留简化占优、无差异、失败和未知。

原文最具体的敏感性义务是：相同网络状态和q_req下改变清洁恢复额度到达时间，以支持恢复时序归因；g或即时工作变化则差异来源分列。R_fix与eta须在目标结果前固定；没有据此挑选新数值网格。当前early/late是清洁开发路径，不是快慢业务或holdout。

E要在选择给定计划、D和固定运行策略后，冻结相应输入与规则，再独立揭示留出并因果执行。当前未选择方案，也未定义留出来源、split、数量、seed/采样、事件、工程揭示、清洁/任务轨迹、末端期限覆盖或是否重评三方法；保持not_defined/null，不创建看似有效的空freeze对象。未来事件记录必须区分scenario_truth、policy_observation、reveal_hour、observation_source_ref，不能把全事件真值当作当时可见历史。本包不访问留出输入、不执行选择或冻结。

## 四层和终结字段

逐时字段分identity/information、resources、actions、service、carry五组，具体机器字段见新core.development_design；对应A规格§7的plan/path/stage/hour，K/w/F/X/D、设备工程状态、P0/完整g/h、承诺分配/q/r/z/实际P、Y/y、两类服务缺口与实际CFE缺口、网络点、任务债务期限、两类事件预算及信息历史身份。这里登记未来记录义务，没有声称当前投影已补齐逐时点。

四层分别保存actual条件轨迹、完整静态F/X网络、局部业务必要条件、完整反事实F/X跨时支持。本包公共部分仅投影原40行必要条件及其premises；通过只表示not_ruled_out_by_this_necessary_screen，false表示该必要条件失败。其余三层明确status=not_evaluated/value=null/reason，容量释放null。实际g、网络点、139节点和完整时序不能从三母线或必要条件填入。

科学终态、发布结果、状态确定性、adoption证据、覆盖、已观察违规、右删失、未接受当期和未观察未来各自保留，不压成一个pass。12分类槽另显式登记method_conditions_satisfied与full_replay_conditions_satisfied两个结论，以及mathematical_infeasibility_inferred和stop_reason，当前均null；未来不能用一个通用result吞掉原方法判断与完整回放判断，也不能把未决/拒绝自动升级为数学不可行。complete只表示保存的终态类别，不等于履约；尾债为零不擦除到期逾期；null、false与字段缺失三分。summary.unapplied_attempts、journal unaccepted_attempt及writer failure诊断不合并为同一种任务。

投影逐字段复制原summary/独立audit/未接受状态等，排除大体量state和嵌套writer_inspection，后者只摘其原始指定诊断字段；若原inspection为null则writer_observation保留null，writer_failure缺失时仍缺失。cost writer_binding、writer_failure（normalized_failure原字段）与保存的fresh_result分开；writer unknown不被后续reader committed覆盖，writer_fresh_resolution保持null，本包不作新裁决。deletion reader拒绝没有summary，不补空任务或零指标。每项附原报告path/SHA/bytes/JSON pointer；20个三母线保存视图是复用轨迹的机制回归，不是20个独立样本、公共D单元或新数值审计。

## 一次有界投影的完整路径

五新源：core、CLI、测试、本合同和[独立来源核验器](../../results/tables/staged_deliverability_evaluation_records_v1_non_authoritative/postcheck.py)。输入为三个固定SHA的既有report：journal_v1的32952 B、append-cost的408939 B和公共business audit的62933 B；另绑定两份原规格与只读Reader。只信任已保存报告字节及声明解释，不沿其CAS解析或reopen；当前组件是saved_report_projection_not_new_numeric_audit，不升级原authority，也不重新验证原数值模型。代码绑定输入SHA/规模后才能执行，不按输出筛选旧case。

1. 普通测试和只读R3 PRE_SEAL审查闭合，保存旧绑定核验。refresh Git/进程，P1 attempt必须不存在。
2. 固定root/cwd、文件路径CLI、-B -s及create-only projection_01；本地stdlib安全读取固定SHA Reader（bootstrap一次<64 KiB），以compile/exec执行刚读回的确切字节，不通过包或.pyc导入。Reader首遍读取五源、helper、三report和两spec（11个repo输入），另读取executable一个选定环境pin。不是完整environment seal。
3. 核验核心输入原字节后同样compile/exec新core，仅依赖stdlib copy/hashlib/json。每个报告一次JSON解析，原3success+5failure及cost12case共20视图、公共local40行和12未绑定分类槽；没有业务动作生成、算术必要条件重算、CAS解码、journal reopen、fresh子进程、外部回调或solver/native/model/compiler调用。
4. Repo和executable输入完整bookend，检查无scientific/parser模块、P1不存在，输出来源pins、阶段wall及显式读计数。一次create-only写projection.json并字节读回；已产生的部分文件/目录失败后保留，拒绝同路径重试，无自动清理或回滚。结束后独立保存核验从原JSON pointer重核全部投影字段，不调用project；开发蓝图按独立完整expected逐层核所有key和值，包括匹配规则、逐时/终态字段、四层、敏感性、holdout访问及空预算；再按pins算术核对24次Reader/字节与bootstrap，最后核旧绑定。

本包串行单进程，实际路径固定24次Reader读（11repo+1exe各首尾一次），另1次bootstrap；保护上限40次Reader/4 MiB（逐Reader预检查并合计后核）、单文件Reader≤2 MiB、bootstrap<64 KiB、输出≤1 MiB一个核心文件、body wall20 s协作式检查。Python启动/stdlib加载不在函数体时钟，metadata IO以外的import/OS加载/输出读回不计入Reader账本；无OS RAM硬限或实测承诺，真实阻塞IO/坏盘/掉电不覆盖。这是静态元数据工具预算，不作公共网络性能代表，不关闭C整体或D/E资源准入。独立postcheck以自身stdlib读取器另限50次/6 MiB、body20 s，重核报告、五源及选定环境首尾；它的直接pointer比较不调用投影函数，且自身源已被CLI绑定。

优化采用一次解析并保留来源直接视图，避免重构全部state/CAS或重复科学计算；bookend与来源对应核验不可缓存掉。不使用旧运行wall估公共成本。改变inputs/fields/规模/路径需successor重审，P1专项授权继续独立。

## 验收

检查必须覆盖：complete+zero debt仍miss40；简化方法true但full replay false；缺未来/censor/debt40与null条件；未接受当期observation不生成已接受任务；writer unknown/fresh known并列；reader拒绝不补summary；每条pointer+SHA+bytes和原字段对应；public未评价层不入通过数；cost12与design12不连；holdout/敏感性未定；源绑定、确切源字节执行及create-only并发/读写/末端wall失败保留。普通回归按相关范围执行，记录真实日志，不重复累计迭代测试数。

输出位于results/tables/staged_deliverability_evaluation_records_v1_non_authoritative。验证报告和新交接随后保存，只有实际完成才更新导航。公共数值与代表成本仍依赖P1专项授权；原B1–B3、public build、journal/cost/business审计和P1绑定均只读。
