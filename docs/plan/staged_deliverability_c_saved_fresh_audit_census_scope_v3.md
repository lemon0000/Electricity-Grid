# audit census第三后继：sentinel replay与完整schedule

2026-10-27，DRAFT_NONAUTHORITATIVE；起点5627d0dc9238c558bb9faf887bc15529e3fb6639，接续[失败交接](continuation_handoff_20261027_saved_fresh_audit_census_wip_v1.md)。root唯一writer、独立只读PRE_SEAL，无official verdict/receipt/seal/run authority。AOC1源码与8文件、30049拒绝、1.7074301s费用全部冻结；本v2不改旧字节。

v2 size admission得到30013/30000、accepted=false、static0.4597152s，0unit/cold，原输入和三文件冻结。v3继承same-creator与primary修复，并补安装过程duplicate/nested sentinel严格拒绝，以及1→8→16→…→56→64唯一frame schedule（含漏项/重复/跳项反例）。core17/probe14/parent14/BS census3成组迁根。14节点还保留foreign/reentrant、preseed、cause叶、bucket倒退、class非method/import oracle。所有旧guard检查、64 guard-passed定义、observer顺序、busy外输出、强持roots、因果异常上限及无watchdog行为继承[v1范围](staged_deliverability_c_saved_fresh_audit_census_scope_v1.md)；仅在测试与只读复核后可称闭合。

新transport先形成本candidate的comment-filtered intended payload，再只压缩prefix同一物理行token之间纯空白，最后以该minified prefix作zdict压payload。保留换行/缩进/COMMENT token，核完整(type,string)序列与AST不含位置；prefix列位置及co_positions/linetable可变化，不声称prefix exact CodeType相等。payload针对本candidate逐字节、含位置AST与exact CodeType保持，不跨版本称相对AOC1原bytes相等。child从实际argv[6]唯一loader marker取同一prefix；bootstrap self-check使用实际minified -c code，startup必须新发现。

本版仅额外把loader内部两个RuntimeError文字缩为OS/cap；错误类型、触发分支、zlib参数/容量上限及payload均不由该文字变更改变。单测恢复这两literal后与parent13的transport AST完全相等，不能借此豁免其它codec变化。

路径：size_admission≤2s（0child，先保存before/after prefix/dictionary/payload/packed/transport pins、完整最长argv UTF16与有限roundtrip）→register≤2s（必须重开size输入pins与accepted，漂移拒绝）→unit capture≤8s→PRE_SEAL≤1s→startup≤3s→profile≤1s→唯一prefix child≤8s→saved≤2s→checkpoint≤1s。static≤22s、unit≤8s、合计≤30s；static最坏20s，另余2s。若尺寸>30000或阶段失败/超帽，create-only保全并停，不运行旧unit或放宽帽。新执行字节也冻结。

root `results/tables/staged_rts24_saved_fresh_aoc_v3_non_authoritative` ≤26files/4MiB（原24+size JSON及1文件余量），command30000、payload131072、stdout131072/stderr32768、profile1MiB/module-cache4096保持。12 census帧、单帧2048/合计24576保持。1unit+2串行cold；unit legacy ENTRY≤12、actual ENTRY≤2，discovery0；adapter≤1；0model/Highs()/solver/P1/hold/capture/replay/OwnedChild/Job/F。RAM仅观测。

前驱static220.08536410000966、pytest366.48897970000326、unittest54.345750399999815，总640.9200942000127s、不接受24条，全部续记不退款；旧120/540/import8MiB超帽不变。Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875与原49 bytes不变。编辑/审查/Git、Python初始启动和最终JSON写入不计capture，不是完整wall，无模拟小时推进。

E/U、TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false，prefix与方法级fixture不证明完整import或资源准入。39项并行dirty保留。
