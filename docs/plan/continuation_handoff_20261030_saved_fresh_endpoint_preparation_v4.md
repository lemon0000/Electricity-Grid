# F：薄入口与 pre-manifest endpoint 接线交接

2026-10-30，DRAFT_NONAUTHORITATIVE。持续推进goal保持active。承接 [route v2](continuation_handoff_20261030_saved_fresh_preentry_route_v2.md)；原八组修补与cleanup binding历史保持。当前完成endpoint/Core源码接线、薄payload容量与合成验证。新增模拟跨度0h，NFC12未重跑；完整F尚未启动。

## 实际进展

- [Core51](../../experiments/staged_rts24_saved_fresh_pre_entry_lease_v51.py)先分配lease/endpoint anchor，再Open-only获取mapping/mutex/view、核header/descriptor与child identity，之后才开放manifest、self resource和Source49。manifest投影消除自身SHA循环，物理header/argv仍绑定完整manifest pin。
- endpoint的执行根、镜像、每资源close-issued状态及两次ownership record已接入local/runtime cleanup。真实resource.owner决定提交；pending record与镜像漂移保留失败，同时按held根清理。Native、endpoint、namespace/B_S和hook各自保存错误。当前只是相应合成效果域的证明。
- [薄suffix](../../experiments/staged_rts24_saved_fresh_pre_manifest_entry_probe_v1.py)由原transport compiler拼接于Core后，已有组合编译和同一Core namespace中的成功/失败寿命控制测试。它不是单独可运行文件，也不承担完整角色dispatch。
- [role runtime v7](../../experiments/staged_rts24_saved_fresh_full_context_role_runtime_v7.py)只将mechanical cleanup绑定更新为Core51 exact bytes/SHA，并保持旧角色门禁。完整角色入口、Guard2与真实Native等价仍OPEN。

Core51固定124483B / `dc1705881a9f8e557e2e8fab2a777a5914c72aa9f1a16622576055495f28602c`；suffix955B / `55165ba83efde0db461be26278ebe0ed44d8fe3fcc15c55ce204f8cc32836d74`。

## 压缩阻塞已解除

真实builder与独立bit-string/XZ解码均核同一组合：

| 对象 | bytes / units | SHA256 |
|---|---:|---|
| payload | 121138B | `876049196cad27d7b145faf052a15aea67b16bd828e83f029aaab334b65d4c6d` |
| XZ | 24816B | `0c9943e086d78d2efcd2282a45c62c81525a1542935ef300ad9582155638655c` |
| transport | 48477B | `4aeffabc33c004243014bec27115918237dd4af8a076e53c12e90324c1b375dd` |
| full argv | 21000 UTF-16 units，含NUL | 含占位值，仅容量预留 |

原raw131072B、XZ26214B、UTF16 30000帽保持；XZ余量1398B。旧Core50+probe42的26312B拒绝记录完整保留。生成transport从未执行；新组合成功不授权真实entry或full F。

## 失败与普通验证

v1首次register后冻结，99方法产生5error+1failure：role v6仍绑定Core50；仅opcode的STORE故障标记未命中。立即checkpoint，保存root5/988785B；CP14340B / `629a459c8405d7836812b752121b59ad7c4f5a6f1fe4a8799a9c66c83c9ee9e8`。register1.5128677999964566、inspect2.796233500004746、unit9.20010330000514、checkpoint0.6601587999975891秒，实际包费用14.169363400003931秒，不退款。

v2在独立successor中更新role exact pin与故障定位，保留Core51、suffix、endpoint fixture及source cleanup v7字节。99方法全部通过，0error/0failure/0skip；包括30 endpoint方法、原32 cleanup、26 role与11 join方法，并保留原48个cleanup故障场景。实际提交前故障见unit contract：`line`事件、payload line1437、marker496、STORE_ATTR offset500、journal_records=1、owner_same=true。该结果证明已追加record而实际owner仍为前驱的故障窗口，未声称opcode事件已发生。

原测试文本14648B / `6114f48bf417fc5659baa06f2781140db425599405b84ba7d2bb1e66b42bdc7c`。测试在控制进程内使用私有模块copy与明确synthetic叶函数；阶段内validation/project/fixture child均0、项目Native/P1/Source49执行/solver/full F均0，未调用Capture1/DRAIN1或Native sampler，未测连续RSS。

v2源码审查的must_fix_open为空，但PRE_SEAL记录阶段6.536766900004295秒超过原6秒，立即保存拒绝并checkpoint；CP15346B / `fd9f69b023e35805fd11d088380aefb5284ed2d1c33c096f982810a1f98cfbba`，root6/987684B，包22.48262600000453秒。v2的已接受inspect/unit保留，超时PRE_SEAL不充当已接受审查。

v3只重放已保存证据，inspect因保存工具3处`pin(Path)`类型错误拒绝；CP13411B / `1caf2d4b323b61babe55f41c0b75819f1a678ee4e15350aba13f4ca747016eea`，root4/885446B，包3.6547531000032905秒。两次收尾拒绝与费用均完整继承。v4区分会计前驱v3与已接受源码/测试证据v2，修为read_bytes并显式复核所有schema、contract门限和零执行数；没有重跑99方法。

