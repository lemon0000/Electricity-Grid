# H1 prepared-ticket owner recovery successor

2026-10-09，DRAFT_NONAUTHORITATIVE；根代理唯一 writer。沿用旧 saved-record owner 的数值重放、
双 heads、paired outcome、sticky conflict 与独立 NTFS lease，旧文件和旧结果不改。
这是恢复门修复，不实现192h producer、live owner/controller附着或新的科学合同。

## 具体 holder 与全链对账

每个 owner 使用独立且互不嵌套的 TicketHolder root，单独 NTFS lease、固定 header、root/header/lock
文件身份、连续六位序号文件。header绑定目标 owner 路径、nonce、实现和明确的数量/单ticket大小上限。
owner header绑定 holder 的稳定identity；第一张 ticket锁定最终owner store identity。
holder不是任意 lookup callback：重开必须提供外部独立留存的完整 holder head，目录、canonical bytes、
hash chain、单链接文件身份、predecessor、owner sequence/before/after heads 全部重验。
每个 DB event 都必须有完全相同的 holder ticket；holder最多领先一个exact next event。
中间孤儿、缺ticket、重复prepare、错误store、gap、未知文件或多出尾部均拒绝。

owner operation guard 在外，holder guard 在内，holder限同process/thread。holder必须是绑定的live实例，
同时核验持久log、lease和身份；Python类型或一个回调的返回值本身不是凭据。
所有owner inspect/advance/witness及DB读写检查重新查验holder。未知event kind在准备ticket之前拒绝。
每次检查从当前属性重建root/owner_root、目录/header/lock身份、容量和实现binding，与固定bytes逐项相等；
同时复核派生cap，并固定exact lease实例。关闭旧lease后换同目录新lease也不能让旧handle继续使用。
close 仅允许创建该handle的process/thread调用，并且幂等；旧handle重复close不得影响同目录重开后的
新holder registry或lease。异常/poison状态仍允许原owner释放固定original lease。

## 写入与恢复

holder prospective after head在写文件前交给 retain_head(genesis,before,after,sequence) 独立持有者，
回调必须返回exact after head；这是明确的外部保留信任边界，不是持久化或断电证明。
随后 holder create/fsync/fresh readback并确认新链，再允许owner执行SQLite BEGIN/INSERT/commit/readback。
holder失败或不确定写入poison该handle，DB不前进；partial文件、旧head或未知tail均fail closed并保留，
不自动清理、覆盖、补写或扫描采用未知head。

重开时由整个holder链发现ticket，不允许通过省略 recovery_ticket 绕过：

- DB exact-after：只采用逐字段匹配的那一个已提交event。
- DB exact-before：重放验证拟追加event，但不写入；Inspection.recovery_required=true，continuation=false。
- prepared-before状态下advance和alternate witness都拒绝；不自动补写、不重试任何producer。
- 更旧外部heads、多个未知events、无对应ticket的DB、holder与DB不同步均拒绝。

当前版本不提供放弃/终止prepared-before的写入接口；状态保留等待后继显式恢复协议。
若prospective head已留存而holder实际写入失败，exact-after head不能用于自动重开；需保留故障材料，
不能通过猜测正确head自行恢复。两目录同一卷不构成独立故障介质；外部head不能与两目录一起回滚。

## 容量与证据范围

holder max_tickets≥owner max_events，max_ticket_bytes≥owner max_event_bytes，绑定入owner header。
每ticket文件读取cap为2*max_ticket_bytes+4096；静态内容上界为header4096、lock1及max_tickets个cap，
并限制六位序号。该上界不含NTFS/SQLite开销，不证明内存、时钟或完整资源准入。
future pre-N attempt/terminal仍需要同时预留owner/holder整个成功或失败分支；本版本尚未实现该producer门。

测试使用原owner显式synthetic source/controller seam，保留真实selector/business数学重放；
数值模块identity缓存仅沿用旧已闭合测试fixture。不会运行native或Job。
external_ticket_log_verified仅说明本次本地log对账；crash_durability_verified、formal_result、resource_admission、
formal_execution_ready、native_execution_authenticated、full_192_hour_execution_verified仍false。
