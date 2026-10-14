# Phase prepared-ticket storage successor

2026-10-09，DRAFT_NONAUTHORITATIVE。根唯一writer，承接192h接线design_v2。
旧prepared-ticket owner的956pins保持原字节；本单元仅替换后继owner所需的外部ticket存储。

新schema接受attempt、intent、outcome、witness、episode_terminal，沿用AppendTicket计算。
只有outcome改变outcome head；所有事件均改变registry head。holder检查canonical bytes、
连续序号、固定store、before/after heads、文件身份、独立外部holder head和完整链。
事件的业务顺序由后续owner FSM负责；本holder不证明attempt对应有效need，不证明terminal合法。
新旧header互相拒绝，不能把旧root重新解释为phase root。

增加显式max_total_ticket_bytes（所有canonical ticket body字节之和），绑定header和live identity。
retain在外部head handoff和文件写入前同时检查数量、单body及总body上限。
check_branches接受非空tuple的备选分支；各分支为每个待写event的正整数body上界。
每条完整备选分支必须同时满足剩余event数量、单body与总body限制；基于expected holder head，
前后重新检查完整holder。多个互斥分支分别校验，不将其相加。

返回值仅为fresh-at-return逻辑容量观察，不持有跨调用reservation，不授予producer权限。
未来owner必须在同一个operation guard下校验自身DB、holder和整个分支的保守body上界，
然后持久attempt；不能把本检查单独当作资源准入。若实际body超过上界，必须停止并保留现场。
文件包装/base64、NTFS、SQLite、scratch、内存和计时不在总body计数内，仍需独立完整资源预算。
外部prospective head回调仍为明确的独立留存信任边界；fsync/readback不证明crash durability。

沿用原holder的same PID/thread、固定lease实例、幂等close、bounded stable read和失败poison。
此处版本复制是为保持旧固定字节与其实现identity；不得用全局替换旧KINDS扩展旧协议。
验证包括新事件head行为、持久重开、新旧header双向拒绝、整分支容量不足时零handoff/零追加、
stale head、总body边界及live bound篡改。无需source、solver或Job。

owner FSM、bootstrap、live capability、192h controller/historical/current仍待接线及独立审查。
resource_admission、formal_execution_ready、formal_result保持false。