验收范围只为 `endpoint_core_ownership_synthetic_and_transport_only`。v4独立PRE_SEAL must_fix_open为空，saved及checkpoint全部接受；不是official verdict/receipt/seal或run authority。

## 当前唯一账源与完整继承

[v4 checkpoint](../../results/tables/staged_rts24_saved_fresh_endpoint_preparation_v4_non_authoritative/checkpoint.json)：15343B / `9fe585ce487cb577813eeda45b79bad17c70b795c48711be315c3cedc0e1dbac`，accepted/accounting_complete/diagnostic_accepted=true；root6/901535B。

| 阶段 | charge秒 | bytes | SHA256 |
|---|---:|---:|---|
| registration | 1.2025035000042408 | 849417 | `5445b573b5bba88abc92e83ec6fdb365edbf397171594d24ab9176ffde709efa` |
| inspect | 2.4686201000004075 | 2548 | `c06baf919438f191874791ab9816281f3323021442e333bcb1e36a43cbf3a07f` |
| PRE_SEAL | 2.091394399998535 | 7962 | `6500d640d757b2c6ff148980e8533b5fac37d7c80eefc1f03e3af3e4e2e1c27c` |
| saved | 2.4572790000020177 | 3286 | `1c047b074f3f9f5b3afc366c13f4fa8124ef29bd27661e4ff69592cd26b27e0d` |
| checkpoint | 1.4096369999970193 | 15343 | `9fe585ce487cb577813eeda45b79bad17c70b795c48711be315c3cedc0e1dbac` |

v4静态9.62943400000222/34秒，阶段帽5/6/10/8/5保持；新unit方法0，复用v2已接受99方法。累计static **735.4391894000321**、pytest **366.48897970000326**、unittest **434.5809687999863**，总 **1536.5091379000216秒**，**61条不接受记录**。这是已登记阶段费用，不是协作总墙钟或完整F耗时。root10files/4MiB、record1MiB、checkpoint预留1MiB/1slot保持。

当前input **1566/89448878B**、own **21/628145B**、archive **335/42600328B**。独立fresh核1901次pin比较、1654个规范化唯一路径、247重复、0缺失/0bytes或SHA mismatch。原42项并行snapshot全部相同；NFC12原16文件全部匹配，原CP仍21591B / `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`。

下一包从当前input1566 + root6 − driver overlap1取得 **1571/90327434B**；archive335 + root6取得 **341/43501863B**，再exact union新own。本文不在当前input map，若后继使用应显式纳入。Source49 epoch仍为 `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`。

只发布本轮新源码、测试、scope/design、v1–v4全部root和本文，保留原42项无关工作树状态。本轮开始HEAD为`0bdf2d8cd4480d4b6f7fccffab8acb3b99349922`；发布时核Git blob原字节、remote hash、空index及42项原始状态。实际发布commit可查`git log -1 --format=%H -- docs/plan/continuation_handoff_20261030_saved_fresh_endpoint_preparation_v4.md`。

## 下一步的完整入口工作

1. 将完整request/offer/context/ACK与create-only manifest/header builder连到host broker和suspended child；child需核实际PID/creation后再读取manifest。Core51目前是endpoint组件，host侧完整路由尚未接通。
2. 为完整角色定义新的closed manifest/case、helper refs与startup/import profiles。Core51仍保留旧producer/import-profile分支；它不能作为新完整角色profile等价证据。薄suffix目前只做owner寿命诊断，需要独立full-role coordinator successor。
3. 接入Namespace完整parent/fresh生命周期、外部root/Guard2、ADOPTED逻辑DENY→IMPORTING首个动作安装hook→audit handoff、LIVE单次role claim，以及source-specific launcher和inner/outer quiet。旧consume_once不能代替完整生命周期。
4. 保留ctypes返回到live_box publication前的异步窗口和execution anchor根协调破坏为OPEN；再准备具体Native失败/停止矩阵、次数、全DAG读取量、时间/RSS/存储与quiet证据包，依agent.md第9节取得专项运行授权。不得由本包合成测试推出真实Native无泄漏或F准入。

原F仍为双侧独立B/C/E21点（h−2..2）、五accepted小时、130CAS、19metrics、17targets、180s绝对时钟、P1读12500/source-runtime6500与四份terminal预留。完整继承WIP、B1–B3、P2七输入、Source49 epoch、NFC12原16文件、全部失败及原42项并行改动；原科学阈值和运行权限保持。

阶段帽仍为10 prepare/45 parent/40 fresh/5 inner quiet/5 inner terminal/15 parent compare/5 outer quiet/10 outer terminal/15 final check/15 final publish/15 failure秒；成功路径165秒，failure只用原剩余额度，不重开时钟。四份terminal记录共512KiB/4slots，包含在8MiB/64files总帽内。12159=`2*5055+3*683`、12053=`2*5002+3*683`只是conditional P1 reads，不是source读取量或完整资源准入。
