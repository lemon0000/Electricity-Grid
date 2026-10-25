# C：successor 冷入口观察与父端独立比较合同

2026-10-25，DRAFT_NONAUTHORITATIVE，接续[self锚交接](continuation_handoff_20261025_saved_fresh_successor_self_anchor.md)，起始HEAD/origin `ea2cd5e1629486158be6cfa6b8372bd43641a44a`。root唯一writer、独立只读PRE_SEAL。本轮实现真正direct-file子进程中的入口事实观察，并由启动前持有独立expected的普通父端比较，推进真实bootstrap所需的cold-entry mechanics。actual F、角色专属上游能力、Job/OwnedChild、full input/runtime、permit及科学/资源/正式门禁保持关闭。

## 两侧结构和角色边界

child只采集真实main/spec/alias、argv/orig_argv/raw OS command line、初始与安装后sys.path、flags/cwd、Python可见环境映射、SF49和EXE的实际bytes/identity read bookend、self-anchor；不接expected packet，不由incoming argv重建expected并自证上游。parent在Popen之前冻结canonical expected raw、完整argv、environment、cwd、独立source49/EXE pins与identity，启动后强持Popen的真实process HANDLE，核PID/creation，再于exit后比较child实际记录与held expected。stdout只是有界诊断数据，不能成为进程间capability。

新增ordinary exact grammar：`EXE -B -s ENTRY --ordinary-successor-entry-observe [--fault CASE]`，CASE仅允许本合同列出的RAM故障。普通探针类永久为`ordinary_probe=true`、role_binding/external_Job_owner/full_runtime/full_P1/run/F及五gates=false；现有store/issuer/owner和saved/ordinary角色域拒绝它。原`--ordinary-entry`行为保持，其他saved入口继续关闭。不得通过修改旧schema/mode或接受`role: str`加任意字典混入角色能力。

角色上游仍按前序五角色合同：controller须独立request/context/ACK/mailbox与broker→controller permit；parent须controller permit/G0链摘要及原reservation；fresh须parent permit/parent hold链摘要、原reservation且无issuer。三子角色分别使用原+155/165、+110/125、+80/90 deadline。host/broker早于context发布，独立START/ACK能力。未来任何packet需exact closed canonical域、nonce/direction/producer身份/一次消费及原deadline，不能把ACK/permit/G0/full/run布尔值写入create-only context。独立expected比较本身不认证这些上游。

## 实现与失败清理

在ENTRY追加stdlib观察组件及单独ordinary CLI。真实direct main必须为执行中的`__main__`、spec=None、固定ENTRY/cwd/EXE、受控flags；安装canonical alias和ROOT-first paths前核无项目/science preimport。通过当前main module frame code与实际ENTRY bytes编译结果比较，只证明该module code一致，不扩大为完整global/runtime闭包。

SF49按原闭集读取，合计raw逻辑帽2MiB；EXE≤8MiB，kernel image path须指向固定EXE。使用原read的lstat/open/fstat/read/fstat/lstat与父目录检查，保存metadata和pin并在final重新读取/比较；文件HANDLE即时关闭，准确称read/identity bookend，不称retained source HANDLE。真正保留的HANDLE仅为self-anchor的process/thread两个query handles；parent另持Popen自带process HANDLE至exit和比较后，再关闭并独立核无效。

环境声明只覆盖Python可见os.environ的完整映射和固定六值、白名单/注入键拒绝，不宣称任意隐藏OS环境block已认证。child不读取P1或actual OUTPUT，不创建目录、共享映射或Job，不导入science/执行模型/native owner。child audit观察窗从ordinary dispatch至退出，早于任何探针Source读取；Python启动/site阶段不在其审计窗，任意native副作用未证明不存在。

观察对象强持self-anchor、main、原路径/alias、不可变raw与dependency绑定；每次entry核实际状态、source/EXE read bookend和self。close先确认自身所有权，再独立执行可安全的final bookends、恢复自己安装且仍属自己的alias/path、关闭自己持有的self-anchor。foreign alias/path漂移不得覆盖；所有primary、bookend、restore、close secondary保留，未决对象不可序列化，不返回部分成功。CLI仅在完全close后发布有界成功stdout，否则输出有界失败并exit1；无目录或结果树写入。

## 普通验证与预算

本轮总320s：pytest全部attempt≤240s；baseline/collection/准入/真实direct探针/静态保存合计≤80s；单次≤40s。重跑前序218节点和新增针对性节点，开测前固定exact collection、互斥组、帽及失败余量≥20s。静态baseline≤12s、prepare≤8s、collection≤8s、admission≤3s、全部8个parent-child probes合计≤24s（normal≤8s，其余单次≤6s）、finalizer≤3s、两次保存各≤12s；各动作按实际累计余量准入，不延长总帽。

