# 显式预算normal的来源连接与固定worker

状态：DRAFT_NONAUTHORITATIVE。沿用旧公开来源核验和进程/文件原语，不修改旧H25声明、旧执行接口或结果。

## 来源连接

`scale_normal_source.ScaleNormalSourceRequest`保留完整旧`NormalTaskSourceRequest`，另带外部streaming assembly/binding及其实现pin、新normal execution pin、solver specification、ScaleNormalBudget和原始NormalResourcePlan。`request_identity`重新检查全部来源实现身份、数值执行身份和完整资源声明；不从首次prepare输出推导并替换外部预期值。

执行前后分别调用现有`normal_task_inputs_stream.prepare_task_inputs`，读取有外部SHA的build-only声明、pair YAML、config，重建RTS输入和pair绑定。新入口检查streaming及legacy内容身份、机制角色、完整输入预算绑定，比较前后规范来源快照。声明中的初态和功率映射仍是机制输入，不是业务观测、registered coupling或可执行checkpoint。

caller的`before_kernel`检查位于首次prepare和全部lineage检查之后、kernel调用之前，处于missing-return捕获区外；失败外抛，不进入kernel。callback后再次检查声明与实现，防止在该窗口改变输入。kernel异常或中断后仍尝试第二次prepare；无完整inner结果时调用数保持unknown，不能计零。旧type或不一致的owned返回不能被接受。

来源层累计耗时包含prepare与kernel等成本，只作观测；尚未由core数值cap覆盖，更不证明完整TaskEnvelope充分。source-bound accepted要求前后来源一致、新inner完整验收通过且无wrapper错误。错误或timeout不产生数学不可行结论。

## 独立来源回放

`audit_source`从当前prepare生成的inputs进入`scale_normal_replay`，不接受归档内保存的可执行状态作为输入。外部SHA、request身份与新schema固定记录；回放结束再次prepare，检测构模期间普通来源漂移。来源快照按规范字节比较，false不能用0替代。

wrapper错误必须与可复现状态相符：存在完整inner时不能声明missing-return；缺失inner须记录missing-return；缺失source-after与post-source错误双向对应。当前来源和inner均可重放时，伪造binding/acceptance/source-change错误并把accepted改成unresolved会被拒绝。诊断异常文字和非accepted的interrupted/unresolved标签不提供历史异常认证或恢复依据。

该回放只证明当前来源/记录的一致性，不认证原生调用或历史资源测量。所有formal/security/native/resource认证保持false，不返回可执行carry。

## 固定transport和worker

`scale_normal_transport`固定10个输入类，逐字段编码、有限hex float、tuple、64层/500000节点/16MiB边界；完整roundtrip后重新检查request身份。result、witness、checkpoint类均不在白名单中。

`scale_normal_worker`有execute/audit两个固定CLI模式，复用已有NTFS独占lease、exclusive/fsync/readback写入及有SHA/文件身份的有界读取。输入request和receipt必须在worker证据root外；输出不得写入upstream原始数据路径。receipt必须为新的non-authoritative文件。

- execute仅创建新non-authoritative root；先保存intent，预留一次调用及声明solver秒数，再执行source/kernel。只有完整来源记录独占写入并回读后才发布receipt。中断或落盘失败保留已有证据，无重试/恢复。
- audit要求外部intent SHA、record SHA及执行环境摘要；当前audit环境独立绑定，可使用不同TMP路径。保持root lease，核exact文件清单、intent与独立request一致，然后只调用来源回放。
- audit窗口通过try/finally封住source执行、normal kernel、native solve和native solver factory四个入口；误调用立即抛错，成功或异常后均恢复原引用。该入口用于独立worker进程，未提供同进程并发执行/审计接口。
- 两模式都在receipt写入后复验request、环境、实现和保留记录，finally释放lease。receipt存在不等于调用成功：最终复验或close仍可能失败，必须结合未来父进程终态验收。

环境仅存摘要；完整source record含独立数值记录，字节上限不超过已声明archive容量。intent、receipt和其他metadata的总量及prepare/archive/audit成本仍需在父控制器分解中覆盖。

## 验证范围与剩余入口

