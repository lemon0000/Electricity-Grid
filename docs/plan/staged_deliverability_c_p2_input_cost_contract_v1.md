# C：P2来源核验的一次无solver成本诊断

2026-10-23，DRAFT_NONAUTHORITATIVE。接续[P2内部执行器](continuation_handoff_20261023_p2_runner.md)及[结构成本](staged_deliverability_c_p2_runner_cost_review_v1.md)。按agent第9节，在已授权开发范围内登记一次自身有界诊断；不执行P2内部CLI、注册、准备、数值点、journal重放或任何solver，不增加P2/native/长实验权限。

## 问题、调用与依赖图

问题：当前原样P2核验的成本主要位于旧runtime指纹、新来源/准备工件hash与JSON解析，还是历史保存核验？仅测固定输入、固定顺序下的三个原函数，不实现优化、不报告提速或P2 ETA。

父端核解释器/环境、原P1 anchor与683文件、准备三工件、55准备源和已发布P2七输入→独占新measure_01→一个fresh受控诊断worker→明确setup/导入→源/函数/输入初核→安装禁止调用观察器→三个独立cProfile→观察器恢复及runtime/module/input书挡→保存profiles/报告→Job quiet→父端来源/保存输入/输出采用。

| 相位 | 唯一顶层调用 | 验证 |
|---|---|---|
| fingerprints | 原p2.fingerprints一次 | 完整结果等于P1保存runtime、context55源、P2七源与准备三工件组成的预期值 |
| packet | 原p2.load_packet(validate=False)一次 | 与固定packet完整数据相同，不调用fixture/compiler/validator |
| preserve | 原p2.preserve一次 | 原P1保存preserved、P1 anchor与准备pins相同 |

不另调legacy fingerprints或preserve；它们各嵌套一次。三相位内准备工件固定hash四轮2021140B，加packet255146B/context249557B解析，合计2525843B/14次逻辑读取；这是其子路径计数，不含旧指纹、683文件及历史来源。setup与首尾/quiet书挡使用独立字节核验，不偷偷追加上述目标调用。

## 测量与边界

imports在计时外明确预热原journal的10个external入口、原指纹7个Pyomo入口、appsi.solvers、email parser及原preserve的pypower.case24_ieee_rts入口；允许导入highspy，禁止Highs/模型/solver实例化。保存导入module库存和selected函数的规范source/code身份及引用书挡；这不是完整OS闭包。三个profile分别记录顶层wall、函数调用、自身和累计时间，序列化与输出核验在计时窗外。子函数累计嵌套，不能与顶层wall相加或直接当可节省时间；单次固定顺序、warm imports、cProfile仪器影响与OS缓存均保留为限制。

禁止model build、numeric compile/import、native构造/调用、P1/P2 CLI/worker/fresh/注册、fixture/完整schedule验证、journal create/begin/commit/finish/reopen、CAS写入及进程派生入口。观察器只在本诊断worker生效，finally恢复全部已导入别名；禁止项计数必须全零，detach/恢复失败拒绝采用。原科学源码、P1、准备包和P2执行器不改。

## 预算与验收

唯一measure_01、一个受控worker、串行三个profile各一次、零重试。采用原process_guard_v1，wall60s/无进展30s、采样RSS512MiB、进程commit1GiB/Job2GiB、16MiB/64文件、HANDLE1024和5秒收束。每相位开始/返回写进度；超限、异常、quiet未知、输入或输出漂移保留失败，不顺延或改原包。父端Job quiet后才读采用结果，关闭/终态保存失败不报告成功。

事件文件create-only初始化，采用时精确核八个阶段的顺序、标签与字段；module全名排序库存进入runtime书挡，worker首尾对象身份保持，父端采用时与自身同预热后的库存和保存观测一致；profile目标的source位置也须等于原三个函数。

验收需普通检查覆盖禁止入口及恢复、目标异常、源/结果/profile/额外文件漂移、module名单删增乱序重复、事件缺失/前缀/乱序/错标签/多字段、quiet未知、已有输出拒绝，独立PRE_SEAL复核；实际唯一诊断须exit0、三返回值等价、三个目标各一次、禁止项零、runtime/source/module与原P1首尾一致、父端quiet/输出绑定闭合。输出DRAFT_NONAUTHORITATIVE，无production lease/seal/receipt。

结论只支持后继核验优化与完整成本审查。outer launcher/quiet采用、十小时writer和昂贵失败、完整journal请求乘数、139数值/F-X时序、C整体/D-E资源与现实输入/留出仍OPEN。P1一次native授权已用，没有新native授权。
