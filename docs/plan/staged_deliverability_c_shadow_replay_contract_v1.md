# C：原P1完整只读重放的逐调用摘要比较

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT。接续[严格域原型](continuation_handoff_20261023_plain.md)。问题是原P1完整reopen的实际digest输入是否逐次满足严格候选bytes/SHA等价；本包不采用候选驱动验收，不接writer/native，不产生提速或资源准入结论。旧c/plain/digest及其他科研模块不替换、不克隆、不改源码。

## 固定执行路径和调用量

controller核原postcheck SHA、P1完整683文件/2950863B、compute解释器及受控环境、新源/合同/测试及旧源pin；exclusive创建独立shadow_01。原Job guard只启动一个fresh worker，父端准备与quiet后核验另计。worker载入原fixture、trusted binding和旧runtime pins，预加载已声明依赖，核新闭包；只对一次原journal_v2.reopen开启监控。结果必须与原fresh.metrics完全相同，原P1及输入源码首尾核对；monitor完整清理、Job全部成员HANDLE退出和父端postquiet核验后才采用。

CPython3.12.12专用的sys.monitoring按原代码对象启用局部PY_START/PY_RETURN：原digest、json.dumps及固定stage。别名调用仍为同一code，不依赖模块属性包装；不调用旧install_observers。PY_START登记(thread,id(frame))；原digest直接调用json.dumps的PY_RETURN提供真实旧JSON字符串，callback以同一digest frame的value运行candidate._walk严格路径，按原JSON选项生成新bytes并逐字节比较；原digest PY_RETURN再要求原返回SHA同时等于两份bytes的SHA。callback不保留frame或输入对象，只存配对计数、SHA及caller标签；同tool回调内暂停事件，避免候选自身混入旧调用计数。局部行为在固定解释器普通测试验证。

从原保存profile固定验收：digest START/parent-json-return/digest RETURN/strict-byte-compare各2547；child audit直接别名caller118，其余2429。stage START/RETURN为reopen1、replay_entry6、prepare_hour10、propose_hour10、accept_hour5、audit_execution17、audit_child_lp118、execution_summary1。原json.dumps总RETURN4861，其中非digest parent2314。pending最终0；unsupported、字节/SHA不等、observer错误、foreign thread、unwind、detach与清理错误均0。未满足即不完整，不按本次数据调准入类型、深度或这些固定计数。

普通比较失败只锁存首错并让旧逻辑继续；比较callback路径的MemoryError单独传播，SystemExit/KeyboardInterrupt/GeneratorExit不吞。生命周期清理异常锁存为不完整。全局PY_UNWIND仅筛目标代码，旧异常保持原样传播。科学构模、numeric compile、backend make_model/call_highs、CAS put/publication等旧Python入口设局部START拒绝，出现即在函数body前中止；本范围是冻结源码可达的已登记入口，typed解码只允许原registry，不执行任意输入代码。callback从不返回DISABLE。退出前核tool名称、事件mask和callback身份；finally逐一清局部事件、清global unwind、注销callback、free tool，任何不完整都不得写等价成功。

fresh scope在调用前后还要求其他monitoring tool均未占用/global events为0、sys profile/trace为None；新增foreign状态不由本tool清理。该书挡覆盖保留到退出的漂移，短暂安装并恢复的任意ABA不在此可信fresh-worker威胁模型内，不宣称任意外部协同篡改防护。

## 身份和边界

旧runtime identity按原P1核对；新shadow身份单列，不能冒充旧注册实现。新身份至少含exact executable及Python版本、受控环境hash、候选/monitor/driver/合同/支持库源码、legacy fallback的模块和代码来源、codec及20类实际加载路径/源码SHA/字段顺序、JSON选项。固定关键函数与其globals/模块对象关系，首尾保持；critical模块实际路径须在声明仓库或compute目录，拒绝module shadow。

对实际加载的标准库module集合、路径/来源及文件SHA首尾绑定，包括dataclasses/fractions/json及其实际加载依赖；builtin/frozen部分由解释器/runtime DLL身份界定，范围不扩展为完整第三方或OS闭包。旧P1所选第三方依赖仍沿原fingerprints核对。换解释器、加载集/来源变化或关键函数对象/代码/registry改变即不采用。测试中的临时monkeypatch仅用于故障反例，不是shadow运行方式。

## 预算和停止

只允许固定P1保存五小时前缀的一次无求解器诊断：Job wall60s、无进展30s、采样tree RSS512MiB、输出16MiB/64文件；原Job guard每进程1GiB/Job2GiB commit及5秒归零截止沿用。每128个digest完成更新进展，失败和超帽保留全部已有字节，不重试/覆盖shadow_01。原P1唯一native授权已使用；本诊断在agent第9节已有有界开发授权内，不启动新native/P2/D/E或长实验。

controller在Job quiet后重新计算实际runtime身份（对象、加载标准库文件、解释器与受控环境），再核原P1、新源与runtime保存绑定、固定输出集合/普通文件、完整shadow配对/计数和原科学metrics。原逻辑失败、shadow mismatch/unsupported、observer detached/failed、超时或缺失report均为unresolved/incomplete。wall受监控与旁路计算扰动，不作提速对照。即使全部通过，也只支持本固定完整重放中2547次实际编码输入的逐调用等价；candidate-only/writer接线、139/F-X时序及C/D/E资源另需证据和权限。

监控机制依据[Python3.12 sys.monitoring](https://docs.python.org/3.12/library/sys.monitoring.html)及[PEP669回调事件暂停规则](https://peps.python.org/pep-0669/#events-in-callback-functions)，并以本机CPython3.12.12的普通反例为准。
