# 168h / 至多24h phase 边界：预算审计与有界验证

2026-10-20，DRAFT_NONAUTHORITATIVE。唯一 writer 为主代理；独立只读 PRE_SEAL 审查按 agent.md §7 执行。原 hour0、两小时、三小时链、失败现场及冻结合同保持保存。当前任务先审计整链预算，再开展不依赖新长链的科学边界单元验证。

## 本轮执行边界

目标长链为原 E=168、F<=24：normal N → 共同 Rref → active Actual → paired business/actual → 额外 terminal operation → 外部 checkpoint → clean close → fresh constructor → public inspect → 独立 historical/snapshot → 原件 SHA/句柄/进程及报告。缺必要 follow-up source 是另一个失败分支；当前实现只留下 pending attempt，不提供 typed right-censoring terminal。

当前审计明确拒绝启动该长链。3h 实测无法界定192h总 wall/RSS/storage，原32-event toy manifest也容纳不下真实边界。新的资源配置、增量验证合同和长链代表性性能证据必须先闭合；本文件不赋予运行权限。

本轮只执行标准库只读预算审计及一包新单元测试。测试使用原 fixture 从业务 genesis 构造全部168/192小时 BusinessCarry，再调用原 phase assessment/body；源、normal、Rref/Actual credential、持久paired journal均不由这些业务事实建立。phase-body的heads/binding为显式测试元数据，不进入任何存储或producer。E/F、due、预算会计期与科学验收限不变。

单元包固定：一次 invocation，最多180s wall、采样RSS 1GiB、输出逻辑存储128MiB，串行、0 Jobs/native/外部下载。每2s记录wall/RSS/storage；30s心跳，CPU或文件活动仅为活动观测，不能顺延wall。超过wall/RSS/storage即终止本包owned子进程、保存非零终态与全部失败原件，不自动重跑。pytest正常结束也读取退出码、JUnit、事实JSON、source SHA与观察PID；不是启动即通过。

unit_01在0.891s、测试收集前被过严的“任意child均拒绝”监视终止，exit15、1304 pins未变、两PID退出。30s上限的collection_probe_01在22.579s exit0，确认唯一child是Windows System32/conhost.exe控制台helper，14项测试已收集、未执行fixture/body。监视改为只允许该可核身份的直接child，保存路径/命令/parent/create_time，其他child仍拒绝。unit_02沿用180s/1GiB/128MiB；首失败原件保持。此修正仅涉及Windows启动监视，没有改科学门槛。

unit_02在96.719s exit1，5项计数/限制测试通过、9项phase body测试因测试SourceBinding使用相对root被原absolute-root门拒绝；无超限、pins无漂移、观察PID均退出。仅将测试元数据改为绝对拼写，不创建root；原门不改。unit_03沿用180s/1GiB/128MiB，并加一次真实192小时due-endpoint测试，验证最后小时恢复后deadline snapshot为0；相对本包96.719s加单192小时业务路径预计仍在180s内，超限即保存失败。终态现在解析预期15项JUnit零failure/error/skip及9份精确事实JSON/hash，旧两次失败原件保留。conhost gate核exe路径和direct parent，命令行仅留痕。此包仍是短单元验证，不是完整N/Rref/Actual或source预算。

## 可复用边界

三小时启动1299 pins、继承1279 pins、444 owned files、465 case files和终态报告绑定须在本轮只读重算SHA。匹配后复用36+23 guards、unit06、旧hour0/两小时/三小时主体及postcheck，不重跑。原 follow-up/phase-owner unit报告仅按精确实现/test/config pins及原作用域复用；历史报告含已被successor改变的bytes时只保留其历史意义。

不得从coverage报告、分离BusinessCarry、旧ticket或待认证journal推断外部expected heads。normal writer关闭后不能adopt原root继续写；重叠source hour只有完整起点、初态和允许输入相同才具备复用条件。动态Current、source、registry、业务或物理carry不跨operation缓存。新的增量方案须独立DRAFT successor证明依赖闭包、freshness、失效/异常/并发窗口和逐小时科学等价。

## 完整调用量与成本缺口

原v2每个成功小时有ready full replay、独立current、paired前独立fresh及post-paired full replay四次batch；每batch两次独立Reader，每Reader的constructor+explicit inspect又有两次parent全遍历。成功T小时加create/reopen constructor时，Reader数=8T+4、prefix-hour权重=4+4T(T+1)。额外terminal的ready/post及reopen后public inspect再增加6个Reader/6T权重。因此完整终结路径为8T+10、4T²+10T+4；parent遍历和其权重各再乘2。独立historical、snapshot、anchor、normal内部、源预验证与失败/回调未由这一层计数涵盖。

业务成本比上述源层权重更高：每次h-outcome owner replay，每active lane的prepare及post-assess、intent/attempt need checks、尾部assessment传入_validate的历史长度合计2h²。仅T次成功run_next的ready+post重放，L条始终active/paired lane已至少产生2L*Σ[h²+(h+1)²]个历史长度单位。cursor.__post_init__、历史编码和live/terminal/重开另加成本，不能当wall估计。失败lane/提前completed需逐lane重新计数，不把三小时实际7lane-hour当成9个。

成功T小时有2+(T-1)*3个事件，额外terminal后为3T；168h需504，192h需576。现toy max_events=32，完成10h后下一小时的四事件branch reservation因29+4>32拒绝。扩大max_events也不能代替owner/holder事件字节、整库、normal档案和总RAM/storage的预算证明。

可直接复用的优化是已绑定旧结果、静态代码身份fixture及已通过的batch v2；fixture没有测生产静态开销。进一步动态跨operation缓存尚无闭包证明；独立任务并行也不能绕过同一N/Rref/owner串行依赖，不能用并行掩盖单链无预算。优先项为versioned owner/business增量验证与一次operation内部重放复用，逐小时对照原实现；验等和性能代表性不足时不采用。

三小时wall1314.969s、峰值RSS403148800B、logical23223898B，单Reader33.283s、双Reader batch65.255s均只保留原作用域。normal每Job240s、每小时selector13s的deadline和是阶段停止额度，未覆盖重放/提交/关闭，不构成整链ETA。真实RTS正常232 stages/h、192h 44544 slots也不是本toy实测。目标长链wall/RSS/storage仍null，overall_performance_review_complete=false。
