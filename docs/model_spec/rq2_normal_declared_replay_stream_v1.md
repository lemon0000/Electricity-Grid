# 流式声明日志的独立数值回放

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE。

`normal_declared_replay_stream.py` 对一次性声明日志的三层wire执行独立回放：
DeclaredStreamingNormalResult → StreamingSourceNormalExecutionResult → StreamingNormalExecutionResult。
只解析记录与重建模型，不恢复可执行 owned 对象，不调用 solver，不自动恢复或重试。
旧日志和旧 `normal_replay.py` 保留。

## 独立输入与来源

`replay_normal_record` 要求独立 record SHA、result identity、store identity、replay identity，
以及原声明执行的全部 request/source/binder/assembly/binding/kernel/execution pins、solver spec和budget。
先核有界record bytes、canonical JSON、精确封装字段与declared lineage，再重新读取pinned三份声明，
调用完整流式prepare。重建source assembly和pair binding，不使用归档terminal carry作为incoming origin。
source/kernel回放前后再次重建binding，声明回放末端重读文件并复核实现链。

`replay_normal_store` 在合作lease内读取，要求事先独立保留的**当前**head、record SHA与result identity；
仅持有genesis不能进入数值回放。回放后再次核inspect一致。新replay身份绑定自身源码、
journal、原wire decoder、native数值回放依赖及原声明执行身份。

## 三层检查

| 层 | 核验内容 |
|---|---|
| 声明 | 精确字段/角色/类型、request/execution pin、prepare timing五字段和分段和、source返回与顶层调用数/完整性/接受标志/状态 |
| 来源 | 当前binding与归档前后内容、独立source execution pin、来源对应、外层wrapper耗时、source与kernel调用记账及接受投影 |
| kernel | solver spec/budget/scale、原生状态/界/gap/目标与完整赋值、所有约束残差和integrality、完整witness及chronology/terminal carry |
| 资源 | 精确timing inventory、builder次数与嵌套时间、wall门、生命周期peak单调性、core payload精确字节、每个资源错误标记的计数与失败条件 |

同值但不同类型的数字和bool不能绕过合同；重新计算外部hash仍不能让错误数值或标志通过检查。
回放沿用原阈值和resource budget。时间相加仅用1e-6秒处理浮点加减舍入，不放宽wall预算。

## 失败证据与结果解释

没有完整source返回时，声明调用数必须为null、完整性false并保留source_return错误。
没有完整kernel返回时，source/kernel调用记账继续unknown。timeout、partial native evidence、
缺界、assignment失败与资源拒绝不能升级为接受或数学不可行。
历史post-source/post-declaration失败即使来源文件后来恢复，也保持原unresolved结果。

声明与source层的静态拒绝标记使用有限词表，重复标记被拒绝；`source_binding_changed`
必须与前后binding差异对应，`post_source`的数量严格等于事后binding缺失的指示值；
完整source/inner返回不能带相应missing-return错误，无inner返回不能声称验证inner时异常。
记录含result binding/acceptance mismatch时不能获得“一致的完整记录”结论，即使执行者
当时正确拒绝了它；原始日志仍保留，这不等于判定求解数学不可行。
异常prefix另保留异常类型和诊断文本；回放只检查类型、阶段与记录相容性，不能认证历史异常
确实发生。给成功记录加入未注册错误或与记录矛盾的静态拒绝标记并降级接受标志，不能通过上述门。

prepare返回也必须保持solver_calls为严格int零、mechanism_initial_state=true，
observed_power_mapping/normal_assignment_verified/formal_result=false，才可进入source数值回放。

`archive_consistent`表示当前可重建输入与记录各字段一致；`accepted_record_reproduced`额外要求
三层接受条件全部复现。`source_input_binding_verified`指当前重建输入，不能证明历史执行者身份。
资源数值和耗时只核记录内部一致性，不认证真实进程测量。
`solver_calls_by_replay=0`；native_execution_authenticated、resource_measurements_authenticated、
resume_authorized、formal_result和security_certified均false，optimality/infeasibility certificate均null。

## 验证与下一步

tiny正例使用完整prepare/source/native求解与一次性日志，随后禁止所有执行入口和solver再回放。
测试覆盖current head、独立pins、重新hash后的三层数值与flag篡改、timing/peak/payload、
timeout/缺返回/失败来源恢复、声明文件在回放中变化。公开loader/package仍为synthetic夹具。

当前仅同步回放；prepare及年度快照、模型重建和整个SQLite目录尚需纳入worker/controller的Job预算。
下一必要工作是连接流式声明日志与独立replay的固定worker分支及controller，保留原预算，
在新的non-authoritative root中验证真实H25全链。现有真实H25证据仍止于完整prepare。
current/四臂、恢复右删失、风险分母、科学注册与正式启动门继续开放。

## 开发审查记录

首轮迁移的49项测试通过（301.99s）。pre-seal审查随后发现：仅凭错误tuple存在可伪造降级拒绝，
且replay遗漏prepare role的显式消费门。已按上文有限词表/静态错误投影和prepare role门修复，
加入声明层专属及finding反例；首轮结果不能替代最终候选验证。

源码SHA256：`d37f3ad8465ff87227ddaa1813bd98fd6a1ee3d42e79f51b294f3aa0e770e7f6`。
测试SHA256：`8919bdf46045b0fd3fa1d3afc851cfe86e3e04ca16f4297e379870a83b129521`。
这些是开发记录，不是production seal或official review receipt。

修复上述两finding并扩展后，78项通过（470.99s）；命令为
`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_declared_replay_stream_v1.py -k "declared or prepared_role or fabricated_source"`，
其中 `declared` 匹配文件名，因此实际运行当时全组78项。独立finding targeted为15 passed,63 deselected in95.80s。

旧相关回归命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_replay_v1.py tests/test_rq2_grid_evidence_replay_v1.py`，104 passed in98.69s。

末次phase审查再新增2项反例，修复前明确复现2 failed,78 deselected in14.73s；
只修上述post-source和validation阶段投影后，按影响范围补验证，不把此前78项当作最后两行修复的直接证据。

最后修复后的命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_declared_replay_stream_v1.py -k "source_exception_phase or post_source or post_declaration or missing_inner or missing_source or owned_record or fabricated_source or fabricated_declared"`，
16 passed,64 deselected in103.32s。覆盖两个新增反例及正常回放、缺返回、真实历史失败恢复和伪造拒绝。
旧五批74项工件bytes/hash一致，`git diff --check` 无错误；无真实H25或formal run。

末次独立只读 R3 pre-seal 复核：`source_exception_phase or post_source_failure_not_promoted or missing_inner_return or post_declaration_failure or owned_record_replays`，
6 passed,74 deselected in42.79s，核对最终源码/测试SHA一致。两轮findings已闭合，无开放实质代码finding。
这仍是限定pre-seal意见，不是official verdict、receipt、seal或运行授权。
