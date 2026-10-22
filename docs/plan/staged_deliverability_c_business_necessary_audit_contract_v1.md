# C公共映射的一小时业务必要条件审计合同

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT。接续[预算交接](continuation_handoff_20261023_budget.md)及[C范围](staged_deliverability_c_scope_and_budget_plan_v1.md)。root为唯一writer；本页是一次独立精确算术审计的输入，成功保存后连同代码和测试保持字节不变。状态更新写新交接。没有production seal、official verdict、receipt或native权限。

固定公共RTS-24方向、两母线机制回归；本包只解析三个已有YAML，不重建网络，也不复用含已编译网络的Fixture.source_identity。public/business/rights原始SHA由runner与主解析器分别校验，交叉检查路径、SHA、工程时点，以及business grid.before/after×200等于对应F+X。独立arithmetic identity还绑定本包五源、两个package入口、旧loader、有界Reader和[B2必要条件语义](../model_spec/staged_deliverability_network_development_v1.md)。业务、设备、清洁及权利参数仍为mechanism_assumption；公共网络来源不赋予其经验数据身份。

## 问题、尺度与公式

一次CLI，40唯一行：on_time/delayed × early/late × h=-2…7，无method维度。h<0为前史8行、h=0…3为登记16行、h=4…7为随访16行；登记期合取只用中间16行。early/late是开发清洁路径，不是业务快慢或独立留出。遵循冻结observe的h<0时f=0；业务设备和电网工程分别按自身时点上线。实际工作量仅用于固定参考策略P0，不替代full-C反事实工作量。

使用Fraction，Δt=1 h，a=γβ>0，w_hat=(C−γP_idle−P_aux)/a，h_hat=max(C−Y/(αΔt),0)；α=0时h_hat=0。输入功率/工作量/电量非负，0≤α,f≤1。原缩放200保持，D=40、P_aux=5、γ=5/4、β=1。只检查零恢复松弛，不计算实际动作、债务、期限或任务轨迹。

三个family分别取q_X=X/a、q_CFE=h_hat/a、q_joint=(X+h_hat)/a。whole-X的necessary_pass保持冻结enrolled-X三条件：w_hat≥0、X≤aD、X≤a·f·w_hat；0≤w_hat−q_X≤K另存为新增假设g=X、无CFE时的设备诊断，不参与原三条件合取。normal及joint则分列保存w_hat≥0、q≥0、q≤D、q≤f·w_hat和0≤w_hat−q≤K。whole-X单项没有CFE义务；normal full-C+CFE固定假设g=0，没有正常网络点证明；joint固定假设g=X，按independent_additive_calls加总两类承诺，不能用max或功率共益抵扣。joint是同时整段X及full-C CFE的假设筛查，事件/时序资格未建立，不声称发生过该调用。

未知网侧g另外保留区间：g_min=max(0,a(w_hat−K)−h_hat)，g_max_business=a·min(D,f·w_hat,w_hat)−h_hat，g_max_with_X=min(X,g_max_business)。负上界不得截成0；非空还要求w_hat≥0。非空仅表示未被该一小时松弛排除，没有选择或推断真实g。g=0因设备活动>K失败可由正g修复，不能把全部g=0失败升级为任意g失败。完整fault业务条件仍未知，没有第四层总合取。

P0=γ(P_idle+βw_actual)+P_aux，保存max(P0−C,0)，仅标识冻结参考策略连接准入筛查，不证明所有策略不可行。normal-C网络点、fault-F点、raw g、139节点、实际轨迹、完整F/X事件及恢复/期限背书、容量释放保持not_evaluated/null。正式/资源准入false。未修改旧aggregate_contract_release；三方法actual比较不以该旧字段转true为前提。

## 完整DAG、上限与停止