parent普通探针每个case仅启动一个EXE进程：normal、argv drift、alias drift、path drift、environment drift、query-helper replay、commit drift、oversize，共至多8次；此增补发生在首次child启动前。每child loop≤2s，超限kill/wait≤1s、reader join各≤1s，父端单次≤8s，不自动重启。两并发reader使用固定stdout131073B/stderr4096B缓冲和4096B读块；超stdout帽或发现任意stderr即kill，不用无界communicate。超长反例由固定child输出147456B后等待，必须触发执行期stdout帽、kill、终态wait、pipes及process HANDLE关闭；不作host RSS准入声明。reader仍live时不通过跨线程强关pipe伪造完成，保留未决。

parent在Popen前安装精确argv/次数的Python audit process guard，child dispatch拒绝Python process launch/P1/actual写事件；不将这些API计数推作Job/tree quiet或任意native无副作用证明。父端另由retained HANDLE核kernel image并与固定EXE和child self报告相连。独立parent reader在读取前核普通file/目录、reparse/single-link、单文件8MiB和Source合计2MiB，并做lstat/open/fstat/bounded read/fstat/lstat/parents书挡，不import当前ENTRY/helpers。parent在drain前保存PID/creation/image的started记录；started不是terminal或成功。

所有故障记录与normal同样要求canonical/duplicate/closed域和完整false门禁；失败image限深度、总节点/条数和类型/message长度，保留primary/final_bookend/alias_restore/path_restore/restore_witness/self_anchor_close等层次。观察对象另持只含原资源/creator/安装路径的ownership tuple和一次cleanup state，完整commit漂移作为primary但最低ownership可信时仍安全cleanup；最低ownership也损坏则强持未决，不声称已关闭。

每个RAM case固定自己的primary type/message和精确layer顺序：argv/control；alias/control+alias_restore+restore_witness；path/control+path_restore+restore_witness；environment/Python-visible环境；helper/dependency；commit/immutable。统一的无关final-bookend失败不得替代六项具体拒绝。Source接受前另核49个最终pin.bytes合计≤2MiB，前置metadata合计只作快速拒绝。timeout分支本轮由固定FakeProcess逻辑测试覆盖，真实OS过程覆盖normal/六RAM故障/oversize；不声称真实child timeout窗口已验证，该窗口保留OPEN。

pytest以继承whole-window lscpu精确阻断/Native owner guard的harness运行；真实direct probes在单独stdlib父脚本进行，不放宽pytest的Popen拒绝域。新增测试覆盖imported-main拒绝、观察对象/旧角色域拒绝、parent comparator对argv/OS line/env/source/EXE/identity/path/code/flags/authority字段篡改拒绝。实际cold child覆盖normal及五RAM失败、关闭见证和独立parent expected比较；不能把logical fixture作为真实角色。

证据路径`results/tables/staged_rts24_saved_fresh_successor_direct_entry_v1_non_authoritative/checks_01`，≤16MiB/224files（普通开发证据，原F8MiB/64files/17targets不变）。保留所有失败、旧epoch及原stdout/stderr/exit，保存实际source/helper执行字节和首尾pin；前序全路径/P1全683、scientific src、其他47 source、原函数/类AST和旧导航正文保持。保存oracle纯stdlib，只核固定字节和隔离前序oracle，不import可变ENTRY/helpers；CLI严格当前source/nav匹配，未来archive漂移不能继承当前节点。完成检查点按已有授权Git同步并读回远端/空porcelain，目标继续保持active。

终态记录：当前epoch `00ef897eb83d55f79491804cc49ee5302d766dd533ee3d8615ffff84b6a1e83a`，64新+218回归=282唯一节点全过；前一epoch59过只保留历史。新组帽212+此前7.344=219.344，仍在原240s账中预留20.656s；所有pytest target wall实花156.314s。8 cold probes各case严格验收，合计target wall4.267/24s；没有将六个预期child exit1或oversize kill改称普通成功退出。

执行目录终态为220files/4,847,222B，保留原224/16MiB帽并冻结不再写。后续依[机械包装合同](staged_deliverability_c_saved_fresh_successor_direct_entry_package_contract_v1.md)使用独立final_package_01，时间账仍共享；组合上限明确为256/18MiB而非原224。旧wrapper wall仅计target subprocess，未计自身前后hash，故这些账不证明完整工作流墙钟或资源准入；机械包装已扩大计时口径，完整workflow wall gate仍false。
