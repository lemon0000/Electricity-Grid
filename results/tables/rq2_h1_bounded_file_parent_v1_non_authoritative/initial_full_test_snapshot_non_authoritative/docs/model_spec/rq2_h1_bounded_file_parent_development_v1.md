# H1 有界文件事件 parent（开发后继）

旧 chunk journal 只声明 metadata/payload 内容预算，未限制 SQLite/index/rollback
空间。新增 `h1_file_parent_journal_development_v1` 及接入它的
`h1_bounded_file_parent_development_v1.SavedSourceParent`，使后继 parent 自身的
所有内部文件有显式内容上界。旧 SQLite 路径、封存、开发证据与结果保持不变。

事件按 metadata.bin、payload.bin、commit.json 顺序 create-once 写入；空 payload
也保留文件。前两者各最多256KiB，commit最多2048 bytes。每次 xb、fsync、稳定
fresh readback。commit绑定sequence、predecessor、metadata/payload的长度及SHA；
完整prefix重新扫描成功后才推进live head。header固定root、parent binding、预算
和实现身份，head由原anchor独立保留。最多384 events，容量检查在mkdir之前。

同一事件任何部分写入、写入确认异常或后验检查失败均poison；文件保留，不重试
或修补。重开是只读，使用外部anchor head扫描全部事件，不截断、不忽略未锚定
完整tail、partial tail、gap或额外文件。同进程/跨进程写入由既有NTFS lease约束，
对象内重入/并发由Exclusive拒绝；已确认事件的live文件身份持续保留，完整scan
前后复核字节/身份/拓扑。重开绑定hash而非跨进程inode历史。不是hostile rollback
服务，也不证明断电目录项durability。

新parent保留来源、clock、carry、typed child、失败停止和anchor规则。`_restore`
只有原SQL读取event head替换为外部head检查的`event_head`；AST等价测试固定这一
差异。构造器接入新journal及单独root lease，declaration schema/identity更新。
事件的旧chronology schema保留。旧parent不能按旧identity打开新根，不迁移旧根。

journal完整但anchor未推进时重开拒绝；anchor已完整推进但调用方未获得确认时，
只能在另外保留的新anchor pin下进行只读检查。无child时结果仍pending_unknown。
这不授予补做outcome、继续运行或resume权限。

E=2H时journal界为E×(2×262144+2048)+2048+1 bytes，3E+2文件、E+1目录。
anchor继续用64KiB/header或record，计header+2H+1编号记录、1byte lock；root另计
1byte lock与自身目录。child沿用已审成功/首次失败分类界。部分文件、未锚定完整
事件仍处于同一槽位内。上界保留所有小时槽位，不从成功测试实测尺寸推断。

完整上界仅覆盖这个saved parent及内部child/journal/anchor；不含Job、scratch、
上游raw副本、文件系统metadata/allocation、运行内存或时间。旧parent历史重放的
累计成本仍需预算，新journal的完整prefix扫描也增加成本。资源准入及所有正式
运行/结果门保持false。完整worker、独立hour Job、完整任务manifest/reuse DAG、
Rref/A和LB/UB、封存与全新official独立审查仍待完成；新native须另行明确授权。
