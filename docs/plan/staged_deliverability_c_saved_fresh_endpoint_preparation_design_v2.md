# F：pre-manifest endpoint 与 Core ownership 接线

2026-10-30，DRAFT_NONAUTHORITATIVE。承接 [route v2](continuation_handoff_20261030_saved_fresh_preentry_route_v2.md)及endpoint preparation v1失败checkpoint，root 为唯一 writer；本包只提供源码接线、真实编译容量和普通合成控制流证据。

v1真实builder已生成payload121138B、XZ24816B、transport48477B、UTF-16含NUL21000 units，保留原帽。99方法执行出现5个旧role Core pin错误及1个未命中故障标记的失败，原记录完整保留。v2保留已冻结Core51/薄suffix/endpoint fixture/source-cleanup v7字节，仅创建role runtime v7（固定Core51 exact pin）、其26方法后继、join测试v6与endpoint测试v2。故障定位采用源码owner赋值行的首个表达式指令（line或opcode事件），必须在实际STORE前且已追加record、实际owner仍为prior时触发，并保存实际event/offset/journal/owner witness；不预先声称某类trace事件必然出现。

Core51 的唯一创建入口为 `open_bound_local_pre_entry_lease()`。它解析实际封闭 argv、原 180s 时钟和 transport/payload pins，先分配 lease 与 endpoint anchor；Open-only mapping/mutex、非继承检查、view、有限 mutex wait、双读 header、描述符与实际 child PID/creation/OS argv 验证完成后，才令 early hook 允许读取 manifest。随后创建 self resource，再允许 Source49。manifest/profiles 与 Native 目标均未在本包真实执行。

描述符绑定 request/offer/context/ACK、角色、channel 名/nonce、manifest 路径/SHA、source epoch、transport/payload pins及原时钟。channel 名由同一 nonce 严格派生。物理 header 保存完整 descriptor；manifest 的 `pre_manifest_binding` 保存去掉 `manifest_sha` 的封闭投影，避免文件自引用 SHA 环。manifest 本体仍按 header/argv 的 SHA 读取。使用新的 startup profile 路径；新 profile、B_S import profile 与完整角色准入仍待准备和专项验证。

anchor 在第一个 Open 前建立。执行用 `live_box` 保存已发布的不可变 HANDLE tuple，`close_states` 在每个 close 调用前写入 CLOSE_ISSUED。capsule._live、opened、resources 为镜像；镜像漂移记录 secondary，清理使用原执行根。关闭顺序 view→mutex→mapping；失败或不确定状态 sticky UNRESOLVED，不重复物理 close，后续域仍尝试。timeout 不 Release，abandoned 先 Release 一次再拒绝，Release 失败保留不确定所有权。当前 creator 和真实 resource.owner 是清理权限边界。

endpoint 进入 lease→inputs→runtime 的目标与 transfer record，早于 resource.owner 提交。held transfer verifier 检查前缀、前驱身份、同一 capsule/resource/target；以实际 resource.owner 判断提交。bookend 拒绝未提交 record；清理未提交 record时关闭原资源并保留 UNRESOLVED。runtime PREPARING cleanup anchor 固定 endpoint 域，Native finally 与 endpoint、namespace、B_S、旧 hook 清理分别保存错误。构造失败包括尚无 `_ownership` 的窗口；已保存的 cleanup factory 元数据失败不能压住 endpoint/hook 收尾。

薄 probe 是 transport compiler 拼接于 Core51 后的 payload source suffix，不是单独可运行脚本。它调用集成 factory，检查同一 owner，关闭后输出诊断；有 primary 且 cleanup unresolved 时，以持有 owner 的 cleanup failure 为顶层。它没有完整 parent/fresh dispatch，也不复用旧 `consume_once` 代表完整生命周期。实际容量检查绑定 Core51+该 suffix，保留 raw131072B、XZ26214B、UTF-16含NUL30000 units帽；argv只作容量预留，含占位值而不可运行。

普通验证使用 private module copy 和显式 synthetic kernel/startup/filesystem/profile/namespace/B_S/role effects；原 Core factory、acquisition/transfer/close/cleanup orchestration 代码不改。组合源码编译 oracle、held cleanup递归 LOAD_GLOBAL、失败/重入/镜像/根漂移、实际 owner STORE前异常、两清理域隔离和旧69方法回归共同约束所述控制流。替换的效果域不构成真实 Native 或 Source49读取证据。

OPEN：ctypes返回到执行根 publication前的异步异常窗口；对 execution anchor 根本身的协调破坏；真实 Native返回值/关闭等价；新startup/import profiles；host完整ACK/descriptor/create-only broker与suspended child；外部root/Guard2、完整role coordinator和source-specific quiet；整链读取/性能/RSS准入。新薄入口不关闭这些项，不生成production manifest、lease、seal或official review receipt。

原F双侧独立21点、五accepted小时、130CAS、19metrics、17targets、180s绝对时钟、P1读12500/source-runtime6500以及terminal预留全部保持。NFC12不重跑，历史失败、42项并行dirty snapshot与全部完整继承输入保留。
