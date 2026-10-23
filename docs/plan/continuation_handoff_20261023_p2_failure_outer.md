# C：P2失败控制与父端观察保存交接

2026-10-23，DRAFT_NONAUTHORITATIVE；目标“推进计划”保持active。接续[成功图会计](continuation_handoff_20261023_p2_accounting.md)，起始HEAD/origin为4a9139204d9226d232ca4877cb3cb1db8e15c2eb；实际发布状态以随后remote readback和worktree核验为准。

## 本轮进展

按[本轮合同](staged_deliverability_c_p2_failure_and_outer_contract_v1.md)固定昂贵失败矩阵：最后raw319数值未决为319 reserved／318 imported／137合同行；transport不保存内存行、不finish/fresh/report。全部合同控制成功为319／319／138行，fresh失败止于父reopen前，metrics失败不发布report。最晚journal begin为40槽、接受9小时；Cursor begin为37槽，commit未知与terminal失败分别处理。详细证据及范围见[报告](../../results/tables/staged_rts24_p2_failure_outer_v1_non_authoritative/validation_report.md)。

新增父端观察记录保存组件，预持有canonical context/SHA，严格核完整Job成员/HANDLE/owner及成功quiet、固定16KiB＋1文件reserve和proposal帽。闭合mechanical claims将worker声明单列未验证；父目录独立并沿原codec pending→fsync→rename→readback，保存publication未决而不覆盖重试。组件没有spawn、生产注册或科学采用接口，不是完整outer。

最终73项针对性检查通过（14个P2故障、59个观察/发布），35项相关回归通过／6 deselected；首轮fixture的5失败和120s组合超时均保留。FakeApi单点走原P2接口；晚期worker测试预置actual计数/接受记录，以278合同槽、同branch的69label及journal/audit/fresh替代件覆盖控制流，不证明实际十小时或69公共事故。所有进程观察只在pytest tmp保存。

PRE_SEAL两项Medium已闭合：任意机械claims改为闭合schema，terminal reserve要求精确16384B。独立保存核验复现原P1和会计postcheck stdout，400旧发布路径、P1/B1–B3/685与冻结依赖保持。没有新P2目录、registration、native或长实验；source-freshness/科学replay/adoption/独立139/resource/formal固定false。

## 下一实质步骤

以现有保存原语开发完整outer的纯机械包检查层：实际注册SHA、packet与55＋7＋outer来源、exe/argv/cwd/limits/root身份；quiet后completion core＋六项manifest外白名单＋全库存书挡、319引用/138行/接受state、fresh/父metrics。kernel注册是闭合schema，outer绑定须独立，不向原注册加键；原P2七输入、prepared packet与历史字节不可改。worker claims只能保留为未验证声明。

独立科学采用另层以受控fresh重审全部raw/KKT/point/合法X与journal。尾部父保存成本、昂贵失败、十小时CAS/摘要及完整wall仍需代表性有界证据；fresh60s＋最多5s收束对65s无进展没有父端余量，不能沿用成功点数或P1墙钟外推预算。完成稳定包、资源和独立审查后，新native仍需专项授权，原P1一次授权已经使用。

RTS-24主比较/两母线机制、原P1五小时missing_input/coveragefalse/双null保持；139/F-X时序、C整体与D/E现实输入/选择/敏感性/时域/独立留出和预算OPEN。恢复读AGENTS、agent第7–9节、本页、C计划及blocker；刷新Git/进程。root唯一writer，子代理只读不分叉，按精确NUL范围、原字节和远端hash同步Git。
