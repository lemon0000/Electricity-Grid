# H1 固定模型规模与 raw 入口开发

本批次为 R3 非执行开发；根唯一写入，独立只读审查。旧 v3 runner/source closure、所有已保存 raw 和已封存资源声明保持。没有新的执行包、lease、official verdict 或 native 运行权限。

## 固定模型规模和旧上限反例

`experiments/h1_producer_shape_development_v1.py` 绑定 canonical v3 request、当前 source receipt 与静态 network；枚举固定索引全集并与真实零求解模型逐项比对。G=158、C=73、B=73、L=120、D=1、R=101、area=3，因此变量数为6C+G+B+L+D+R=891，阶段数为1+C+G=232。全部变量名JSON token最长38字节。

固定成本模板非零项为73 commitment、216 segment_power、73 startup、0 shutdown，共362项；逐项二进制系数与canonical linear representation相同。后231阶段仅选择单个变量作为目标。carry和strict locks不添加变量或目标项，但会添加约束。

约束数拆分：不含条件行的core为3C+4C+2C+L+B+R+area=954。固定pinned RTS loader将thermal bounds始终设为静态p_min/p_max，且cost breakpoints端点相同，因此normal generation_limits恒为0；reserve commitment行固定26。future source boundary要求age>=1，仅61台机组可能在H1增加一条residual dwell行，strict locks最多231条。因此该数据源族的未来上限为954+26+61+231=1272，origin上限为1211。

脚本另核对192个已加载小时的generator keys、thermal bounds与reserve area keys，并保存行摘要hash。这是来源族的开发验证，不是完整192h执行、因果前缀或未来逐hour来源认证。数学上界还依赖固定源码的loader赋值和model循环结构；真实successor必须逐小时绑定相同静态inventory、来源入口和相对时钟。

反例使用relative_hour=1的合成carry，将eligible units放在age=1，对231个锁使用合成0.0值，真实模型得到1272个约束。它通过接口的状态和输入校验，足以反驳1211作为该接口全域规模上限；没有证明这个carry及锁存在可达或可行的科研轨迹。synthetic_boundary=true，reachable_assignment_proven/scientific_witness=false。

若只保留相同静态inventory、base-only H1、固定reserve area keys而允许任意合法hourly bounds，则generation_limits最多146行，reserve commitment最多73行：future source boundary下上界1465，允许generic initial age=0时为1477。这些值不能与pinned-source的1272混用。

新 `h1_report_byte_bound_development_v2.py` 只在开发语法中将constraints上限设为1272；组合字节界仍为929218。它继承且不改写v1语法文件，其余变量/terms/UID条件保持。v3的1211上限和16MiB采集合同未修改。native export是否重复terms等仍需独立runtime guard；producer_coverage_proven、native_export_coverage及resource_admission保持false。

## Raw-before-consumer 入口

依赖闭包修订：规模脚本在加载source之前只读校验既有v3 exact outer `e3acc7a6de1c1863ab64a8c1ae67ded9676e01c564a3d4ef2d0be29252f0edcf` 的1695个成员，记录outer hash和成功验证结果。另显式pin `continuous_grid_normal.py`（residual dwell逻辑）及 `normal_h1_full_job_v3.py`（binding入口）。初版产物及七份开发文件已保存到pre_dependency_review_snapshot_non_authoritative；旧封存包作为依赖闭包证据，不成为新运行授权。

`experiments/h1_raw_ingress_development_v1.py` 为create-once、单PID/thread的开发适配器。每stage依次：写入intent；调用producer一次；将非空且不超过16MiB的原始bytes exclusive写入；flush/fsync并从新handle复核；写入绑定intent和raw hash/length的receipt；重新读取raw后调用consumer一次；写入consumer_returned outcome。首个内部异常poison，不重试、不修补结果。producer抛错、未返回raw或超过旧cap时不承诺完整raw已存。

外部审计若发生在deliver返回后，调用方须显式abort，永久poison并写bounded aborted记录。三阶段旧collector的test-only seam在科学审计前断言raw/receipt已存在；审计抛错时显式abort，并测试后续deliver被拒绝。旧collector自身已有独立的armed/poison保护。测试gate和saved capture替身仅位于pytest，既有solver-forbidden fixture阻止任何native求解；这不是生产runner接线。

稳定reader在同一handle最多读取cap+1；读取前后fstat及路径身份均核验，并对完整inspection的文件和目录视图复验。Windows当前Python中path stat与fstat的ctime语义不同，跨API只比较device/inode/size/mtime，各API内仍比较完整ctime身份。增长、替换、超限或视图变化均保持unresolved。reader不恢复、不写盘，不授予retry。

fsync和fresh readback证明的是当前文件系统可见的完整写入；未证明断电后的目录项或卷级持久性。每次ingress保存额外raw副本：raw cap仍为232×16MiB/小时，metadata单文件2048字节上限；该副本和物理分配、scratch、overhead必须加入后继资源预算，不能据此沿用旧磁盘准入。没有跨进程writer lease、外部不可回滚anchor或恶意全链重写认证。

`consumer_returned`仅是回调完成，不表示scientific accepted、projection发布或native认证。fresh inspector只能确认所读链和文件一致，所有formal/resource/native flags保持false；partial files和缺少terminal记unresolved，保留现场。

验收包括：顺序和exact types、零/边界/超限raw、每个写入窗口、producer/consumer异常、外部abort、短写/fsync错误、同handle增长、stat/open之间替换、inspection后段修改前段、232份保存raw完整传递以及既有三阶段collector审计前持久化接缝。后续仍需完整source parent、native guard、collector生产接线、timing、失败通道分类和完整资源准入。
