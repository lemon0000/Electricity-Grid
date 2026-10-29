# F：完整角色入口路线与压缩容量准备交接

2026-10-30，DRAFT_NONAUTHORITATIVE。持续推进goal保持active。用户原八组full-context role修补已在[role v2](continuation_handoff_20261029_saved_fresh_full_context_role_v2.md)完成26方法验证，后续[cleanup binding v4](continuation_handoff_20261030_saved_fresh_cleanup_binding_v4.md)保留69方法/48故障场景的开发证据。本轮完成真实入口接口、压缩容量及失败/停止条件的静态准备，尚未实现FullRolePreEntryBinding。新增模拟跨度0h；NFC12未重跑。

## 当前结论与实际证据

1. 旧broker实际交付8s role probe；旧SavedFileBootstrap是direct-file入口；Core等待stdin frame，现有Job owner使用不继承stdio的suspended process。它们不能直接拼接为完整角色入口。
2. 选定独立suspended-channel后继：host full-context ACK → create-only manifest/transport/descriptor及pin关联 → channel → suspended child → 绑定实际PID/creation → publish binding → ResumeThread。child必须先取得Open-only物理endpoint并核自身PID/creation，再读manifest、创建Core self resource、读Source49。
3. **Core50+旧probe42已有压缩阻塞**：payload125987B低于131072B，但XZ26312B超过原26214B帽98B。真实builder在原`encode14`第28行抛空message AssertionError；未生成transport，也没有命令行大小结果。新薄入口是实际实施前置条件，压缩帽没有放宽。
4. Core44+probe42可生成容量基线：payload97429B、XZ21136B、transport42333B。旧形状与新增字段预留形状分别18533/18995个UTF-16 units，均包含终止NUL；项目帽30000。两者argv含占位值，不能运行；Parent40真实SOURCE_REFS仍只绑定Core44。这些余量不能给未来Core/entry授权。

实现文件：[静态审计器v2](../../experiments/staged_rts24_saved_fresh_preentry_route_audit_v2.py)、[设计v2](staged_deliverability_c_saved_fresh_full_role_preentry_design_v2.md)、[scope v2](staged_deliverability_c_saved_fresh_preentry_route_scope_v2.md)。原source14份、主节点23、三条完整source-span顺序及watch→release链已核。16行Native failure/stop矩阵含59个列举variant，**全部OPEN、执行0**；10个source接口尚待实现。

Core44实际transport SHA `01980354f1c5f43f2e6036f8a37a6f5b9d962a03356ca6f76d5d68130126545a`，独立bit-string解码核原payload、zero padding、CRC64及生成loader的内嵌pin、解压帽、memlimit、拒绝guard AST。Core50实际失败参数从原encode14 traceback frame取得，XZ SHA `b5a8ff4161f8080dd101ce9a83ecc2d3934e3b08878f1874e2d9543fd9f8a115`，保存原XZ字节并独立重放。

## 冻结失败、验证与账源

[v1失败root](../../results/tables/staged_rts24_saved_fresh_preentry_route_v1_non_authoritative/checkpoint.json)完整保留4files/852895B。register1.2257124000025215s接受；inspect3.640360299999884s拒绝；checkpoint0.6481291000018246s，会计完整、diagnostic不接受；总5.51420180000423s。原失败记录只有空message AssertionError，v2增加实际来源绑定与后续意外异常最多20帧trace，未回写v1。

v1 CP：13243B / `685569ed7930824f66736e48edda277c2a8f73b17a05d4427d63a6a1a10ab232`。

v2唯一顺序register→inspect→独立PRE_SEAL→saved→checkpoint全部接受：

| 阶段 | charge秒 | bytes | SHA256 |
|---|---:|---:|---|
| registration | 1.6541291999965324 | 821107 | `6228c2762ff9e798c141d69e78389f4f0a8868bf035a72df312c5237ab139bc7` |
| inspect | 4.757320400000026 | 119838 | `214b6306d3de26dbcab21d81b8e0cc33e6a0d0f1b2e794457c928c6b19b03e97` |
| PRE_SEAL | 2.0804910000006203 | 7567 | `734dde049df75af8ee92421b4135d8fec9d82573b3c3a6936d799ba98849f48a` |
| saved | 3.627174199995352 | 2551 | `4feb729afd88a2069d5a1009ed868b534243986cf0e056f2fcc6f1cc3d1ebb89` |
| checkpoint | 2.619320899997547 | 15134 | `037ec427e1f7d42592d1a0704194df21c7511676aecb3a6d0735e77e8efc6008` |

