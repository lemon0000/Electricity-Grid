# C：F 的只读 adapter 与启动协议组件开发合同

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[F范围/预算](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)及[设计交接](continuation_handoff_20261025_saved_fresh_scope_budget.md)。本次实现原计划的第一层接口：B/C/E只读连接、完整载荷绑定、标准库启动前核验、运行中metadata安全会计。本页是开发接口和验收索引；原范围、总预算、原source/P1字节、模型、策略、容差及门禁保持。

## 交付范围

原预留的`src/staged_rts24_saved_fresh_adoption_v1.py`、`experiments/staged_rts24_saved_fresh_adoption_v1.py`和对应测试现已存在，选定来源仍为原45＋原定四路径共49，不引入新runtime来源。本页不是第50个runtime依赖。三个文件处于未seal的同一provisional draft；本次测试字节另存独立snapshot，后续修改须保留旧snapshot并重新核对受影响证据，不能沿用旧测试结果代表修改后字节。

src adapter调用原B独立政策生成query、原C重建raw/snapshot/import/KKT及原journal_v2.reopen。21个typed证据和最终state精确连接，完整19项metrics、六prefix及最终trusted tuple保留。D四行仅受完整683文件库存保护，未加入本组件科学重算。当前只运行普通同进程adapter检查，没有新增五小时fresh进程或父端采用流程。

ENTRY当前提供启动前协议函数，直接作为脚本执行会明确非零退出；它尚未实现stage supervisor、`--parent/--fresh`编排和trusted invocation。不能把这个脚本当作可运行F，也不能从相等的payload或一份context JSON推导进程/采用成功。

## 接口不变量与验收

| 项目 | 必须满足的接口行为 | 对应检查 |
|---|---|---|
| 外部caller锚 | trusted initial capture在读锚前持有其identity/祖先与P1根，冻结完整683 pins/metadata/directories、fixture/预期query/state、source、六prefix及trusted tuple；角色`hold`只消费该外部canonical image | 同字节新identity、caller各字段晚变、两侧同改caller标签均拒绝 |
| 完整科学载荷 | parent/fresh纯载荷比较须同时绑定external caller image/SHA、context/source/input pins；19 metrics、21 refs、六prefix、完整trusted tuple逐域canonical相等 | 每个metric漂移；两侧同错summary/audit/ref/prefix/trusted且保留正确caller标签均拒绝 |
| 历史对照含义 | caller image从锚定683库存取得历史完整metrics和原request/result引用，作额外固定baseline；`replay`仍实际执行独立B/C/E及typed join | 一个真实保存parent adapter完整metrics匹配；禁止native/spawn/journal/CAS writer/publication |
| 启动前核验 | bootstrap先核固定继承source清单SHA、49源码、compute executable bytes/identity/version、原controlled environment、完整P1锚和canonical context；trusted initial capture才显式导入科学定义 | canonical/duplicate/nonfinite、source/exe/env/input漂移、独立短Python仅import ENTRY不加载src/Pyomo/Highs |
| 范围与时间 | 实际F输出固定原draft_01；普通pytest只准专用系统tmp output；冻结输出父链及`invocation_started+180`，creator要求目标尚不存在 | 任意repo/src/其他result/temp根、加长deadline、模式漂移拒绝 |
| argv与角色 | argv从已核raw context+同一SHA生成；实际main路径/字节和sys.argv全展开匹配；production角色另拒绝pytest mode | 跨context SHA接线、错main/argv、实际argv正确但test context不能进入执行/采用 |
| 安全会计 | 只收创建进程/线程持有的不可变validated context，固定全局O及其目录identity；只lstat/size/count，返回safety_only/unknown/content_read=false | 同步改可变dict和root、层级根误传、根替换、额外路径/hardlink/超帽拒绝；内容reader被禁时仍能安全扫描 |
| 双层预留 | 四份128KiB/四槽共512KiB在8MiB/64内；已有pending按实际bytes及一个槽收费，不能双计或漏掉内层父目录 | record超限、final/pending冲突、剩余reserve不足与独立fresh_parent路径 |
| 失败出口 | 科学重建异常仍做末次source/input书挡；主错误与书挡双错分别保留，不推断数学不可行 | 两类故障注入，不继续fresh或补写成功 |

纯比较函数只返回`payload_byte_equality_verified`，显式保持`saved_P1_fresh_process_verified=false`、`saved_P1_parent_adoption_verified=false`及全部P2/science/139/F-X/resource/formal false。metadata safety scan不成为最终稳定库存。完整quiet后的真实库存、owner来源与采用只能由后续层提供。

## 普通检查预算和保存

每个普通pytest命令硬帽90s、不自动重试；collection限15s，原保存标准库核验限30s。首轮adapter 63项与后续protocol 68项的原始stdout/stderr、exit、source pins均保留，另存首轮及最终draft的三份源码；中间68项仅列历史日志/pins，不列最终通过或完整字节复现证据。最终collection有85新＋9原回归，共94唯一nodeid。protocol的70项终态通过；其余24项组合命令到90s硬帽，保留timeout物证、不计通过，按原collection顺序固定拆互斥12＋12，仍各90s。最终70＋12＋12的并集恰为94，不含超时重叠项。相同最终源码批次已花67.25＋90.047s，加后两组最坏180s为337.297s，仍小于原360s普通测试预算；加30s静态和未执行F的180s也小于570s，不扩大预算。split_admission_04在执行前保存具体nodeid、源码pins和此预算核对；任何后续失败继续保留并重审，不自动顺延。

本组件只做普通开发验证，测试wall不作为F整链性能测量。原条件compile42/import21等基数不冒称本次新增实测调用数；新source/canonical/metadata/失败费用须在完整F实测前重新核对。真实F的一次180s、完整570s及40/50s请求仍是下一层准入合同，当前没有执行该测量。

旧发布路径、原三导航body和P1全部683文件须保持；原保存检查器继续使用`D:\Miniconda3\envs\compute\python.exe -B`。只读独立PRE_SEAL findings闭合后保存组件检查点，不生成official verdict/receipt/seal或运行权限。

## 完整F仍需实现

下一步是stage-aware retained-owner执行40s活跃/50s内层/180s总截止、两层真实nested Job及完整历史成员、启动capture与失败cleanup、角色间的create-only候选/记录、quiet后完整输出库存与最终父端采用、四份记录长度oracle和外部trusted invocation的controller资源/尾部I/O控制。异常发布和全链成本也须纳入原矩阵。上述未实现部分仍OPEN，`F_launch_admitted=false`；同进程parent adapter和历史fresh对照不关闭它们。
