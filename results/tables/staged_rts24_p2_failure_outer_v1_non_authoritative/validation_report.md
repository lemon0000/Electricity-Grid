# P2失败控制与父端观察保存开发记录

2026-10-23，DRAFT_NONAUTHORITATIVE。接续[成功图会计](../staged_rts24_p2_workflow_accounting_v1_non_authoritative/validation_report.md)，按[本轮合同](../../../docs/plan/staged_deliverability_c_p2_failure_and_outer_contract_v1.md)补失败控制和quiet后父记录保存。只实施普通临时测试与保存字节核验，没有实验attempt或性能测量；公共P2输出与registration继续不存在。

## 新增行为及证据范围

`src/staged_rts24_p2_outer_observation_v1.py`接收预持有canonical context/SHA及supervisor记录，严格检查成功退出、完整历史HANDLE/owner闭包、quiet、固定16384B＋1文件reserve、RSS/Job commit/存储帽。只有这些条件均满足才调用机械检查函数，其他分支只保存父端进程观察。它不启动worker，也不创建注册。

机械返回使用闭合schema：固定scope、nullable SHA、严格计数和bool；worker的full_139/package声明只进入`unverified_worker_claims`。不允许调用方注入科学采用、权限、gate或verdict字段。规范化context/process快照后，父目录与worker目录分离，沿原codec执行create-only pending、fsync、rename与readback，并核目录身份和最后原字节。失败保留phase/expected SHA/may-have-published及已有pending/final，不自动重试。所有独立科学重放/采用、139、F-X、resource/formal标志固定false；worker terminal保持`not_independently_replayed`。

新增两个测试文件，其中P2故障14项、父端观察保存59项。父端覆盖未知quiet/cleanup/close、成员/owner矛盾、1025成员、monitor/RSS/Job/storage/reserve、context/目录漂移、闭合claims与异常、已有target/pending和七个publication阶段及readback故障。所有记录只在pytest tmp产生，仓库内没有真实`parent_observation.json`。

P2单点七种故障使用FakeApi及原point_worker/transport：nonoptimal/warning为numeric unresolved，其余getter、CAS、raw发布和log故障为transport unresolved；永久占1 reservation、0 imported、不重试。它们不创建真实Highs实例。

P2晚期控制测试运行原worker与full_contracts，但**预置41个actual计数、10个接受槽和10条替代记录**，并显式替代journal、Cursor/transport、audit及fresh。实际推进的是278个合同控制槽。69个label共享同一解析branch形状，不是69个公共事故。最后raw319数值未决得到319 reserved／318 imported／137完整合同行，允许finish→fresh→parent reopen替代路径保存不完整report；transport异常则不finish、不保存内存合同行、不fresh或report。全部合同控制成功为319／319／138行；fresh exit/timeout/quiet失败保留替代terminal marker、合同和trusted binding，父reopen未执行；metrics失败已调用替代parent reopen，仍不发布report。替代monitor在故障路径也先写fresh.json，不能据此推断真实失败必有可用fresh结果。原fresh_worker的reopen拒绝回归确认不发布fresh.json。

## 失败矩阵与成本边界

完整矩阵见合同。最晚journal.begin_step在参考取证后40槽（31 reference/recovery＋9 actual），接受9小时；取证前Cursor.begin_hour仅37槽。commit到41槽仍可能存在第10小时发布未知；terminal在319／319后失败时138行也可能尚未落盘。这些位置由原执行顺序及既有journal组件证据支持，本轮没有新增公共P2 begin/commit/terminal失败观测。

319成功图不界定失败wall。数值未决可花满单点帽及fresh；transport、CAS/pending、清理、关闭、父扫描和发布也有独立尾部。十小时CAS/摘要、真实native/getter失败、完整outer尾部与IO阻塞成本仍未知。fresh60s＋5s收束对outer65s没有父端余量证据，帽未改。普通测试耗时不纳入P2预算。

## 检查与保全

最终针对性检查[units_04](development_checks_01/units_04.exit.json)为73 passed，exit0，四输入首尾pins相同。首轮units_01的45 pass／5 fail是替代session缺两个状态字段，修正fixture后units_02为50 pass；独立审查后闭合claims和固定reserve，units_03/04为73 pass。历史失败stdout/stderr及源码pins均保留，不并入最终通过数。

相关回归[related_02](development_checks_01/related_02.exit.json)为35 passed／6 deselected，exit0；终态计数见[保存核验](postcheck_01/related_check_summary.json)。首个组合在120s wrapper上限停止，没有终态通过结论；其进度点不计通过。后继缩小journal选择，保留guard、未决/terminal及P2控制回归，未更改旧测试或放宽原组件限值。最终两组外部wall分别9.619194s与84.671502s，仅为普通检查耗时。

独立PRE_SEAL审查的两项Medium分别为任意claims可混入权限声明、reserve可伪造为零，现已修复并加反例；40槽措辞也已澄清。记录见[findings](development_checks_01/prereview_01.json)，仅为开发审查，无official verdict、seal或receipt。

[stdlib-only postcheck](postcheck_01/postcheck.py)验证四输入、17个冻结依赖、400条旧发布路径及原P1/上一轮会计postcheck stdout精确复现。原P1683文件、B1–B3118保存文件和685个前序检查点路径保持。原P2七输入、prepared packet、journal/codec/backend及历史失败字节保持；三个导航文档只添加新检查点并保留旧尾部。

## 后续依赖

当前交付只是观察记录保存组件。完整outer还需实际注册/packet/55＋7＋outer来源、exe/argv/cwd/root/limits绑定及首尾核验；quiet后completion core、manifest外白名单、全目录库存书挡、319点和138合同行/接受state、fresh/父metrics检查。科学采用需另由受控fresh独立重审全部raw→snapshot/KKT/point/合法X与journal，不可直接采用worker声明。

之后补完整成功/昂贵失败/尾部的代表性有界成本、十小时存储增长及稳定包资源审查；新native仍需具体登记和专项授权。RTS-24主比较、两母线机制回归保持；139数值/F-X时序、C整体、D/E现实输入/选择/敏感性/时域/留出和总预算继续OPEN。原P1一次native授权已用。
