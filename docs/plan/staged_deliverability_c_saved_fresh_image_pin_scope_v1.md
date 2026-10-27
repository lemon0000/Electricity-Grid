# B_S image pin：单次调用内纯bytes摘要复用

2026-10-27，DRAFT_NONAUTHORITATIVE。起点72fde56cfa8aaacb5eb1e8afa5e6da272d16fb9f，接续[64-open前缀交接](continuation_handoff_20261027_saved_fresh_audit_census_prefix_v1.md)。前缀image_digest为0.0284853s/64项，仅指示有限优化机会，不证明完整import瓶颈。root唯一writer、独立只读PRE_SEAL；旧census4与AOC1–5全部原字节/失败冻结。

独立候选`bootstrap_import_image_pin_v1.py`只改`BootstrapImportBoundary._image`：每次调用创建私有memo，对exact bytes复用原`pin(raw)`结果；每次以字面量复制返回独立dict，保持输出pin无别名且不增加builtin dict读取。非exact bytes直接调用原pin，不缓存可变buffer。tuple结构、顺序、所有字段与id读取、global kw的exact-bytes分支保持。无新slot/global，无跨调用或跨audit缓存，不改`_audit_entry`、ownership、metadata、cache/finder/Source校验或科学输入。memo仅由本次读取的完整bytes内容作key，SHA为纯固定实现；这是输出等价，不声称故障调用轨迹完全相同，不把被替换pin/sha的第N次调用副作用或任意RAM篡改视为合法等价前提。

依赖DAG：当前self字段与各binding行 → 完整原image tuple → canonical JSON → SHA → 原commit比较；只有相同bytes子节点的pin计算在本次调用复用。exact bytes不可变，后续调用重新取字段并重建memo；可变buffer仍逐次hash。代码/default/closure与所有原expected binding根继续按原顺序检查。目标是减少重复的短bytes SHA，不缓存整个image、最终digest、code图、路径、finder或current cache。

本轮路径：register≤2s → 9节点unit child≤5s → 独立PRE_SEAL记录/准入≤1s → saved metadata≤2s → terminal checkpoint≤1s；static≤8s（另2s余量）、unit≤5s、总≤13s。最多1个unit child，0 cold child、0 ENTRY exec、0 adapter import、0真实guard安装/self HANDLE、0模型/Highs()/solver/P1/hold/capture/replay/OwnedChild/Job/F。完整helper只在逻辑context定义与验证；core import不创建live runtime。失败/超帽create-only保全并停止，允许单次metadata终账，不原路重跑或扩帽。root `results/tables/staged_rts24_saved_fresh_image_pin_v1_non_authoritative` ≤16文件/2MiB，metrics≤64KiB，stdout65536/stderr16384，RAM只观测。

9节点覆盖：仅_image AST改变；完整tuple/canonical/digest独立原方法oracle；重复/不同kw、profile/source及global非bytes；状态迁移与所有被image读取字段的相邻调用替换；bytearray/memoryview变异与不支持类型异常；返回dict无别名；原pin调用顺序、首次unique异常与每次清空；完整candidate helper源代码/默认根proof、metadata/finder bookend与stale commit；固定三轮真实SHA/JSON成本。set/del是直接调用真实classifier的逻辑注入，不安装进程audit hook；kw内容漂移/finder/stale commit直接执行真实bookend。方法fixture从真实factory字段及源码global/class行数构建，仍是合成对象，不是完整guard/runtime证据。Source49不变、原检查AST保持可复用，当前9项不冒充旧14/其他回归重跑。

成本固定：代表pre-import factory形状，128次image+digest/variant/round，共3轮，顺序old-new/new-old/old-new；另空binding小形状各20次，记录小case退化。两variant在同一fixture上求原tuple与canonical/digest，相同轮外先核结果相等；计时内使用真实pin/SHA/JSON，逻辑调用量另用纯代理计数。采用候选进入cold后继的必要条件：语义/proof/反例均过，三轮new总时间与中位数各≤old的95%。未达则记录失败且不采用，不追加测量等成功；达到也仅允许后续独立cold范围设计，不证明全import提速或F准入。

前驱AOC5 checkpoint全部root/input/helper/source pins重开；旧root inventory严格为原24项加checkpoint，新root登记前严格仅driver.py。登记预载固定stdlib根及其已加载依赖，记录条件性disk origin、source与存在的cached-bytecode pins，并纳入input；unit开始/结束重核同一origin表。ast/copy/threading/unittest、core所用ctypes/dataclasses、失败报告与JSON/statistics等均在此条件TCB内，builtin/frozen由已绑定runtime条件承接，不声称独立TCB认证。累计static231.03523670001164、pytest366.48897970000326、unittest67.59156209999855，共665.1157785000134s，不接受25条；新帽不重置前驱费用、旧120/540/import8MiB超帽或任何失败。Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875及49份raw不变。编辑/审查/Git、Python初始启动与最终exit写入不计capture，不是完整wall。39项并行dirty保留。

E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false；无production seal、official verdict/receipt或实际运行权限。整体F性能审查仍未完成。