测试使用既有合成来源fixture；其中RTS载入和pair窗口有测试替身，不能写成真实RTS来源端到端认证。真实Gurobi部分只运行一秒上限小例。worker测试直接调用固定入口，验证独占归档、独立零solver审计、来源变动、环境/实现/请求漂移、写入异常和lease释放。

source首轮21项通过（83.67秒）；修复伪wrapper错误降级后，全部worker/transport加source正例、missing-return及三类伪错误组合19项通过、18项未选择（75.88秒）。旧prepare、pair与declared执行相关82项通过（94.26秒）。命令均为compute Python `-B -m pytest -q -p no:cacheprovider`；组合筛选`worker or transport or false_error or source_native or missing_kernel`。这些分批证据不合并为最终一次全组结果。

独立预审补充audit运行时阻断后，最终执行—审计正例和四入口阻断/恢复反例5项通过、12项未选择（48.88秒），筛选`fixed_worker or audit_worker_itself`。既有19项发生在该补充之前，不冒充最终全部测试。`git diff --check`通过。

另做一次现有真实H25来源的零solver只读检查：先核旧配置SHA `688c2090f8e26c08b744fea7f61dfef38726d29ed69163727efa23575ccca03d`，使用其中既有外部source/assembly/binding pins完成prepare，再核新预算绑定和transport roundtrip。得到25小时、158 UID，input SHA `d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c`，solver_calls=0，34.9373秒。诊断packet 11979 bytes，SHA `27e381ce52cfe7f170e2b255fad1729e816acaf3e02c9f0df35f955705360455`。该packet只在检查进程内构造，未发布运行配置；用于一致性核对的normal/episode资源清单不是完整研究任务清单或预算推荐。未执行normal，更未取得新的H25最优性证据。

持久父控制器尚未接入：它需在进程创建前保存intent、release前保存launch，监督整个Job及静默，检查receipt/退出状态，给prepare、normal、archive、audit和最终关闭分配完整预算。现有进程监督及两phase事务可以复用；本worker本身不证明这些条件，不授权H25长任务或正式实验。

## 2026-09-28 Normal父控制器审计语义修复（端到端验收未完成）

scale_normal_controller.py已形成草案，复用现有进程监督和execute/audit事务。当前完成的限定修复：不完整normal返回或调用计数未知时输出normal_invocation_unknown_not_replayed，保留solver_calls与call_count_complete原值及完整reserved_solver_seconds；只有完整数值记录可进入replayed分类。父端独立调用source.audit_source，逐字节比较完整审计报告，防止嵌套native_replay被自洽改写；父端回放封住四个求解/执行入口并在finally恢复，耗时计入controller allowance。request以packet SHA进入controller identity，修正identity encoder不支持bytes的问题。

验证：D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_scale_normal_controller_v1.py，17 passed in 31.10s。覆盖missing-return、TIME_LIMIT类未接受状态分类、完整预算保留、真实一秒上限合成normal的零solver父端回放、嵌套报告篡改、四入口阻断及恢复、预算不足拒绝和identity绑定。测试没有启动父控制器子进程，不代表完整pipeline或真实规模验收。

下一项是该既有控制器的短合成子进程execute/audit联通与失败窗口测试；完成前不进入依赖它的真实长任务。真实H25最优性、episode内层预算、完整任务清单、机制参数与删失登记仍开放。此次仅修改草案控制器、其测试及进度说明；旧冻结协议、结果、公开观测及无关未提交文件保持。

## 2026-09-28 Normal父控制器短流程验收

限定pre-seal已闭合：真实Job execute/audit合成流程及5个audit失败窗口6项通过（106.30秒）；当前controller其余19项与新旧process相关50项共69项通过（47.53秒，6项未选择）。最终字节下终态前完成全链核验，跨phase保存目录/锁及文件身份，audit读取与终态写入实测持锁。规格、准确命令与证据边界见docs/model_spec/rq2_scale_normal_controller_v1.md。来源使用显式synthetic替身，native上限一秒，不改变真实H25 TIME_LIMIT或正式数据/资源门。

下一项转向实际研究任务清单及逐阶段预算核算，先判断所选预算是否触发episode内层3600秒限制，再确定必要接口变更；同时准备normal验证和机制参数/删失登记候选。完整科学协议及正式运行许可仍开放，不宣称已能开始正式实验。
