# C同append批处理开发核验

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。接续[合同](../../../../docs/plan/staged_deliverability_c_append_batch_contract_v1.md)。公共RTS-24方向保持，两母线用于机制回归。本页记录普通测试和静态核验；没有新性能attempt、公共数值点或P1执行。

新journal_v3在一次同步append内复用刚完成的CAS/root核验快照，各逻辑根只pack一次，合并对象闭包与联合预算后按首次出现顺序发布。旧key只核字节、不补写；新key排他发布。entry前及采用前仍完整核CAS/root/目录/依赖，外部数值等待、其他append和fresh均不复用此快照。完整科学审计保持。

| 成功操作 | v2结构调用 | v3普通测试观测 |
|---|---:|---:|
| hour，包括begin与commit | inventory 10、pack 4 | inventory 6、pack 2 |
| finish | inventory 8、pack 4 | inventory 4、pack 2 |
| append自身，不含调用方检查 | inventory 7、pack 4 | inventory 3、pack 2，由完整操作分解 |

v2依据[保留成本审查](../../../../docs/plan/staged_deliverability_c_retained_cost_review_v1.md)及原代码；新测试同时覆盖codec动态pack入口。计数排除create、fresh及额外诊断。attempt只有一个逻辑根；失败不补齐成功调用数。复制、typed比较和新增runtime检查有自身成本，未测wall/RSS/storage收益；key/state物化、科学前缀审计与累计扫描增长仍存在。

普通检查终态：

- `pytest_batch_03.log`：74 passed / 137.49s，exit0。共享闭包与原wire/根SHA、联合对象/字节预算、新key竞态、旧overlap删除、两种发布目标各七阶段、原对象/旧prefix/Session字段修改、prepare与外部等待删除、目录/root/依赖漂移、三类未决、known rejection、terminal pending/unknown、失败witness写入失败、foreign entry、可信绑定和fresh读后篡改。
- 三方法两小时、finish及独立只读重放的完整state、CAS清单/逐文件字节、summary、audit、outcome/certainty相同；v3 schema/runtime单列，不宣称journal entry/root哈希与v2相同。新测试阻止Pyomo solver factory和Highs构造；fresh另阻止构模、put与publish。
- `pytest_related_01.log`：旧journal_v1/v2、reference queries、causal及child optimality五份测试188 passed / 196.45s，exit0。合计262项不同普通检查。两份测试wall均为开发验证成本，不用于公共网络整链准入。

保留失败记录：`pytest_batch_01.log`为`-s`测试启动时缺user-site pygments，未收集测试；改用既有`compute/python -B -m pytest`，未安装或变更环境。`pytest_batch_02.log`为70 passed / 1 failed / 106.10s：缺文件已正确拒绝，新断言仅允许ValueError，后改为也允许FileNotFoundError。失败日志原字节保留。

只读sol_reviewer发现Session字段重绑窗口：一次捕获的tuple不能检测原Session字段重绑，后半段仍读原head/ordinal可能污染entry。现整体deepcopy(Session,payload,candidate)，两次动态提取全部字段比较，后续操作及failure全部使用隔离副本；八个字段重绑与两个旧row修改反例通过。最终源码/合同静态复核无剩余High/Medium实现finding，仅要求封装后复核。见[findings](preseal_findings.json)。这是pre-seal开发审查，没有official verdict、seal或receipt。

[机器记录](development_checks.json)绑定新代码/测试/合同及保存工件；[只读postcheck](postcheck.py)核29个selected runtime源与10个external入口，AST确认v2的17个顶层定义保持、`_check`仅增加返回已核CAS。旧P1 postcheck在首尾均exit0：118个B1–B3文件、42仓库pin/7选定外部、C/build/causal、531/138 journal核心及numeric/P1源保持；P1注册SHA仍为`23577e5d79d3284a260decbfe2258a3103252617953452565a9feeffafbd94e2`，13个注册源未改，`p1_01`不存在。具体终态见`postcheck.log`与`verification.json`。

本后继尚未接入P1，原注册继续指向v2。公共点/g、真实dual/日志与公共保存成本、完整139及F/X反事实任务时序、长cohort/真实失败与阻塞IO、C整体性能和D/E方案点数/资源仍OPEN。下一步先登记本后继的保存成本有界测量，或在原P1获得专项授权后按原绑定执行一次；两者各自保留范围与权限。
