# 完整selector调用的持久记账

状态：DRAFT_NONAUTHORITATIVE。实现`scale_selector_store.py`，复用既有`episode_store._Lease`的本地NTFS排他锁、路径及文件身份检查。新SQLite schema/application ID与旧normal/episode store隔离；未修改刚审查的`scale_selector.py`或旧store。

## 一次调用与未知状态

`SelectorRequest`私有副本包含完整info/disclosure/before、实际功率、selector/spec/budget及外部input/policy pin。创建新`*_non_authoritative`目录和独占数据库；已有目录不覆盖。header绑定请求、全部有序阶段、最大solver秒数、记录限额、root身份、selector/lease/codec/store源码及SQLite版本。

`execute()`在进入数值内核之前，以SQLite DELETE journal、synchronous FULL提交一个覆盖全部有序阶段的intent。随后只读回验exact intent与pending状态，再进入selector。返回后保存完整encoded `ScaleSelectionResult`、其identity和记录SHA256，回读exact bytes后才把结果返回调用者。任何失败使当前owner不可重试；constructor也不提供恢复执行模式。

| 落盘状态 | 解释 | 资源计费 |
|---|---|---|
| unused | 无intent；不是可直接恢复运行的游标 | charge为0 |
| pending_unknown | intent存在、完整结果未发布；实际调用数未知 | 全部planned calls与reserved solver seconds占用 |
| returned_unverified | 返回记录与请求、摘要、调用计数字段一致 | 仍按全部预留占用，早停不释放 |

这是一次完整selector调用的外层记账，不是逐阶段checkpoint。进程在任一阶段退出时，不从退出位置、PID不存在或缺少result推断零调用；保留unknown，不重启、不重试。若完整结果确已返回，archive保留其中已有阶段和known/unknown调用字段。`reported_solver_calls`仅复述返回记录，不等于原生调用认证。

## 检查与解释边界

重开仅提供inspection，要求调用者独立持有header绑定摘要和record限额。获取现有目录lease后只读数据库；检查schema、integrity、root路径/inode、规范JSON、记录摘要、typed字段清单、request/result对应关系和调用数范围。复制到另一个root不会继承原绑定。进程存活期间还校验数据库文件身份及源码/请求漂移。

inspect不能重新构造可执行结果或cursor，也不执行原物理/数值回放。因此`numerical_evidence_replayed`、`native_execution_authenticated`、`actual_solver_calls_verified`、`executable_resume_available`与formal均false。`returned_unverified`不是selector数值通过，也不是安全、容量或资源证明；unresolved结果同样可以被完整保存。

原selector返回对象保持原字节语义，其`durable_invocation_tracking=false`不被外层改写。持久intent证据由此store的inspection单独承载。合作式本地锁与SHA检查不是恶意进程防护、远程认证或掉电硬件保证。

`max_record_bytes`只限制单个完整result payload，metadata、SQLite/journal开销、全部归档及scratch另需整任务预算。没有硬wall/内存/磁盘终止，没有发布生产lease/manifest、official receipt或运行许可。后继进程监督必须在硬终止后等待Job静默，再检查intent/result；不能在写者仍活跃时把数据库当作immutable snapshot读取。

## 验证记录

首轮9项通过（10.95秒），包括真实tiny reference存储、排他/不可复制、结果写失败、intent确认丢失、超小record限额、摘要破坏及子进程intent后直接exit17。补结果已提交但确认丢失、错请求结果拒绝后，与selector组合47项通过（51.43秒）。

独立pre-seal指出提交后exact回读和codec源码闭包缺口，已修复；同时增加全额charge字段。17项通过（18.48秒），包含intent/result INSERT no-op、回读I/O失败、codec漂移与早停仍全额计费。另补复制root拒绝反例，最终18项通过（19.02秒、exit0），限定独立复核已闭合，无剩余实质finding。复用lease的旧跨进程排他、hardlink拒绝及unlock异常句柄释放5项通过（20.87秒）；git diff --check通过。所有文件写入测试仅使用pytest/system tmp；未运行真实H25任务、清理仓库或修改旧结果。
