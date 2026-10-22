# H1 phase-boundary preparation continuation / 2026-10-21

用户持续目标：把正式实验前的准备都做完，准备开始正式实验。当前推进E168/F≤24阶段边界和episode终结，先完整性能/预算，复用保存证据。goal仍active，未完成。仓库为 `D:/CUHKSZ/Research Project/electricity-grid`，PowerShell，Python `D:/Miniconda3/envs/compute/python.exe -B`。

先核Git/进程、AGENTS.md与agent.md适用段；当前R3/root唯一writer、既有phase_budget_review仅PRE_SEAL只读审查。原canonical plan/blocker被旧950包绑定，保持当前字节；新状态在本versioned non-authoritative目录。没有正式seal/official receipt/native/长链运行授权。本轮未改source/helper/owner/config，也没有Git commit/push。

## 当前入口

- [验收记录](acceptance_report.md)
- [whole-workflow budget v8](whole_workflow_budget_v8.json)
- [formal preparation state v8](formal_preparation_state_v8.json)
- [source adoption decision v4](source_adoption_decision_v4.json)
- [九个枚举故障的组合核对](combination_postcheck.json)
- [已有M232资料fresh hash复用](saved_M232_evidence_reuse_v1.json)
- [最终绑定](final_verification.json)

## 实际终态和保留失败

suite_01原9个cases前8 accepted，第9在总240s的下一采样点suite241.344s停止，含清理outer241.812s、exit1。最后case仅34.8s，无worker terminal；FileNotFoundError为停止后读缺失终态的次生错误。仅已观测PID/create-time进程被清理；无目标故障、Reader finally或hooks/guard恢复证据。不得改写该套件为9/9或exit0。

另登记remaining_01，只补第9，保持原per-case90s、总90s，其余限额不变，使用exact v1 worker SHA `413eed58eec7bbeabdcce68465c9899d0b4d4da068a50f9526e455a79c5ebaaa`。remaining_01 outer47.125s、case46.796s、worker42.670941s，exit0。第三namespace round的第一个root/第7root inventory返回值seam由原_inventory拒绝，injection=1，2 Job/10 stage/1正常after，实际inner/outer cleanup及hooks/guard恢复、465文件SHA相同、观测PID尾部为空。

前8与此项组成9个枚举保存M5单Reader故障覆盖，accepted实际合计10Job/50stage/5正常after。被终止原case实际计数仍未知。sampled RSS分别197337088和203472896B；两attempt已花wall288.937s，不是生产性能上界。全部0新normal Job/selector/native solver；sharing case有非求解器Win32 API。

support_04为16 passed/0.30s，6份tested源前后未变。原294 unit与H3双Reader证据按上游2483绑定复用。原suite2492、remaining2584启动pins fresh均匹配。只读reviewer已逐case核查，没有新具体finding，仅PRE_SEAL。

故障覆盖保持有限：五constructor早拒、postconstructor、真实只读sharing conflict(32→Python errno13)、H2未选中packet0内存反射、namespace返回值seam。ReadViews不是OS writer lease；只检查capture和3种显式清空容器。不存在全文件并发/任意反射/ABA/完整动态闭包/双Reader prepare_many失败/owner/H192覆盖。trace直接raise会停trace，独立profile负责cleanup观察，保留exact实现。

## 预算和科学边界

v8继承v7调用量，source v3未被owner采用、无折扣。T192 clean W0 terminal路径773batches/1546Readers/P149380；基线597520Job、条件M232138624640stage；未采用v3为298760Job/69312320stage，并保留allH149380、fullpacketdigest298760、显式model154018、guard23963、root listings13914等额外成本。静态数量不等于native solve数。clean paired575+terminal1=576 events，requires needs_next_hour=false；不能覆盖所有witness/failure，旧operational cap32不足。

已有M232旧单小时校准251文件/20938085B fresh SHA相同，旧232 reports和2744.984s只属历史单小时。native_execution_authenticated/optimality_certified/whole_task_resources_verified均false；没有重新运行、读取SQLite replay或模型装配。zero-solver shape只测端点0/231且placeholder locks；future shape1272>旧1211反例不是可达科学见证。不能由这些资料宣布v3 M232/192 retention通过。

全部16 gates false，totalwall/RSS/storage admission null，source adoption/long launch/formal ready/full192/native authority false。E=168、F≤24、nonrolling recover_then_check、primary births只在enrollment、followup births/debt保留、所需缺源诚实U/right-censoring、q=g+c≤f*w及q+r≤D合同保持。原connected03仍仅3h/7paired lane-hours，h1 Actual timeout+incumbent仍actual_unresolved，缺h3 source无第4Job。旧target business192h参数overlay并非authenticated source-connected链。

## 紧接着做

1. fresh核本包final bindings、process/Git和未解决gate，不再重跑已完成九项/H3/connected03/chain07/target cost01。
2. 基于已有M232资料和v3代码，固定有界source applicability/full-packet retention/namespace规模诊断问题、次数、全路径成本与停止条件。不要用未验证的future carry构造来源证据。需要新的真实native校准时先具体登记并取得专项授权。
3. 冻结适用source及两Reader失败窗口验收后，做versioned owner接线/完整net-cost、failure/terminal/reopen和writer crash证据，再连接E168→followup→episode terminal。实际总预算未成立前不开新的长链。
4. 继续完成其余formal准备门。agent§4旧46cells与approved finite-v2 1900cells的authority同步、具体sealed科研包、新独立official review及具体正式运行权限分别处理，不能由local测试或本包推导。

旧工件及失败保持。新实现只在独立DRAFT successor，后续official reviewer必须是新的实例和独立上下文。完整工作区仍含先前未提交研究成果，禁止revert/delete无关文件。