当前唯一账源：[v2 checkpoint](../../results/tables/staged_rts24_saved_fresh_preentry_route_v2_non_authoritative/checkpoint.json)。accepted/accounting_complete/diagnostic_accepted=true，acceptance_scope=`source_route_and_transport_preparation_only`。root6files/985003B。static **14.738435699990077/36s**，阶段帽6/12/6/6/6s；root10/4MiB、record1MiB、checkpoint预留1MiB/1slot保持。首次登记后所有own冻结；首拒绝后仅checkpoint，没有重跑或退款。

独立sol_reviewer的PRE_SEAL `must_fix_open=[]`，不是official verdict/receipt/seal。saved再次核PRE_SEAL绑定的registration/inspect/own pins，重放两种容量结果。实际执行driver、route audit、contract snapshot控制模块、只依赖stdlib的仓库transport compiler及抽出的Parent40 minifier；Core/probe/完整Parent/Source49/native owner目标模块只读/compile。阶段内child0、项目target child0、普通测试方法0、项目Native/P1/solver/full F均0，未调用Capture1/DRAIN1或Native sampler。

累计static **705.1804242000246**、pytest **366.48897970000326**、unittest **414.9035574999798**，总 **1486.5729614000077s**；**58条不接受记录**保持。这是已登记阶段费用，不是协作总墙钟、完整F耗时或资源实测。

## 完整继承与现场

v2 input **1526/85221717B**、own **21/1069378B**、archive **314/38753410B**。独立fresh审计1840次pin比较、1614个规范化唯一路径、226重复、0缺失/0bytes或SHA mismatch。NFC12原16文件全部匹配；其CP仍21591B / `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`。

下一包从v2 input1526 + root6 − driver overlap1精确得到 **1531/86187914B**；archive314 + root6得到 **320/39738413B**，再union实际新own。本文不在当前input map，后继使用时显式纳入。Source49 epoch仍为 `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`。原WIP before_repair、B1–B3、P2七输入和所有失败/已发布绑定字节完整保留。

原[42项并行snapshot](continuation_handoff_20261029_saved_fresh_source_cleanup_state_v1.json)的exists/bytes/SHA fresh核对全部相同，包括原project_abstracts.md的exists=false。当前仅见VSCode Jedi，没有项目/solver运行。本轮开始HEAD `6a07a8bf8ef550ad42fdd88e76b2c91c79c1e2be`。只发布本轮v1/v2独立源码、设计/scope、两root和本文；remote hash和空index在发布时核对，保留原42项工作树状态。实际发布commit可用`git log -1 --format=%H -- docs/plan/continuation_handoff_20261030_saved_fresh_preentry_route_v2.md`查询。

## 接下来实际实现

先按设计实现薄入口、pre-manifest endpoint kernel和Core ownership API的独立successor。endpoint必须进入lease/input transfer record与runtime PREPARING cleanup anchor，早于实际resource.owner commitment；manifest或_Core Resource构造前失败也要独立关闭endpoint。根据实际resource.owner区分pre/postcommit，不能用journal末项推断。Native finally不能被endpoint/Guard/child/channel失败压住。

同一完整source包还要补full request/offer/ACK、broker create-only manifest/descriptor与suspended constructor、Namespace完整角色生命期、外部root/Guard2、LIVE单次role claim及source-specific launcher/inner/outer quiet。Guard2时序是ADOPTED逻辑DENY、IMPORTING首个受控动作安装hook，再audit handoff。旧consume_once在单次expectation后关闭owner，不能用它代表完整parent/fresh生命期。

新pre-source endpoint改变启动模块和Native图，旧startup/import profiles不能直接充当等价证明。未来薄入口的真实payload/XZ/UTF16大小、完整读取DAG、失败/清理/quiet、独立语义与资源账均须重新验证。原F保持双侧独立21点、五accepted小时、130CAS、19metrics、17targets、180s绝对时钟、P1 12500/source-runtime 6500读帽和四份terminal记录预留。任何项目Native/P1/Source49诊断先准备具体次数、预算、停止条件和包，再依agent.md第9节取得专项授权；本检查点没有增加运行权限。
