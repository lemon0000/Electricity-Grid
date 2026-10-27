# runtime import timeout：仅定位pre-import阶段的有限后继

2026-10-27，DRAFT_NONAUTHORITATIVE。前驱runtime_guard首组27/27通过，startup discovery/admission通过，首次import_discovery在9.516213s超时：child被parent终止，stdout/stderr均0，无child self-close见证；父HANDLE/stdin/reader/pipes终态。前驱链停止，原helper/transport/registration/报告全部冻结，费用不退款，累计意外不接受记录17。

本后继只回答耗时是否发生在adapter import之前，以及具体哪个连接边界。新增core v8、probe/parent v4、trace controller与独立结果root；B_S v3、namespace v2及Source49原bytes复用。时标写已有stderr，每次一行canonical JSON，最多32行/4096B，记录step与相对perf_counter秒数；不写磁盘日志、不设置profile/trace、不产生authoritative clock声明。

完整路径：登记pins/实际transport → 独立startup discovery → profile admission → 唯一pre-import child → 保存原streams/exit/phase timings/pins。最多2个cold child，并发1；每child最多2次ENTRY exec，**adapter import 0次**。第二child完成owner adoption、B_S安装、audit handoff与PATH6后，主动抛固定diagnostic_stop_before_adapter并按原runtime cleanup路径收尾。它是诊断预期停止，不是B_S成功、LIVE或F验收。

step映射：0 manifest前；1 self begin；2 inputs LIVE；3 namespace helper已装；4 ENTRY ready；5 B_S helper已装；6完整proof已核；7 transfer begin；8 runtime ADOPTED；9 boundary protocol已备；10 policy已读；11 B_S factory返回；12 audit handoff完成；13 PATH6 ready；14主动stop；90 exception；91/92 runtime close前/后；93 namespace close后；94 inputs close后；95 lease close后；96 DLL cookie closed；97 report前。所有elapsed仅诊断观察；缺失step不补造，原timeout不能由后继成功反推。

static≤16s，总≤16s，无unit/pytest；登记≤2s、startup≤4s、admission≤2s、pre-import≤4s、保存≤2s，留2s失败余量。任一超帽/异常保留raw并停止，无相同child重试或扩大单例帽。结果root results/tables/staged_rts24_saved_fresh_runtime_trace_v1_non_authoritative ≤20文件/4MiB；stdout131072、stderr4096、payload131072、command30000UTF16。原parent bounded drain/capture复用，comment等长空白化须含位置AST和完整CodeType相等。RAM只观察。

保存前驱完整result map、全部input/helper pins、原Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875、费用与17条不接受记录；新帽只覆盖新诊断，不称旧110或任何全累计帽通过。Native仅原self query/handle cleanup，不构造模型/Highs/solver，不读P1，不执行hold/capture/replay/OwnedChild/Job/F。所有E/U/TCB/native/full-runtime/P1/role/permit/F/science/resource/formal/run authority保持false。原scope的normal/六故障窗口仍未执行。
