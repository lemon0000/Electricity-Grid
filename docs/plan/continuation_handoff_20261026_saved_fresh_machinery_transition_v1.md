# C/F：Pyomo精确迁移、94回归与真实三cold

2026-10-26，DRAFT_NONAUTHORITATIVE。接续[取证交接](continuation_handoff_20261026_saved_fresh_machinery_diagnostic_v1.md)、[实现scope](staged_deliverability_c_saved_fresh_machinery_transition_scope_v1.md)及[机械封装后继scope](staged_deliverability_c_saved_fresh_machinery_transition_archive_scope_v1.md)。root唯一writer，独立只读PRE_SEAL，无official verdict/receipt/production seal。宽goal继续active。

## 已实现与已观察

新import policy v3为3797B／`1010bb4d10f29551ea3c4cdd639697ade004321fe70dcec0efe422e1b128acb9`。三函数literal固定根，旧v2和所有冻结输入保留。factory只compile固定的两Pyomo源码，建立finder/loader/全局warning函数的code计划；源码不exec为预期对象。

guard强持B、hooks/path/cache/modules容器与对象，只允许观察到 `B → B+M → D+B+M`。busy内观察序列、类/实例/registry/direct globals身份，显式非busy authenticate核代码/default/closure，分别记录observed/authenticated stage。对已持函数的code/default/kwdefault setter/deleter事件sticky拒绝；原NumPy六次受控内省不增加。完整成功需final2/2、无pending、Source/external书挡及全部原终态条件。

当前Source49 epoch `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`：ENTRY/tests改变，其他47源/集合名称、原科学/wire API与CLI AST保持。逻辑回归94项（旧42＋新52），隔离环境下实际94/94通过、无skip，admission在collection_finish首test call前保存且末端pin一致。`--noconftest`、关闭第三方autoload及清空PYTEST_ADDOPTS/PYTEST_PLUGINS/ini addopts，避免未pin本地conftest读取。

三个真正fresh普通child均按预期终态：

| case | loader返回 | boundary | 关键证据 |
|---|---|---|---|
| normal | adapter＋guard | CLOSED，observed/authenticated 2/2 | Source49相等、code bookend成功，optional/blocked/sentinel/internal=1/1/1/6 |
| caught_effect | 不返回 | FAULTED，2/2 | 真实M.find_spec同code赋值被审计拒绝；异常被driver吞掉后仍不返回；code未变，mutation audit/injection各1 |
| blocked_installation | 不返回 | FAULTED，0/0 | 既有hook阻止安装，sentinel/optional均0 |

三例P1/actualF open、文件写/mutation及额外process观察计数全0，pipe/thread/HANDLE均关闭。内部科学API未装profiler，不作零调用证明；同code冷例只动态证明code setter，其他属性/删除分支为逻辑反例。峰值WS分别143,310,848／143,585,280／56,180,736B，仅观察，无RAM硬帽。

## 保留的记录与预算

实现root为`results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative`。首次collection target5.388268s超时，charge6.1048414，raw logs/exit/旧helpers全部保留。显式revision1把collection合入主组，94/94、charge6.218794；其本地conftest输入未pin，故保留成功记录但不当最终闭合。revision2登记隔离和admission书挡，在原repair25s内重跑94/94、charge6.4484841。cold三例合计capture charge6.8918396。未来raw流在exit内base64无损保存，历史独立log不改。

登记费0.1813344＋0.1401629＋0.1486545；机械封装前本实现账static13.4668328/60、pytest12.6672781/45，总26.1341109/105。上游全累计账static129.3531059、pytest353.8217016另行保持，原540/420/120不延长，9历史失败和旧8MiB超帽仍原样保留。新collection timeout为第10条不接受记录；原主组成功按原helper世代保留，未改accepted值。

旧实现driver的terminal文件预留存在确定性错误：44文件加saved实际2到46后，会按预留3误判49而拒绝。四helper已经被accepted repair/cold绑定，未修改，原driver saved/terminal未执行。独立机械封装后继复用其已pin oracle.verify与证据；旧实现根补PRE_SEAL后冻结44，仍≤48/2MiB；新机械根独立≤16/256KiB，不把组合文件数当原48内通过。

机械保存/重开最终以新根 `results/tables/staged_rts24_saved_fresh_machinery_transition_archive_v1_non_authoritative/saved.exit.json`、`terminal_repair.exit.json`为准，均实际accepted。原`terminal.exit.json`仍accepted=false：启动child前，严格重放将记账加法分组为a+(b+c)，与parent的(a+b)+c差3.55e-15；charge0.6197372、无report/process，完整保留。revision_02固定五原文件和新repair helper，只把已pin原controller AST中唯一AugAssign拆成同parent顺序两次+=，不增加容差。首次saved费2.9317292，修复terminal3.037705，原terminal＋repair=3.6574422/5s；两fresh oracle canonical完全相同，old44/Source49/external/controller/revision pins和HANDLE/pipe/thread均闭合。

最终实现账static20.400935/60、pytest12.6672781/45，总33.0682131/105；五次登记合计0.8150826/2s。上游全累计static149.7540409、pytest366.4889797，总516.2430206s；这些全累计不宣称在原static120帽内通过。原9失败、本实现collection timeout、机械原terminal失败共11条不接受记录都保留。原主组94成功但conftest未pin的记录亦原样保留，由隔离repair94替代作当前闭合证据。

实现root最终44文件/1,443,516B；机械root最终9/75,995B，分别满足本根48/2MiB与后继16/256KiB。组合53文件/1,519,511B仅报告实际，不称原48文件内完成或完整资源准入。原实现capture.py的saved/terminal从未执行；新controller的原terminal仍失败，只有明确repair后继完成fresh重开。所有resource/formal/actualF门持续false。

## 仍未闭合与后续

B四对象仅构造前现状持有，首次模块provenance、自锚和独立Source expected truth未认证；两个registry的深层mapping/callback及warning递归行为闭包未认证。无事件RAM/native ABA不在此证据范围，full finder behavior/transitive runtime/全资源准入仍false。当前新增结果只是可观察的精确绑定迁移和普通依赖导入，不是完整import capability、真实role或F权限。

下一步先读机械terminal_repair终态和本交接、核Git/进程并续账。保留原driver及失败，复用94/三cold/封装的准确范围；随后为真正cold-main/self-anchor及transitive globals/class/builtin/native闭包建立有限的根catalog与证据DAG，再连接successor context/request与真实producer/bootstrap、retained owner/ACK/one-shot permit。旧runtime v2继续UNDECIDED、旧v3 proposal整体admissible=false；actual F及科学/资源/正式gate均false，仍无正式运行授权。

Git只同步本轮实现、测试、两个新结果根、scope/交接与四导航短prefix。并行论文/文献/绘图及共享导航旧body保留；全局worktree仍可能dirty，远端hash以实时读回为准。
