# C：P2输入核验成本交接

2026-10-23，DRAFT_NONAUTHORITATIVE，目标“推进计划”继续active。接续[P2内部执行器](continuation_handoff_20261023_p2_runner.md)，起始HEAD/origin为ad2325a246c4f464e5135ad6f6c764fe30a87b85。本检查点发布以远端readback与最终clean worktree为准。

## 当前实质进展

按[新诊断合同](staged_deliverability_c_p2_input_cost_contract_v1.md)完成唯一无solver measure_01。原p2.fingerprints/load_packet(False)/preserve各一次，profile wall分别0.6391264/0.0027545/1.4016708s；旧fingerprints/preserve各嵌套一次，没有另行测。命令exit0/wall7.1231711s、Job4.640s、RSS151965696B、2/2历史成员HANDLE signaled/active0/quiet，未超停止帽，无重试。完整16文件493559B，0 native/模型/重放。

[报告](../../results/tables/staged_rts24_p2_input_cost_v1_non_authoritative/validation_report.md)解释：fingerprints主要累计热点为原Distribution.files/存在性枚举，preserve主要为历史stamp/open/read；packet本次很小。准备工件子路径2525843B/14逻辑读取是结构计数。warm imports、固定顺序、单次cProfile只定位本次成本，不能形成提速、P2 ETA或资源准入，命令/Job/profile差额未归因。

66来源、39应用模块/33选定函数、1929加载模块书挡相同；三个原返回值等价、raw profile目标各1/1、38禁止项零、观察器恢复、八事件和quiet后输出采用闭合。33针对性/68相关普通检查通过；built-in _lsprof的早期失败及旧证据保留，case动态入口明确预热。PRE_SEAL实现与实际保存包无剩余High/Medium，没有official verdict/receipt/seal。

stdlib-only[后核验](../../results/tables/staged_rts24_p2_input_cost_v1_non_authoritative/postcheck_01/postcheck.py)确认：原P1683文件2950863B、B1–B3118/685前序路径及294前次发布路径保持；原P1/准备/P2runner三个postcheck stdout逐字节复现。测量源/合同/测试已被start和最终检查绑定，今后不改这些字节；优化进入后继。P2公共目录和执行registration仍不存在。

## 下一实质工作

先写版本化核验复用合同，逐对象说明来源、缓存范围、失效/漂移窗口、最终采用与失败可观测性，并以普通临时文件/模块反例验证；之后才实现后继。Distribution.files提前过滤或跨窗口缓存会改变存在性/PermissionError语义，不能沿用等价主张。packet、context55、P2七源与legacy runtime各自身份须保持可追溯。原P2 v1和本次measure保持，本次没有优化接线。

再补outer launcher/quiet采用及新执行注册开发；65s无进展与fresh60s＋5s收束仍缺父端保存余量，内部条件成功路径load_packet960/fingerprints1281/preserve3、准备工件2345752302B尚非实际成本。journal请求构造、prefix重审、十小时存储增长及昂贵失败的完整DAG/预算仍缺，不能据本表时间线性外推。完成具体稳定包和审查后，新的native仍须专项授权，原P1唯一授权已使用。

RTS-24主比较、两母线机制回归保持。P1仅五模拟小时missing_input/coveragefalse、method/full双null；十小时P2/139数值/完整F-X时序、C整体性能及D/E现实输入、选择/平局/敏感性/时域、独立留出来源/split/seed/reveal均OPEN。恢复先读AGENTS、agent第7–9节、本页、C计划和blocker，刷新Git/进程；root唯一writer、子代理只读不分叉。精确NUL范围及raw/index bytes核验后同步Git，远端hash与clean worktree为发布凭据。
