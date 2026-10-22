# Constructor窗口依赖修复与预算续核

本轮完成指定constructor返回窗口的依赖失效修复及保存路径回归。当前为R3 / DRAFT_NONAUTHORITATIVE，唯一writer为root；旧owner没有接入候选，完整168h/≤24h连接、episode终结及正式实验准备仍未完成。

修复前，真实HistoricalSnapshot构造器完成内部inspect并接受后，将normal模型的_dependencies替换为改变runtime tuple的wrapper：旧historical Reader在第二遍读取时拒绝，候选直接返回。probe_01保留这份反例；它没有执行完整source batch，不能推断完整batch接受或科学输出漂移。

修复在构造前和原全部postbookends后读取模型source SHA/runtime tuple，严格检查结构及一致性，观察模型直接函数、常量及相关版本槽位；source和detached validator要求模型bookend metric为exact True。双Reader和原后置检查保留。源码仅修改独立DRAFT historical/source候选、辅助validator和窄测试，旧owner及所有历史原件保留。

| 实际验证 | 终态与范围 | 外层耗时 |
|---|---|---:|
| model_units_02 | 171 passed / 2.61s；含模型函数漂移、metadata值/类型、bookend位置及source/validator metric拒绝 | 4.297s |
| probe_02 | old/new各一个实际H1 Reader，指定_dependencies alias变化均拒绝；new在take前拒绝 | 71.406s |
| runtime_probe_01 | model alias保持，模拟metadata.distribution返回不同numpy版本；old/new均拒绝，new由post snapshot拒绝 | 73.453s |
| oracle_01 | 一个H3/M5完整双Readerbatch 83.976012s；3小时保存身份绑定重构及21项辅助拒绝通过 | 89.781s |
| short_comparison_01 | H1/M5固定old→new各一次；56.969790s→28.378482s；科学摘要一致 | 91.938s |

故障profile在exact构造器正常RETURN、accepted state以及实际capture状态成立后注入，错误只事后记录，不向被观察代码抛异常。两类修复后故障中观察到的ReadViews全closed，实际MRO的SourceParent.close各执行一次，Reader三项owner字段清空、capture清空。这个MRO包含timed_job_parent.SourceParent，与前轮stand-in直接借用的bounded HistoricalSnapshot.close不同；清理结论仅覆盖本次观察窗口。

H3重构复用原join/projection、保存normal audit和fresh synthetic source/registry，单字段packet projection为明确stand-in。重构bytes等于候选，SHA等于旧保存scientific identity；没有直接读取旧raw science，也不是独立科学实现。保留shared saved manifest resolver seam，未重审真实manifest来源。H3的21项辅助拒绝不包含新增model-bookend负例，后者来自171项unit。H1单次固定顺序时间只作描述，不建立普适、生产或192h提速。

七个attempt的运行时/after pins均未变，当前由live或各自tested snapshots解析；全部465个保存case文件及444个owned文件SHA重新匹配。前轮constructor core/final的157/164项和更早source-cost core/final的56/59项均按原bytes解析，不重跑旧主体。本scope全部新normal Job及real native calls为0，观察到的子进程已退出。

生成链有两份独立更正记录。短harness除两处语义替换外还将CRLF规范为LF；实际worker由execution request绑定，生成器、生成记录及真正前驱short harness另由外层绑定。runtime生成记录中的runner SHA属于加入四项provenance pins前的模板；原模板已重构保存，实际执行runner及tested bytes由request及最终verifier核验。原记录和执行包均保留。

整链预算见whole_workflow_budget_v4.json，16门对账见formal_preparation_state_v4.json。T192原路径仍有1546 Reader /149380 prefix-hour、597520次Job replay；候选若将来合法接入，条件Job replay为298760，另有3092次模型依赖snapshot及对应source/version/guard成本。这些不是native求解次数。576个operational events与旧toy cap32、三条lane始终活跃的业务历史长度下界28311936，以及完整档案、失败、terminal/reopen成本仍需处理。

指定alias及模拟外部版本变化已拒绝，完整真实文件/runtime闭包、Path方法、非确定性/ABA、owner接线和全规模资源仍缺证。整体wall/RSS/storage准入为null，overall_performance_review_complete及long_connected_launch_admitted为false；正式准备16门全部开放。下一步仍是合法source路径选择与全流程代表性成本，再验证真实167→168、携债followup、按需缺源typed右删失和episode terminal→checkpoint→close→fresh-process replay。formal/native/resource/full192/seal/official各门保持false。
