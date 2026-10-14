# H1 historical controller/current 开发草稿

2026-10-09，DRAFT_NONAUTHORITATIVE，R3，根代理唯一写入。
实现为 `experiments/h1_historical_controller_development_v1.py`；此前 design 文档保留原状态。
本规格没有 official verdict、生产封存或运行授权。

## 指定历史前缀

`inspect/prepare` 从外部 obligation header/terminal pins 与 completed_hours 指定 1..168 小时前缀。
完整重验旧 header、manifest/resolver/enrollment、terminal 反向回链至 header、每小时 obligation/request，
再重验 clock 的 Job/outcome 对应和已有 `bridge.inspect` 的全部校验。
HistoricalTimedSnapshot 明确保留 timed SourceParent 的 declaration、Job child、outcome 与 carry replay。
旧 controller、source、Job、clock、parent 文件没有修改。

`prepare` 两次调用完整 replay，最后小时捕获完整 accepted timed projection，复用旧 current-only `_decision`。
回放不接受序列化 carry，也不接受 detached prefix 类型作为凭据。
source坐标、外部pins、Job/clock身份、历史carry与selector locks留在audit，后续suffix不进入decision或audit。

## Freshness 与后缀

prepare调用级观察记录在两次replay间保留：obligation稳定视图、有界后续名字与inode、root锁/目录身份，
parent journal/anchor/header/child-reference、clock三个小时记录、Job与worker完整有界视图。
Job视图复用既有 `job_view`，不打开 scratch 内部；这些观察摘要不进入任何科学或audit identity。
固定来源支持包括已pin config、两个package的manifest/member、builder config/code、power chronology，
以及固定 RTS SHA256SUMS 中的全部成员和相关目录。解析RTS成员前先验manifest固定SHA与字节上界。
来源只比较文件身份、stamp、目录身份/名字；内容合法性仍由既有source loader的hash/语义检查承担。
来源观察在每次replay前后复核。只承诺普通变更检测与fresh-at-return，不承诺hostile ABA、锁或静默期。

obligation后续名字必须是合法ASCII三位小时与binding/job/terminal，按发布顺序连续出现；
每个已消费小时必须完整，未知、更晚越界、hardlink或已观察项替换均拒绝。
Job/clock后续只看有界目录身份，不消费其内容。完整latest或suffix真实性需另行验证。

## 验证范围和开放项

首轮名称9项、两小时集成1项已通过；集成使用现有显式synthetic source/catalog和禁止真实solver的worker，
实际两个bounded Windows Job正常退出。这不是真实RTS调度或native可达性证据。
首轮独立静态审查保留F1：两次replay未共享inode观察。当前草稿修复F1，新增跨层同字节替换、
真实prepare接线故障注入、固定来源inventory，以及多类prefix证据损坏回归；最终测试与独立闭合仍待完成。

历史parent/obligation/Job/clock成功重验仅为已保存证据的对应关系。
suffix_chain_verified、current_latest_*、live_release/handoff、writer_lock_authenticated、
persistent_lane_owner_implemented、detached_consumer_authenticated、common_prefix_publication_verified、
reference_or_actual_ready、resource_admission、formal_execution_ready、formal_result、native_execution_authorized
全部保持false。尚未接通outage/current owner、same-key registry、Rref/business/actual paired commit，
也未扩展N生产至169..192小时或完成正式资源/manifest/LB-UB门。
