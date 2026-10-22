# 保存输入的 append 成本诊断：启动前开发记录

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL。公共 RTS-24 方向及两母线机制回归保持；本记录只核一个三母线解析保存前缀上的无求解器诊断实现。B1–B3、旧 codec/journal、batch 五源和 P1 十三源及注册保持原字节。

新 runner 使用旧 v1 三方法的前两小时保存输入，原 observation_end=5 不变；先独立准备 baseline，再固定 v2→v3 顺序运行六成功、六失败和十二 fresh。准备 selective 会计为 12 calls/34 descriptions，测量 186/514，合计 198/548；构模、full compiler、native 和 solver 次数为零。输入读取、科学审计、持久化、failure witness、独立 fresh、Job 静默和 controller 终态读回均计入自身 DAG。

准备 Job 上限 30s；测量 outer 上限 300s，其中 worker 分组总额 270s；单 fresh 10s 且启动前预留清理预算。测量输出总树 16MiB/3000 文件、采样 RSS 1GiB；quiet 后 controller 读回另有 45s 合作式预算。外部 Stopwatch 记录解释器启动至退出；它和晚写的 controller_timings 均单独保留并绑定。详见诊断合同，不把 worker wall 当全部流程耗时。

普通测试经历六次保留日志：首轮 14 passed/5 failed，随后 19、31、36 passed，新增 timing/tree-cap 后窄测 12 passed/28 deselected，外部 capture 修复后窄测 11 passed/35 deselected。后两轮各新增4和6项，因此共46个不同检查；窄测分别另有8和5项重叠，不加总重复测试为样本数。含十二个真实 case/fresh 函数路径的单进程测试、一个微型 Python owned Job 传输和六个临时假Python外部捕获测试；普通测试不是性能 attempt。

包装复核曾发现外部wrapper的非原子日志创建和缺timing可误接受两处Medium。已改为create-new owner/log/intent/capture，启动前绑定脚本，准备request及每角色首尾纳入同一direct pin，末端核脚本/request/timing，外部capture绑定日志字节；两进程同时启动的普通反例确认只有一个假child被调用。原启动前binding_snapshot及development_checks_draft_01.json保留为修复前草稿快照，当前绑定以binding_snapshot_v2.json和development_checks.json为准。

只读 sol_reviewer 已复核源码及合同，无剩余 High/Medium 实现 finding；明细见 preseal_findings.json。本页与 development_checks.json 保存启动前事实：尚无 cost_preparation_01、cost_registration_v1.json 或 cost_probe_01。后续实际诊断另存，不改这份历史开发记录。postcheck.py 默认拒绝这些路径已出现；完成后可用 --allow-cost-attempt 复核此历史绑定。

本诊断只支持固定顺序下阶段绝对值与科学/保存等价检查，不报告提速比、节省百分比或优势推断。公共数值点、真实 dual/log、完整139/F-X时序、长 cohort/192h、真实阻塞IO/坏盘、C/D/E资源准入均未覆盖。P1未获专项授权且未创建；没有正式结果、seal、official verdict 或 receipt。
