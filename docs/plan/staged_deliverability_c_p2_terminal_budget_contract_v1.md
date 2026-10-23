# C：1024 HANDLE与父端收尾记录预算开发合同

2026-10-24，DRAFT_NONAUTHORITATIVE。接续[P2机械包检查交接](continuation_handoff_20261023_p2_package_check.md)。root唯一writer；子代理只读、不分叉。开发独立guard v3及parent observation v2，不改变guard v1/v2、父观察v1、P2七输入、packet、原注册和已发布绑定字节。本轮只执行普通短测试和标准库保存核验，不启动native、公共P2或长实验。

## 固定边界

1024是包含owner的累计不同`(pid, creation_filetime)`及其保留HANDLE上界，不是当前active进程数。沿用原OwnedChild：逐成员HANDLE signaled、Job active=0/final PID空且Job累计total等于完整保留集合，才确认quiet。遗漏短命成员、1025成员、cleanup/close未知均阻止采用；不删除成员来满足上界。P1的两个residual保持未完全归因，642仍只是条件结构投影。

worker内的`launcher.json`和独立parent observation分别有131072B（128KiB）规范ASCII JSON硬上限，各占一个文件。guard v3分别返回两份reserve和1024成员帽；原P2仍接guard v2，不在本轮替换其绑定。总预留262144B/两个文件，每次运行中及terminal扫描均计入原64MiB/8192文件总帽；3600s/65s、RSS1GiB、进程commit1GiB/Job2GiB及5s收束上限不变。RSS为收束前离散采样及pre-quiesce末次检查，不声称捕获收束窗口内已退出进程的RSS峰值；Job peak commit在quiesce后、close前再次读取。fast exit不伪造采样RSS。guard返回前也实际编码核launcher长度。

为证明长度，父观察v2在序列化前限制闭合process字段：PID为正uint32，FILETIME为正uint64；非负计数为uint64，exit为nullable uint32，wall为有限非负float。owner可双null（构造失败），否则同域。错误字符串最多514字符；guard捕获异常限定类型名64和message448字符，加两个分隔符字符，规范JSON最坏每个非BMP字符12B。witness只能为null、原quiesce的三字段部分记录或七字段完整记录；member数组及final PID数组各最多1024，成员字段闭合、身份唯一。完整记录的累计total可超过1024，但此时quiet不能成立。字段非法或超限在发布前拒绝，保留原输入、不截断member、不生成假terminal。

父观察context显式绑定两份record cap、两份文件槽与HANDLE cap，使用新schema，保留原proposal及authority=false。独立v2不接受旧reserve。所有mechanical claims沿用原闭合schema，error type/message分别限64/256字符。异常文本本身抛错时保存固定`[message unavailable]`；超长文本保存`[truncated]`标记，publish hook错误先安全归一化以保留原codec阶段。记录不嵌入context路径、原始异常或额外库存。用各有界字段的最坏规范编码独立计算上界，并以完整1024成员/最大PID与FILETIME/最大错误文本验证128KiB足够；同时保留发布前实际长度检查。reserve不是整体资源准入。

## 保存与最终会计

父目录是专用空普通目录，与worker物理路径不相交。quiet未知时不扫描或读取worker，也不调用inspect；只保存有界process诊断。quiet已知时先核worker内`launcher.json`原字节等于持有process记录，worker metadata会计等于supervisor终态加该launcher实际bytes/一个文件；不一致或扫描失败只保存失败诊断。完整metadata遍历固定entries≤16384/depth≤12，不把monitor超帽后的早返前缀称为最终总量。每文件保留path/fstat/dev/ino/size/mtime书挡及末次全文件metadata、目录identity/entry集合核对；worker完整祖先identity及launcher字节还跨越callback和publication反复书挡。成功quiet、成功退出且所有proposal帽满足时才调用机械回调。该metadata会计不替代全内容SHA或科学重放，也不提供不可观察ABA或并发文件树的线性化快照保证。本轮不提供launcher发布/spawn接口，测试仅在pytest tmp构造launcher。

父观察先按原create-only pending→flush/fsync→不覆盖rename→readback协议发布。pending和final在正常协议中只占同一文件槽；失败保留实际pending/final，禁止覆盖、自动重试或补写成功。发布前实际record长度不得超过128KiB。发布后再核父目录只有该final且原字节未变，并扫描quiet worker，返回真实worker+父记录总bytes/files及是否在原帽内。记录只声称保存观察；任何失败或超帽不成为包成功、科学采用或运行权限。

worker可能在轮询之间越帽；reserve是检测/准入条件而非文件系统硬配额。超帽失败仍可保留至多128KiB的父诊断；有界完整遍历成功时报告实际超帽总量，遍历范围或书挡失败时报告会计unknown并保留失败诊断，不扩大原帽或删除证据。quiet未知不报告完整最终包会计。发布后身份/库存/读回失败抛未决异常，保留final及expected SHA，不返回已核会计。完整outer尚未实现；本组件不提供CLI、spawn、注册、production manifest或lease。

## 验收矩阵

- 独立规范编码上界：1024成员、uint32 PID、uint64 FILETIME、1024 final PID、全部最大标量/错误文本及inspection error；128KiB边界实际检查。
- guard v3：reserve恰好/差1B、files恰好/差1、运行中/terminal超帽、pre-quiesce RSS和post-quiesce Job peak commit、fast exit、无进展、非零退出、完整/遗漏/1025历史成员及cleanup/close错误；小型真实Python Job验证quiet，零solver/native。
- parent v2：成功/失败/部分witness/双null owner、非法标量/字符串/数组、未知quiet零worker访问、metadata前后漂移、专用父目录、回调异常与全部发布阶段/读回故障、实际最终bytes/files、已有pending/final不可重试。
- 相关旧guard/parent及机械检查的窄回归；旧来源pins、原P2七输入、B1–B3/P1/已发布库存首尾SHA；Git diff/链接/进程检查。只读独立PRE_SEAL findings闭合后记录开发检查点，不生成official verdict、receipt或seal。

之后仍需真实outer启动事实/新来源闭包、受控独立raw/KKT/合法X与journal重放、昂贵失败/十小时存储及完整wall/RAM/storage。fresh60s+5s对65s无进展帽的父端余量仍OPEN；不能由本轮测试时间解除C整体、139/F-X、D/E或formal/resource门禁。
