# Bootstrap4 到提交链的后继接线

状态：DRAFT_NONAUTHORITATIVE。root 为唯一 writer。此文保存只读 PRE_SEAL 审计提出的实现切口；未 seal、未运行本图、未打开 gate。旧 design01 和所有旧 attempt 保留。

83 在固定600秒上限停止，四Parent于368.591秒完成，Handoff于368.768秒进入；最后采样处于 `_retain_journal -> prefix -> validate_bundle`，没有 paired/Post/reopen终态。绑定1027文件无漂移，已观察PID4332及creation1792380970.763687退出。它有明确fake N0/source/numerical/common bridge，不能代替本文的genuine图。当前无需再跑相同四Parent前缀。

## 最小类型切口

`Bootstrap4/Owned4/verifier3 -> Roster3 -> bytes-only scientific projector`。

Genesis侧新增独立 witness/source/Common9、routes3和GenesisOp3；witness必须静态指向Op3。Handoff侧新增另一套 witness/source/Common10、CommonValidation5、Handoff7、ParentValidation5与PostNegative4，随后更新helper/E2E/entry。现有已绑定的Common7/8仍exact import Roster2，不能靠alias换成Roster3。

优先保留原Gen2 class、Snapshot2和Parent4的exact type。前提是Op3像Op2一样在cold import时安装可审计的private proxy，proxy.common.roster_api明确指向Roster3，并绑定全部host/helper原件和新active identity。构造器保存Common9自己的active report作为 `_initial_report`，header/declaration必须绑定Op3 identity。若不能证明这个类型与依赖闭包，则需要Gen3和Snapshot类型后继，不能混接。

Roster3只接受exact Bootstrap4 owner，拒绝Bootstrap2、subclass和lookalike。local body按Bootstrap4 `_N0_body` exact keys/bytes重建；global按 `_global_N0_body`绑定local head/body。分别验证retained verifier3 schema/identity与嵌套legacy compatibility metadata，不把返回dict里的registry execution receipt计数当作terminal绑定事实。

## 科学投影与各自执行报告

两条Common先按自己的完整keyset、schema、implementation、source/witness合同验证active report，再调用同一bytes-only projector；未知、额外和缺失字段必须拒绝。不能通过删除不同字段得到“相等”。

共享payload包括：排序后三臂完整retained references及claim/release/local/global heads与bodies、Bootstrap4/verifier3 lineage、phase manifest candidate science、exact SourceBinding、historical audit、已验证wrapper内的canonical predecessor/exact-current science、decision/exogenous hashes、common science payload/identity、canonical arm/binding、fresh-at-return/reuse-edge观察合同。

route schema/implementation、session、call/limit、执行counts、proof/cleanup由各自报告保留，各自receipt绑定 `(active_report_sha256, projector schema/identity, shared_projection_sha256)`。

Genesis持久化Common9 active report及其投影绑定。CommonValidation5逐次验证22份Common10 report的own identity和稳定性，对比其科学投影与持久化Common9投影；向Handoff functional body返回原Genesis report，而非将Common10报告冒充为Genesis报告。receipt同时保留两份报告SHA和共享投影SHA，明确完整报告不同而科学投影相同。

## 调用量和预算边界

最小正向包为create15 + inspect2 + 4 captures各2 + Handoff22：47 logical common calls、7个独立session、282 source operations、4512 contexts、564 registry preparations。每session仅首call full；合计168 full numerical replays、168 within-common revalidations、1920 cross-common reuse。不能将logical数称为full数。

若保留现helper的三轮missing-one后inspect，则另增3 sessions、6 common calls、36 source operations、576 contexts、72 registry preparations、72 full、72 within、144 reuse；总计53 calls、10 sessions、318 source operations、5088 contexts、636 registry preparations、240 full、240 within、2064 reuse。三臂Bootstrap4 N0 producer成本不在这些数里，必须另行闭合，暂不给整链ETA。

Bootstrap operation nonce、Owned transaction、verifier scope/envelope、roster guard/journal lease、witness session/ticket/proof、PreparedCommonInput、Genesis资源、ParentCompletion/Handoff token及callback均不跨阶段借用。只允许传递canonical saved bytes、SHA、纯immutable projection和closed JSON receipt。三臂N0依次运行；前两臂关闭后以terminal bytes存在，Roster3仅持一个exact live canonical owner读同一global registry。

## 验证顺序

先补Roster3类型、local/global字段及三层identity漂移拒绝；再做projector逐字段mutation、执行字段差异的metamorphic比较；再补两条Common的genuine own-root输出对比及route/preload/thread/reentry/cleanup故障；再验Gen create/inspect/capture/reopen、22-call首/中/尾投影漂移与report receipt错配；最终用新root有界验证三N0到paired/close/reopen。

83审查另发现Handoff registry lifecycle及每Post原guard/marks直接断言不足。当前测试已补强；83未执行这些新断言，不能追溯写成已通过。GenOp alias/session闭合必须同时绑定fixture teardown的 `genesis_observation_closed.json`与exit0，单独的body observation不足。

全部源代码改动和新有界实验仍遵守agent.md第7、9节。整体性能审查、完整优化链、资源及正式门均保持OPEN。
