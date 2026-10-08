# H1 worker 输入的只读 parent snapshot（开发）

新增 `experiments/h1_parent_snapshot_development_v1.py`。独立 worker 需要在 parent
保持自身写锁时读取已锚定前缀，因此新增只读观察器，不获取、注册或释放 writer
lease，不读取被 msvcrt 锁住的 execution.lock 首字节，只检查目录及lock文件身份。
该观察不认证writer是否活跃或持锁；历史pending也可能通过纯数据复核。

JournalSnapshot、AnchorSnapshot分别复用已有完整扫描器，以外部head/anchor pin
复核全部记录；append/advance始终拒绝，close仅关闭读观察器。Snapshot继承既有
source/clock/carry/typed-child重放，从声明的pinned origin重建network，通过已有
科学child重放重建before carry，再用当前source组装packet。不从JSON构造owned
boundary或projection，不沿用前进程的内存结果。

输入只允许pending_unknown：events=2h+1、attempted=h+1、anchor.sequence=events、
anchor.registry_head=外部head。根目录必须恰有lock、journal、anchor及前h个完整
child；当前hour child不存在。已有或部分current child不能转成可重试输入。前后
重放及完整根目录视图复核，并逐项匹配最后intent metadata、source audit payload、
event head、source identity、request key和packet audit。错误、漂移或不完整均停止。

`pending_input`返回冻结`PendingWorkerInput`，含实际packet/spec/limits及≤2048bytes
canonical receipt。receipt绑定parent/declaration hash、anchor record、journal及
intent head、hour/source lineage、before identity、request key、packet audit、
stage count和snapshot实现。构造器重新核对packet/spec/limits与receipt语法、值和
权限字段；validate另要求外部保留receipt SHA。冻结对象仍需使用前复核，因为嵌套
科学数据可能遭外部修改；receipt本身不提供密码学身份或执行许可。

receipt明确：writer_lock_authenticated、quiescence_certified、native_execution_authorized、
independent_job_integrated、resource_admission、formal_execution_ready、formal_result
均false，external_live_handoff_required=true。最后一次读检查后writer仍可推进；
后继controller必须实现从live create-owner到Job消费的一次性handoff并重新检查。
仅有磁盘pending、某个进程的锁或该typed input都不能授予resume/native权限。

验证包含synthetic连续carry、外部pin与clock/config错误、当前child出现及
journal/anchor推进竞态；另用真实已保存v3 source declaration，在独立Python进程
重建实际pinned RTS origin输入和232-stage inventory，solver调用被禁止，parent
三个lease保留，文件内容和mtime不变，没有创建child。该项是source输入验证，
没有执行232个求解stage，也不是full-window producer/native export覆盖或Job验收。

此单元不启动生产worker，不新增native gate/lease或复用v3授权，不写parent结果。
完整worker/独立hour Job、live handoff、raw-before-audit native接入、完整分段/observer、
Job/FS/时间资源、实际reuse DAG/task manifest、Rref/A和LB/UB、封存及全新official
独立审查仍待完成。新native运行仍需具体包和门禁就绪后另行明确授权。
