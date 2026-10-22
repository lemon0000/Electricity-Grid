# 业务record操作内复用：有界负结果

2026-10-20，DRAFT_NONAUTHORITATIVE。原数值重放次数减少，但本次完整detached validator路径变慢，**此优化点不采用，不接入owner**。本包只形成开发诊断；整链预算、168h/≤24h连接和episode终结的准入状态仍见[预算后继说明](whole_workflow_budget_status_v2.md)。

新[helper](../../../experiments/h1_business_record_replay_operation_development_v1.py)仅替换原business._validate中record.__post_init__的一处调用。保留原globals和其余完整validator；同一operation、同一个record对象、typed全字段图相同且依赖检查成功才复用原先通过的数值重放。完整history/current/cursor、implementation及文件观察继续执行。资源门为1024records、64MiB snapshot raw payload，另有dict/tuple/强引用开销；整体RSS独立采样。任意Python反射、未观察ABA与完整动态闭包均未证明。

`run_units_v1.py unit_01`：22 passed in 10.65s，exit0，outer13.172s；sampled tree RSS173953024B，logical615512B，1303 source pins未变，观察到的pytest/conhost PID退出。4h事实为10次validator调用、20次record观察、4次原重放/16次复用，clean close且cache清空。测试覆盖原函数的列明合法prefix及五类非法业务输入、nested mutation、实例shadow、代码/alias/default/metadata与可变常量漂移、private/creator拒绝、文件bookends及资源上限；没有穷举Python所有输入。

按[固定plan](profile_plan_v1.json)，4/16/32h各两轮，同一组原实现生成的carry做两次genesis..H完整扫。原实现计两次扫；后继计operation初始化、enter、两次扫与close。两轮顺序相反，不启用profiler。结果为描述性样本，不作为普适速度估计或192h预测：

| 业务历史H | 原validator两轮总wall，秒 | 后继两轮总wall，秒 | 每轮原重放工作量 | 每轮后继实测原重放/复用 |
|---|---|---|---:|---:|
| 4 | 0.045757 / 0.057663 | 0.242476 / 0.289813 | 20 | 4 / 16 |
| 16 | 0.323724 / 0.360779 | 1.566380 / 1.567497 | 272 | 16 / 256 |
| 32 | 1.166528 / 1.469459 | 4.763573 / 5.333247 | 1056 | 32 / 1024 |

表中“原重放工作量”按原固定代码与H(H+1)推导，不是instrumented call count；fact字段original_record_replay_work_units在两条路径均表示这个baseline理论量，后继实际计数见operation_observation。每个总wall是两次扫合计，不是单次validate。每个H均为后继更慢；32h两个block的耗时比约4.08与3.63。这里没有单独测定runtime guard与snapshot各占多少，不能把慢的原因归给某个未计时函数。

`run_profile_v1.py profile_02`：1 passed in 20.50s，exit0，outer23.094s；sampled tree RSS174002176B，logical303878B，1305 source pins未变，观察到的PID退出。33个prefix科学payload SHA前后相同，各路径接受；fixture原prepare生成32h单列0.697249s，payload前后hash单列0.055236s。32h单operation peak snapshot raw payload181178B，clean close/清空。RSS与disk为2s采样观测，不能称硬配额或未观察进程树证明。

保留`probe_01`早期import TypeError，以及`profile_01`collection失败的源码副本、stdout/stderr/JUnit/terminal。后者由旧fixture使用tests目录下sibling import而诊断脚本位于results目录引起；补显式tests/路径后只重跑这个有界诊断。失败未执行业务，也未产生性能事实；未覆盖或改写旧失败。

原hour0/2h/3h主体、phase-body 15项及其边界事实只按精确绑定复用。本包没有N/source/selector、durable paired append、真正phase terminal或owner close/reopen性能；0新normal Job、0 real native。所有resource/native/formal/full192、connected terminal/right-censor gate保持false。无production seal、official review verdict或运行授权。
