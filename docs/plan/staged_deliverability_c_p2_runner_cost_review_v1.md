# C：具体P2 worker的结构成本与剩余准入

2026-10-23，DRAFT_NONAUTHORITATIVE。接续[执行器开发合同](staged_deliverability_c_p2_runner_development_contract_v1.md)。以下从具体源码核算条件满成功的内部worker路径，不是已执行P2、整体资源准入或时长预测。新执行注册及outer launcher尚未创建；未来注册构造、完整准入、outer Job与quiet后采用必须另计。

## 当前实际接线

内部worker CLI轻核注册→新执行pins/历史字节→固定packet完整验证→Cursor→原journal actual十小时→h1/2合同→原finish→顺序fresh子进程→父端原reopen/metrics→观测与completion。逐点为Cursor槽/父/接受门→永久reservation→parent compile/CAS/request→point子进程轻核注册与依赖→worker compile/native/import→quiet后parent raw重导入→父端依赖书挡→Cursor证据族采用。transport/所有权未知停止依赖，已知数值未决保留较短前缀；通用失败不否认可能已有terminal。

原Win32 Owner、1GiB进程commit/Job2GiB及1024成员HANDLE不改。v2 monitor只允许P2提案的3600s/65s/8192文件上限；point10s、fresh60s，仍须完整HANDLE清点和5秒收束。提案不代表准入；fresh60s加最多5秒收束已接近outer无进展65s，父端文件保存、核验及真实阻塞成本尚无余量证据。

## 内部满成功调用量

| 工作 | 条件结构次数 | 直接依据与范围 |
|---|---:|---|
| point transport/native槽 | 319 | 41 actual+278 contract，实际未执行 |
| QP / LP | 160 / 159 | frozen packet角色 |
| scientific constructs / import | 1276 / 638 | 每点4构模、2 import，未改变原数值合同 |
| 内部CLI轻核注册 | 321 | worker1+point319+fresh1 |
| load_packet(false/true合计) | 960 | CLI321+parent transport319+point worker319+worker setup1 |
| P2 fingerprints | 1281 | parent2×319+point2×319+worker3+fresh2 |
| P2 preserve | 3 | worker initial/before finish/after fresh |
| 新合同raw child-LP重审 | 138 | 保存显式最优性audit，不增加构模/import |
| 合同firm audit / legal-X内部point audit | 138 / 138 | 原数值证据有效后保存正负verdict |
| 关闭后reopen | 2 | fresh一次、parent一次；各自重放全部接受条目 |

1281次fingerprints各核55个准备源及7个P2源，另调用原P1指纹方法；其文件/metadata遍历成本不能忽略。当前函数先核三件准备工件、返回时再次stamp三件，因此内部成功路径仅准备工件的hash读取子量就为`505285×(960+2×1281+3)=1781129625B`。另有load_packet的JSON读取`255146×960=244940160B`和fingerprints的context JSON读取`249557×1281=319682517B`，三件工件合计逻辑读取2345752302B，不是独立数据量或已发生IO观测；55-source stamp为70455次、7-source stamp为8967次。这里不含原P1指纹内部遍历、preserve的683文件及旧保存核验、CAS、native日志、journal、原审计/摘要、completion或outer开销。

worker setup另执行一次packet静态验证（316个PointRequest对象）；controller直接请求构造为326，但原journal/policy/独立审计与两次reopen还会重建请求及反复遍历prefix，不能将326或316当作全执行对象计数。完整journal/CAS/摘要与失败分支的乘数尚待对具体接线闭合。

## 优化与下一证据

重复解析固定255146B packet、重复hash三件505285B工件、原环境/来源遍历及prefix重审是下一有界诊断对象。尚未测本后继的实际占比，不据静态bytes报告提速。若复用已验证的只读slot/context或减少stamp，必须先证明loaded-object固定、输入freshness、失效、point/quiet/fresh漂移与失败窗口保持；当前不通过全局monkeypatch改旧科研栈，也不直接套用plain_v2。

新执行器尚无外层launcher/quiet后采用、运行注册、十小时writer增长与完整合同/昂贵失败成本证据。普通解析/FakeApi/短Python检查不是上述测量。下一步先登记并执行一次无solver的来源/packet核验诊断，分清旧指纹、新stamp、parse、preserve和bookend成本；再决定优化与outer实现，补齐全DAG预算后才讨论具体native代表测量。P1唯一native授权已用，C整体性能、139数值/F-X时序及D/E来源/选择/留出仍OPEN。
