# C/F：真实 import 栈已进入 cache 路径检查

2026-10-27，DRAFT_NONAUTHORITATIVE。接续[namespace成本交接](continuation_handoff_20261027_saved_fresh_namespace_graph_timing_v1.md)。root唯一writer，独立只读PRE_SEAL；无official verdict/receipt/seal或运行授权，宽goal继续active。当前只形成真实import内部的有限诊断，完整B_S、LIVE、实际F与正式门槛仍未闭合。

## 已取得的证据

[RTI v1](staged_deliverability_c_saved_fresh_runtime_import_timing_scope_v1.md)登记被command≤30000 UTF16挡住，未执行unit/cold。原controller、六份helper snapshot及失败均冻结；原失败只写generic AssertionError，后续独立[size admission](staged_deliverability_c_saved_fresh_runtime_transport_size_scope_v1.md)重构同一原transport，明确实际长度为**30044**。固定8个纯静态候选、0 child，原bootstrap prefix作zlib只读dictionary的mem8/default候选为29560，逐字节payload roundtrip一致；没有扩大帽或引入其他codec。

[RTI v2范围](staged_deliverability_c_saved_fresh_runtime_import_timing_scope_v2.md)采用core13、probe/parent10，BS timing1与namespace timing1原bytes复用。新实际命令**29564/30000**，登记先保存transport及command_size。5/5逻辑unit终态通过，0failure/error/skip，charge**1.3104663/4s**；capture child正常exit0、未kill，HANDLE/pipes/readers均终态，peak working set44576768B。测试覆盖原BS guard AST、arm/import/cancel/trace错误顺序、五default根替换、held stderr身份、mixed/partial stderr与完整报告反例、dictionary有限回放及含位置AST/CodeType。

完整child报告现在须核canonical newline、schema/case/epoch、18个false gates、status/exit、kernel PID/creation/image/command、phase、close_calls与清理字段；self-close witness须[1,1]、resource CLOSED、DLL cookie关闭、alias移除。无stdout的partial不能产生self-close witness。独立只读PRE_SEAL无cold前must-fix；这不是official verdict或运行权限。

真实Windows startup discovery及profile admission均完成，证明该命令的dictionary重建和bootstrap pin链实际可用。唯一actual import诊断随后运行：

- controller charge **7.6513574/8s**；内部parent charge **7.1800347/7.6519149s**，两者边界不同，均非模拟小时。
- 只收到`loader_ready`与`before_adapter_import`，没有`adapter_import_returned`或后续stage。
- import开始后2秒watchdog触发。栈明确经过`diagnostic_import_once → import_module`，当时下游在加载PYPOWER的`qps_pypower`，顶部为`_check_cache:297 → pathlib.is_relative_to → __eq__`。
- child最终被预算停止，exit1，stdout0，stderr**8977B**。父端完整保存raw与pin；stream未截断，faulthandler栈自身末尾有`...`，不能称完整无省略调用栈。
- 父端process HANDLE/stdin/writer/readers/pipes均终态，无reader/cleanup错误。没有child report，**child self-close状态未知**；不推断child handles、DLL cookie或alias已自行清理。
- 受控faulthandler加载、arm与触发已有真实见证；实际cancel/finally未获见证，因为import未返回且child被kill。异常顺序与取消仅有逻辑unit证据。

这个单样本把下一调查位置推进到import内的重复cache路径检查。它不证明该位置占满本次约7秒、原9.516秒，亦不证明其它identity/commit/import成本可忽略。Stage时间含trace I/O与相应步骤，不是纯CPU。实际import RSS未记录，不能用unit峰值替代。

## 保存与账

RTI1 root `results/tables/staged_rts24_saved_fresh_rti_v1_non_authoritative` 原4文件保持，失败费**1.2287622s**不退款。Size root `results/tables/staged_rts24_saved_fresh_rti_transport_v1_non_authoritative` 5文件，static **0.3273174/2s**，8候选全部只做静态解码。

RTI2 root `results/tables/staged_rts24_saved_fresh_rti_v2_non_authoritative` **24/24文件**，不继续添加。unit、PRE_SEAL记录、discovery、profile、import_timing、saved均accepted；其中import_timing的accepted仅表示partial诊断保全与父端收尾符合本诊断合同，**不是cold import验收通过**。

`saved_report.json`保存metadata与观测；随后独立执行的`experiments/staged_rts24_saved_fresh_runtime_import_timing_checkpoint_v1.py`生成`checkpoint.json`，charge**0.3849096/1s**。它再次核Source49、所有注册/阶段pins、raw streams、root限额，并补足当前解码payload按comment spans逐字节校验。checkpoint在saved之后，不反称其已受原saved.exit绑定。

RTI2含checkpoint累计static **10.9398491/18s**、unittest **1.3104663/4s**，总 **12.2503154/22s**。全历史累计static **206.4446454000165**、pytest **366.48897970000326**、unittest **51.491678900001716**，总 **624.4253040000215s**。累计意外不接受**22条**；本次预算停止的import是预定partial诊断，不洗成import成功，也不删除旧失败。旧120/540/import8MiB超帽保持。编辑/审查/Git、Python初始启动和最终exit序列化不计capture，不是完整wall。

Source49 epoch仍为**acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**，49个原字节逐项不变。39项并行文稿/图件/文献dirty保留；只发布本轮范围及四导航新段。

Git whitespace检查中，size root的`payload.snapshot`第423/619行含注释等长替换的尾部空格，是位置AST/CodeType保全所需原字节，保持不动；其余发布范围单独检查。该例外不改变snapshot pin或运行证据。

## 下一步

恢复先读本交接、RTI2的checkpoint/saved_report/probe_import_discovery.receipt及raw stderr，核Git/process与source pins。不重跑RTI1或同一cold child，不扩大时间/命令帽，不采用此前无真实SHA收益的NSv3。

先做`_check_cache`同一次调用内路径构造复用的有限等价与收益验证，保持每次全cache扫描、原初始项identity、后来项finder/path、每audit的identity/commit/ownership检查，暂不跨audit缓存。原函数已在循环外求EXE.parent；不能重复计为节省。`is_relative_to`内部仍构造other并遍历parents，外层构造次数减少不等于总成本同比减少。应覆盖空/小cache、双root、相似前缀、相对/drive/UNC、大小写与`.`/`..`、finder类型/path及相邻audit间变异；以冻结原函数为oracle，不改路径判定语义。先固定有限次数、预算与失败停止，再考虑一次新实际import的成本证据。

E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority均仍false。当前剩余关键动态缺口为完整B_S import、M/D迁移在此runtime的闭合profile、NumPy政策及完整runtime收尾，之后才是实际producer与F。
