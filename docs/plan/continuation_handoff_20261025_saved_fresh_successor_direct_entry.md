# C：successor 冷入口与父端独立比较交接

2026-10-25，DRAFT_NONAUTHORITATIVE，接续[self锚交接](continuation_handoff_20261025_saved_fresh_successor_self_anchor.md)。起始HEAD/origin `ea2cd5e1629486158be6cfa6b8372bd43641a44a`，最终提交以远端读回为准。[执行合同](staged_deliverability_c_saved_fresh_successor_direct_entry_contract_v1.md)与[机械包装合同](staged_deliverability_c_saved_fresh_successor_direct_entry_package_contract_v1.md)共同约束本轮；root唯一writer、独立只读PRE_SEAL，没有seal/official review或actual F。

真实direct-file child观察active `__main__`/alias、初始与ROOT-first路径、flags/cwd、Python可见完整受控env、argv/orig_argv/raw OS command line、SF49/EXE read/identity bookends及self HANDLE；当前module frame code与磁盘ENTRY编译结果一致。child不接expected packet。普通parent在Popen前独立冻结expected bytes/完整argv/env/source/EXE，强持真实Popen process HANDLE并独立核PID/creation/kernel image；退出后比对observations再关闭HANDLE并核ERROR_INVALID_HANDLE(6)。stdout只有序列化诊断数据，不是跨进程capability。

8个真实cold probes已终态：normal父端比较通过；argv/alias/path/env/helper/commit六RAM故障各自primary与layer顺序正确拒绝；oversize由固定stdout缓冲在执行期触发kill/wait，reader threads、pipes与parent HANDLE均关闭，cleanup为空。probe target wall合计4.267/24s。真实timeout窗口仍OPEN，只有FakeProcess deadline逻辑与真实oversize清理链；未证明Job quiet或任意native无副作用。普通对象、输出和比较结果永久ordinary，role/bootstrap/upstream/full input/runtime/permit/F/science/resource/formal保持false。

当前epoch `00ef897eb83d55f79491804cc49ee5302d766dd533ee3d8615ffff84b6a1e83a`，64新+218相关回归=282唯一节点全终态通过；早期59普通节点属于另一epoch，不计当前。所有pytest target wall156.314/240s；执行目录static/probe target wall20.003s，其中probe4.267s。旧wrapper没有计其自身source/helper前后hash，不能把这些slice称完整workflow墙钟≤320；该workflow wall gate明确false，资源门禁未关闭。机械wrapper计入pre/post哈希，measured与0.5s尾部reserve分别报告，仍共享原80/240/320账；完整终态账按两个目录的exit累加。

`checks_01`固定220files/4,847,222B后只读，仍≤224/16MiB。`final_package_01`仅机械脚本/helper快照、inventory/indices和三次机械记录，≤32/2MiB；组合≤256/18MiB，不移动或裁剪执行历史。恢复先核Git/相关进程，再运行`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_successor_direct_entry_v1_non_authoritative/final_package_01/saved_checks.py`。oracle先核execution exact inventory/root，再核282/8probes/3815前序路径/P1全683；不import当前ENTRY或current helpers，仅调用已hash固定且独立的旧stdlib oracle。CLI严格current source/nav，未来archive漂移只保留冻结282、current=0。support清单和三次机械原记录由后继pin链及最终Git逐blob承接。

ENTRY追加273行/tests174行，原200/229顶层函数/类及scientific src16定义AST不变；SF49闭集、其他47及原F8MiB/64files/17targets/guard/outer保持。P1仍21点/5模拟小时，无新增模拟小时。详见[报告](../../results/tables/staged_rts24_saved_fresh_successor_direct_entry_v1_non_authoritative/validation_report.md)。

下一步把已验证的cold-entry mechanics接到角色专属上游：controller=request/context/ACK/mailbox及broker→controller permit；parent=controller permit/G0链摘要/原reservation；fresh=parent permit/parent hold摘要/原reservation且无issuer。host/broker先于context另走START/ACK。真正bootstrap还需context文件书挡、外部retained OwnedChild/Job及原绝对deadline；之后才到full input/runtime/store/issuer/owner。生产NumPy probe政策、33根传递绑定、source6500/180s、全workflow wall/RSS/失败/wire/host硬停止和真实timeout仍OPEN。实际fresh、最终父端采用、整包科学采用、资源和正式门禁均未开放。
