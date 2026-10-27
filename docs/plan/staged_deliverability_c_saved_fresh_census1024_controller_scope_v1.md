# 后续1024窗口的独立控制器检查包草稿

2026-10-28，DRAFT_NONAUTHORITATIVE，尚未实现、登记或运行。承接[pin方法交接](continuation_handoff_20261028_saved_fresh_pin_memo_v1.md)。目标仍是取得真实1024个guard-passed open或1024前自然返回的完整终态，不把方法测试替代actual import。原NFC v1-v3、metadata trace和pin-memo包保持冻结，原30秒包实际17.533584500015422s、unit7.3020775000040885/8，全部失败、费用与未用余额保留；不挪用旧unit余量，也不将旧失败改成通过。

## 决策与实际依赖

不接入pin-memo候选：完整check配对比为0.7796472410277864和0.9933261750405756，不能把总0.8733857582172452解释为稳定收益；每次需要39577485B raw cache且未测whole-controller收益。新执行路径沿未缓存的原fresh读取；不减少原legacy checker的任何观察点。

控制器以冻结NFC v3的check(reg)及其固定registration作为一个leaf，每个必需的phase/child bookend仍完整调用，不随新版本递归增长checker链。新源及当前artifact另外验证。pin-memo只作为历史ledger端点和八文件archive绑定，不执行其候选或把它的全部checker重新嵌套。注册时核历史证据保全、执行依赖闭包和Source49；每phase再核固定leaf及新输入，历史ledger的哈希绑定不能授予当前runtime权限。

拟新root为results/tables/staged_rts24_saved_fresh_nfc_v4_non_authoritative；core31/probe29/parent28仅由固定constructor迁移root/core/probe路径，helper仍冻结的census1024_none_v2原bytes。14节点测试和native fixture走独立路径，保留exact source constructor与六项native-audit逻辑guard，不能只复用v3 stderr的OK。parent仍核完整profile admission，当前无model/solver或P1/实际role/Job/F调用。

## 全路径与新分配

前驱ledger端点为pin_memo_v1 checkpoint SHA e340c6ee3758175c78c2992c57586000a021ead268158e3e67571bb16243297b；累计static323.3060006000553、pytest366.48897970000326、unittest90.0103723000102、总779.8053526000688s、不接受34条。新增预算单独分配，不重置原预算；本草稿不是任何gate的通过或实际窗口运行许可。

拟DAG为size≤2→register≤2→唯一完整14节点unit≤8→PRE_SEAL≤2→startup≤3→profile≤2→唯一1024/return≤8→saved≤2→checkpoint≤1。static≤22、unit≤8、总≤30s，最多1 unit child+2串行cold child。NFC v3的4.75s unit已失败冻结，不能延长它；此处是独立后继整个控制器包。依据：v3 runner本体2.004s；固定check观测0.5567至0.7123s，四个fresh bookend最多约2.85s，再加启动/收尾0.7s约5.55s，8s留控制器和系统不确定性。不得将该估算称为实测总wall或保证。

冻结leaf规模为每check约2496次显式Path.read_bytes，不缓存读取；unit父/子前后四check约9984次，再加新源及phase artifact检查。必须在实现后重新核实际DAG/调用量、collection、command尺寸与输出布局，不能只凭公式启动。两cold上限与旧PFC流程相同；窗口limit1024、最多1023次窗口内physical open、或自然返回时诊断stop；完整primary/secondary、自身HANDLE各close1与父端pipes/readers/HANDLE终态是必需项，timeout/partial/unknown一律不接受该诊断。

拟采用15文件packed布局、root≤4MiB；单文件/流caps、stderr24576B census/32768B总帽、stdout131072B、decoded131072B和命令30000 UTF16保持，写前预留退出和checkpoint。Root size和实际最坏registration/packed-exit尺寸须先准入。RAM/完整import耗时仍未知，direct RSS仅记录且不赋予资源准入；64MiB cache候选不进入此路径。

在真实窗口之前必须完成稳定source/input绑定、完整unit终态（含最终report与子进程exit0）、独立只读PRE_SEAL findings闭合、新startup/profile回读和live process检查。任何失败保存原raw/partial、费用与拒绝checkpoint后停止，不重试、不续时。新包最坏把累计capture上界推至809.8053526000688s；尚未花费该新预算。旧原包剩余12.466415499984578s及unit约0.6979225s保留，不转移。

Source49及所有旧record原字节、39项并行dirty保持。无production seal、official verdict、实际P1/OwnedChild/Job/F、长实验、native校准、外部下载、科学/资源/正式或run authority。实现和审查仍需按agent.md第7/9节完成，本草稿不能越过任何依赖门槛。
