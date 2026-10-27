# runtime import：单次CPython stack诊断

2026-10-27，DRAFT_NONAUTHORITATIVE。27/27 unit、startup discovery/admission成功，首次实际import_discovery超时且无stdout/stderr；随后phase-marker trace的两次登记均因30000UTF16帽被拦，未启动child。三份失败及压缩比对费用保留，不继续该trace后继，不扩大任何旧帽。

本scope回到较短的原v3 probe主体，另建core v9、probe/parent v6及独立stack root。只新增builtin faulthandler：两种case均import该CPython builtin leaf，仅import_discovery启动一次1秒dump_traceback_later（repeat=False），finally取消。该watchdog为CPython native观察线程，不是科学模型/solver线程；不把Python current_frames单线程检查称为所有native线程认证。新增叶纳入新的startup profile，不能复用旧画像。

完整路径：登记实际源码/transport/pins → 独立startup discovery → profile admission → 唯一import stack child → metadata保存。最多2个cold child、并发1；第二child最多2次ENTRY exec和1次adapter import，3秒内完成或由原bounded parent终止。允许预期timeout并保存真实CPython stack、原stdout/stderr/exit/parent清理；无child报告时self-close/owner阶段保持未知，绝不由parent HANDLE关闭补造。此为有界瓶颈观察，不是原import验收重试或放宽原10秒帽。

static≤12s、总≤12s、unit/pytest0；登记≤2s、startup≤3s、profile≤1s、stack≤3s、保存≤1s，余2s。任一admission/资源失败保存并停，不自动再执行同scope。root results/tables/staged_rts24_saved_fresh_runtime_stack_v1_non_authoritative ≤16文件/4MiB；command≤30000UTF16、payload≤131072、stdout≤131072/stderr≤32768。RAM仅观察。Payload comment等长空白化与原含位置AST/完整CodeType相等，保留原未格式化prefix；无新增压缩库。

继承guard实际累计、trace两次登记失败与0.2622036s压缩比对，累计不接受19条；所有旧原字节、未执行normal/六故障窗口及超帽保持。Source49/ENTRY/adapter/BS3/namespace2原bytes复用，epoch不变。Native仅原self query/cleanup与CPython watchdog；不构造模型/Highs/solver、不读P1、不执行hold/capture/replay/OwnedChild/Job/F。E/U、独立TCB/native/完整runtime/P1/role/permit/F/科学/资源/正式/run authority均false。
