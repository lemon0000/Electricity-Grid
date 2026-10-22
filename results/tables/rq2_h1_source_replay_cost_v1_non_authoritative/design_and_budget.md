# 保存三小时source重放成本分解

2026-10-21，DRAFT_NONAUTHORITATIVE，R3，主代理唯一writer，独立只读PRE_SEAL复核。旧hour0/2h/3h与phase-body证据复用；业务record复用负结果不改。当前无活动研究进程。目标168h/≤24h整链预算及真实episode终结仍未闭合。

已有证据明确32个Reader observation耗时合计655.2262379s，但缺当前三小时、双机组/五stage路径的函数成本和精确Job/stage调用量。旧historical_profile_04覆盖单小时、旧三stage路径，含9475次importlib.metadata.version、8次inspect_job和24次stage.inspect；只能提示重复依赖身份/科学重放，不能直接代替当前路径的预算。

本次必要诊断固定为**一个保存三小时prefix的historical.replay_prefixes调用**，selected_hours=(0,1,2)，不重跑已有32次观测。执行路径：核旧1299 source pins与465 case/444 owned SHA → 按原fixture在内存重装synthetic source/catalog及原15个immutable-code identity memo → 原pin-bound manifest/externally saved terminal map → 一个原Reader（constructor与显式inspect均执行）→ 原clock/Job/worker/stage科学重放及原清理 → captured normal audit与旧三个intent逐一对照 → 原memo恢复/bookend → 保存profile及原件SHA复核。不开N、selector、Windows Job、native或owner写入；没有新缓存/优化实现。

固定wall180s，2s采样，30s心跳，sampled tree RSS1GiB、logical输出128MiB。无独立延长；卡住或超限按wall/RSS/storage条件停止仅本runner拥有PID/create-time树，保存失败终态。ReadView可在旧execution.lock上取得只读共享句柄；没有writer lease/adopt，不创建或改变旧文件。审计hook拒绝旧case内open写入及mkdir/remove/rename等修改；fixture中两个已存在支持文件的write_bytes/mkdir调用只核原bytes并返回，不实际执行写入。

源、config、manifest和科学阈值均不改；重装的synthetic环境是旧链同样的明确seam。原静态memo15函数照旧，metadata.version、source/current/history/input identity不缓存。它仍不证明完整动态闭包/未观察ABA或生产开销。本次cProfile只支持成本归因，wall包含profiler开销，不能将其当未profiled吞吐或192h预测；旧计时不相加外推。

manifest复用保存profile前驱的同样方式：先核冻结原bytes的MANIFEST_PIN，再用私有_resolver编译它作为synthetic fixture节点；不在三小时toy source安装后重建真实168h source audit，不声称本次重新验证了真实manifest源。这与旧链显式enrollment/precheck seam保持同一边界。首attempt profile_01在setup错误调用完整open_manifest而失败，尚未进入profiled Reader；错误文本、tested_bytes和外层终态保留。空profile的报告失败同时修复为保留原错误，不掩盖setup失败；后继只重做这个必要的单Reader诊断，规模及上限不变。

验收：单Reader parent_inspect_traversals=2，captured/proof恰0..2；三个原normal audit bytes与保存intent一致；预期inspect_job=4H=12、timed_stage.inspect=4H*5=60，实测profile计数须核对；旧case清单和SHA完全相同，原1299 pins不变，所有owned PID退出。输出profile.pstats、top表、调用边及重点函数JSON。任何失配保留失败，不解释为科研不可行或略去gate。

合法减少边界仍待论证：每batch双Reader是source join前后独立观察；每Reader双parent inspect是原显式合同；clock bridge和parent child的双Job replay分别位于不同文件观察窗口。单凭相同root/head/输出不能跳过动态source、registry、clock、worker或runtime检查。先用本次分解选择后续独立DRAFT方案，再给等价/freshness与有界总路径对照；本包不接入owner，不开放任何resource/native/formal/long-chain门。
