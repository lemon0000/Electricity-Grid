# 正常计划审计与单小时网络信息隔离

日期：2026-09-16。状态：DRAFT_NONAUTHORITATIVE。
实现`grid_information.py`，测试`test_rq2_grid_information_v1.py`；本组件不调用solver。

## 入口与机制声明

审计侧入口接受`ContinuousNormalInputs`、完整canonical正常赋值、预存normal input identity，以及显式
`PlanInformationDeclaration`。复制输入后复用`audit_normal_assignment`，只在无错误且有terminal carry时产生输出。
没有从`ContinuousGridCandidate`提取未来事件或逐小时corrective结果的入口。

本DRAFT要求调用方显式声明：给定正常输入作为episode前已给定的完整确定性benchmark预测；normal schedule
在首个动作前固定。`issued_at_source_hour`不得晚于incoming carry的source hour。这是mechanism assumption，
不提供真实预测或发布时间证据，也没有注册正式实验的perfect-forecast信息集。

事前输入白名单包含normal SCUC实际使用的逐时timestamp、逐bus负荷、逐机组min/max（含可再生边界）、
逐area spin-up reserve requirement、DC baseline/physical/connected上限、数值初态、静态网络及规划参数。
初态source_scope、raw source hash、trajectory label、outage seed均留在审计侧。
备用资格使用的机组category与10分钟备用限额使用的ramp_mw_per_minute也进入allowed身份；
不能仅绑定小时ramp而遗漏正常计划的备用边界。

## 双层身份与视图

`PreparedNormalInformation.audit_identity`绑定normal原输入、完整assignment witness及本模块实现SHA。
它不是策略输入；其中的terminal carry仍含原来源身份，应仅留在审计侧。

`allowed_plan_identity`从白名单预测、数值初态、静态网络/规划参数、显式机制声明、全时段正常commitment与
generation重新计算，不散列或截短原input/candidate/source identity。它可以包含声明已在origin给定的未来预测信息，
不能包含尚未揭示的未来actual report或事故表。改变事前预测可改变这一identity，这不等于隐藏未来actual的前缀不变性失败。

每个`NormalHourView`只携带当前source hour/timestamp、当小时generation/commitment、上小时planned commitment、
信息声明和allowed plan identity。第一小时prior commitment来自固定初态。非committable机组保留静态enabled语义。
source/normal assignment/full audit身份、原始hourly_points与未来事件不进入此视图。

`current_grid_information`在审计侧核对预存audit identity及实现SHA，匹配当前小时后输出`CurrentGridInformation`：
静态网络、一个normal hour、独立当前条件及contract。所有准备结果与视图禁止普通构造和dataclasses.replace。
其visible identity只绑定可见内容；没有指向完整来源或envelope的对象引用。

身份是内容绑定，不是签名或Python反射安全边界。该接口不提供跨进程导入或origin前immutable receipt。

## 当前条件独立提供

`CurrentGridConditions`显式提供当前source hour/timestamp、完整逐bus需求、逐机组min/max/base availability、
DC baseline/physical/connected容量和mechanism角色。当前值不会从normal预测自动复制。
输入要求有限非负、完整唯一排序inventory、上下界一致，generator上界不得超nameplate，committable下界不得低于
静态minimum；DC baseline不得超过physical/connected上限。不能用base availability启用静态disabled机组。

当小时base availability与plan commitment分别保存；N-1 outage overlay仍由`event_disclosure.py`另行提供。
实际prior generation/availability、故障/repair响应、节点方程与恢复功率需后续单步模型组合验证。
本组件不对当前条件求解，因此当前条件可与正常预测不一致，也不声称存在对应网络可行赋值。
静态投影保留原continuous branch rating、tap/reactance、DC上下界、机组nameplate/ramp；未新增或放宽物理限额。

## 非预见性与未完成项

完整normal赋值可能由调用方在看过未来事故后选择，即使它通过canonical审计，也可能通过多解选择编码未来。
当前声明不排除这种选择机制；因此`causal_certificate=None`、`formal_result=False`。
正式升级需要origin前不可变发布证据，或只依赖注册allowed forecast的确定性normal求解/选择规则及相应反例验证。
当前组件不认证solver来源、最优性、实际预测来源、grid request、DC/AC安全或完整服务容量。

后续单步kernel只能接收隔离后的视图、当前overlay与已验actual carry；不能把prepared envelope传入决策函数。
request含义、CFE credit、实时reserve范围、紧急启停、非唯一解选择及失败状态仍按因果合同登记，未代选正式协议。

## 验证

36项新测试随四文件179项相关回归通过（16.36s），独立pre-seal另复跑36项通过（3.60s），限定范围无开放实质finding。
命令使用`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`，文件为
`test_rq2_grid_information_v1.py`、`test_rq2_event_disclosure_v1.py`、`test_rq2_continuous_grid_normal_v1.py`、
`test_rq2_continuous_grid_carry_v1.py`。新模块和新测试不调用solver；既有normal测试保留其原微型求解。
源码SHA256：`957af693018cd99aefa2d32bc599a1482d81cbc8cba05d686266393f9d38d69e`；
测试SHA256：`5de4b819b2cc4bf1cb22f80041cf6b2d9df42515aa6b6309b07291b88eaa729e`。
直接覆盖：seed/provenance只改变audit身份；normal reserve/angle/flow改变而commit/gen不变时allowed视图不变；
事前forecast改变可改变allowed身份；当前报告偏离forecast仍分别保存；actual未来后缀不改变先前视图；
首小时prior索引、分块投影、非法完整赋值、越界当前输入、owned输出、caller后续修改与contract漂移。

继承的构模边界：一机合成输入若将唯一机组category改为无备用资格，旧SCUC在区域空备用集合上产生
trivial Boolean constraint错误。该输入当前不受既有normal backend支持，新负例要求本入口原样失败且不产生视图。
没有把构模错误当作数学不可行或调整备用约束；如后续实际输入出现该情况，须先修复并验证相应backend successor。

下一项为当前信息下固定业务功率的单小时网络可行性及actual carry递推，随后才按明确的请求语义接request generator。
