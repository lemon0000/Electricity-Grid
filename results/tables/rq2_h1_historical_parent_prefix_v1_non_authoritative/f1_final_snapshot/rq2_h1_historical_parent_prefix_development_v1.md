# H1 historical parent prefix reader 开发草稿

2026-10-09，DRAFT_NONAUTHORITATIVE。R3，根代理唯一writer。
新增 `experiments/h1_historical_parent_prefix_development_v1.py`，不改旧parent/journal/anchor/reader。
此组件读取由外部 declaration identity、completed_hours=h、parent head、anchor record SHA固定的历史
accepted prefix；不是当前最新parent认证，也不是writer lease或持久lane owner凭据。

## 范围

旧Snapshot要求完整目录恰好停在其retained最新head；后续追加会使旧pin无法使用。
新reader仅消费parent events 1..2h、anchors 0..2h和children 0..h-1，保留旧声明的完整hours上界。
正h且h≤hours≤192；不支持genesis-only或半小时pending/rejected边界。

PrefixJournal使用旧header与commit schema，验证每项canonical metadata、payload、byte cap、
长度、SHA、sequence、previous和最终外部head。PrefixAnchor验证旧header、previous record SHA、
previous registry head、逐项head/event hash和最终外部anchor pin。
genesis anchor必须指向journal identity；每个anchor[k]的registry_head与event[k] head相等，
event_sha256与event[k] metadata相等。不能仅依赖一个final pin替代这些对应检查。

只读view复用原bounded parent的source `_load/_packet`、child replay与`_restore`；只由完整accepted
prefix重新生成carry，不能直接加载序列化boundary。没有native调用、Job或写入方法；原writer lease
保持其所有权，reader只观察文件身份。旧source、child、gap/残差和selector规则未改变。

## 后缀隔离

合法后缀仅允许声明上界内的三位ASCII数字目录/文件，编号连续，类型正确，无reparse路径或额外名字。
只读取后缀名字与文件系统identity，不打开后缀payload/metadata/commit/anchor内容或child目录内部。
后缀可尚未完成或内容损坏；该事实不改变已固定prefix的科学投影。
reader存活期间可新增合法后缀；已经观察到的目录项删除、替换或重命名则拒绝。
prefix文件仍按有界稳定read和retained identity/stamp复查，任意prefix变化拒绝。

返回HistoricalInspection保留旧历史state字段并显式标记：
historical_parent_prefix_verified=true、suffix_namespace_bounded=true；
suffix_chain_verified=false、current_latest_parent_verified=false、live_handoff_authenticated=false。
没有暴露suffix计数或最大时刻。其余执行、发布、资源、formal字段沿用false。
前缀读取成功不证明现存suffix真的接续了该head；需要latest真实性时必须另做完整latest验证。

## 尚需后继接线

本组件只实现parent层。完整accepted N historical-prefix controller仍须校验前h小时的
obligation binding/job/clock/terminal链，再使current-information reader在返回前后都调用该历史校验。
owner还须持久绑定这些外部pins、N/Rref/business/actual前序heads并执行paired commit。
单独HistoricalInspection、可手工构造的Python类型或历史child都不提供上述认证。

PRE_SEAL验证应覆盖合法append、部分/损坏suffix且不读内容、prefix各类文件变更、错误外部pins、
时钟/来源漂移、namespace边界/gap/类型、过程中替换与新增、所有写入方法拒绝。
完整controller/Job对应、168/192 producer与资源容量尚无完成声明。

## PRE_SEAL F1 single-link repair

All consumed parent journal/anchor header and prefix evidence reads check regular single-link identity before and after stable reading. Journal header identity is retained across checks. Anchor namespace files, including suffix names, require single-link and distinct inodes. Suffix event content remains unopened; linking it to consumed prefix evidence is rejected through the prefix link count. This does not authenticate unused suffix content or provide a filesystem quiescence certificate.