1. 普通测试与只读领域/PRE_SEAL审查闭合，再由独立进程核对旧B1–B3/批处理/成本/P1保存绑定。已有记录复用，不重跑科学生成器。
2. 唯一CLI使用文件路径（不是-m包入口），先检查固定root/cwd、-B -s、新repo/parser模块作用域及audit_01不存在，拒绝预加载src/experiments/yaml及其子模块，将repo root置于sys.path首位。本地stdlib读取在任何repo包导入前核对两个package入口及Reader的固定SHA，三次bootstrap read另计、每文件≤2 MiB；随后绑定五源、上下文及三个YAML原始字节。对Reader、主计算器、独立oracle和两个package入口核对实际module.__file__，关键执行函数另核co_filename等于所绑定的repo路径。元数据发现PyYAML 6.0.3的21个选定py/pyd/METADATA/RECORD/WHEEL文件和Python executable，首遍hash后才导入新计算器/独立oracle。不是完整环境seal。
3. 三个YAML主解析一次，40行精确算术；独立oracle再解析同三份原始字节，独立重建40行，用交叉相乘及替代方程逐字段核对，独立按小时集合汇总。总共6次YAML解析、80行算术，无递归/历史重放、无子进程/外部回调、无compiler/model/native/solver、无旧journal writer/reopen。
4. 三个Reader各完整bookend；禁止scientific模块导入，确认P1目录仍不存在。报告所有输入/parser/interpreter的SHA/bytes和阶段wall。仅在自有namespace一次create-only写audit.json并逐字节读回，失败保留已产生文件，后续修复使用successor。没有报告覆盖、清理、自动重试或共享缓存。独立保存后核验同样要求file-path入口及新repo/parser模块作用域，在helper/package导入前以本地stdlib核对bootstrap三源，随后要求精确13项project keyset、PyYAML版本/21选定文件集合及非权威状态，再重新读取全部输入与报告，核对实际导入/函数路径，再跑独立oracle。测试中的publish辅助函数只在pytest tmp使用声明异常，不启动CLI。

每个Reader≤160次read、≤4 MiB，合计≤480次/12 MiB；复用Reader每文件≤2 MiB、每Reader20 s检查。另有固定bootstrap三读/≤6 MiB，其源也在project Reader bookend覆盖。这是显式Reader与bootstrap计数，import机制、metadata发现、OS加载和输出读回不计入该字节/次数账本，不声称系统总IO有此上限。新层整体30 s协作式检查，不是OS硬超时；阻塞系统IO未覆盖，超限报错保留输出。单进程串行，固定40行/两实现；解析单YAML<16 KiB，输出≤1 MiB/一个文件。没有OS RAM硬限或实测RAM承诺，Python/解析器分配和系统加载成本只作为该小型审计开销，不外推公共求解资源。stdout日志和独立保存后核验在外部另存，不混为CLI核心文件。报告时钟截至发布前另标，CLI终态stdout给发布/readback后的wall。

复用安全Reader、仅解析一次主输入、独立oracle不信任主中间值；不能通过缓存掉独立核验来缩预算。新依赖/规模/路径超出本合同即停止另审。此包不是公共native代表性测量，不关闭C整体性能或D/E点数/预算；P1十三源/注册维持native_authorized=false，专项授权仍单独。

## 验收与输出

针对性检查覆盖阶段/窗口、精确缩放、参考与反事实分离、原whole-X三条件与附加设备诊断分离、独立加总反例、未知g区间/负上界、正g修复设备上界、α=0、输入域/浮点/布尔拒绝、重复/合并YAML键、hash drift在解析前拒绝、原输入不变、独立oracle拒绝行/汇总篡改及错误root不写/模块影子路径拒绝。发布窗口包括existing output、并发mkdir、mkdir/open/部分写/短写/readback异常/读回不同/末端wall超限；有输出的失败保留原字节并拒绝同路径重试，没有模拟真实坏盘、掉电或阻塞IO。独立领域手算表和PRE_SEAL findings保存在开发记录；所有40行/汇总必须与独立oracle一致，审计如实保留必要条件的失败，不调D/X制造通过。

输出位于results/tables/staged_rts24_business_necessary_v1_non_authoritative/audit_01/audit.json；外部测试/保存核验/报告/交接分别留档。本页未预写实测时长、通过计数或新gate结论。B1–B3、旧公共build/causal/journal/cost/P1输入结果均只读。
