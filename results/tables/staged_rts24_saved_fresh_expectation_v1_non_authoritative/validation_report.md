# C：caller expectation 数据投影开发验证

2026-10-25，`DRAFT_NONAUTHORITATIVE`。起始HEAD `41ed32c08519ccacbb932bddc2b16babb3132cb3`；接续[supervisor事前账本](../staged_rts24_saved_fresh_supervisor_budget_v1_non_authoritative/validation_report.md)，执行范围见[开发合同](../../../docs/plan/staged_deliverability_c_saved_fresh_expectation_reuse_contract_v1.md)。本包是普通开发检查与单次数据准备观察，实际saved F调用为零；fresh/parent局部verified、科学采用、资源准入、正式结果及F启动门禁均为false。

## 结果与实现边界

原ENTRY新增独立`SavedCallerExpectation`和完整successor context schema。从外部锚读取683份expected pins，前后扫描全部P1 metadata，只读取固定53份JSON：5份根记录、6份prefix、21份request、21份result。原load_fixture、outer和metrics检查保留。投影的canonical caller image与原full capture相同；`full_P1_content_verified=false`始终保留。未读CAS内容仍须由后续原full hold/replay/bookend核验。

新context使用`caller_expectation_core/sha`，没有旧`caller_core`别名；原validator、RoleStore、argv及CLI拒绝它。新增私有本地G0/H3 probe均为`real_verified=false`。G0 prototype在G2/G3保持同一个HeldInput，H3重新hold全683；对象entry仅返回自身，HeldInput保持私有。阶段claim先于委派、失败后不可重试；hold及bookend发生primary错误时仍独立核最终context/identity并保留同进程双错。它们不是生产G0/H3发行端。

十个直接callable检查code、defaults及globals字典身份；传递global binding内容闭包尚未建立。生产trusted role/ACK、parent issuer强持真实G0能力、actual supervisor/driver、saved public入口均未接通。普通prototype测试不关闭这些阻断。

## 当前源码终态证据

当前三源epoch为`6d0e1f9937a93ce6c1ea661382aab6ad9701333ca587b126657924a1b20f155e`：ENTRY SHA `0eb32bc64b10a68e1cd3fa7f426601e5bf10d979956e525b15321daff7603244`；tests SHA `3c5fdf8035f2d92a269fa984856f96225ad50d507b6fa966246e8fc4cc70e25b`；scientific adapter SHA `26b919e385f9d7042587db490dab694fc5bf1643665ab4bf94a1c9bac8087396`。各组的完整SF49、三源snapshot、原stdout/stderr及exit均保存在`checks_01`。

| 当前组 | 节点 | 外部帽s | 实测wall s | 终态 |
| --- | ---: | ---: | ---: | --- |
| expectation_smoke_09 | 2 | 25 | 13.796 | exit 0 |
| expectation_rest_05 | 17 | 35 | 26.875 | exit 0 |
| expectation_rest_06 | 16 | 35 | 21.110 | exit 0 |
| binding_regression_07 | 18 | 40 | 32.047 | exit 0 |

精确并集53节点，无重复，35个新增节点及18个相关绑定回归；当前epoch累计93.828s。旧epoch的smoke04另耗13.047s，保留但不计入当前53节点；全部pytest attempt累计106.875/160s。历史161节点仍绑定其原源码snapshot，不能自动计为当前源码通过。

覆盖投影等价及53/683实际读取差异、完整metadata、successor schema拒绝旧消费者、selected内容/metadata/source/anchor/creator/raw漂移、直接callable替换、同元数据未读内容须由full hold拒绝、本地阶段/同对象/不可重试及primary+final双错。对同inode/size/mtime未读内容的故障使用只读文件代理；P1磁盘字节未修改。scientific compile/import_snapshot、B/C/E replay、solver和journal写入在新fixture中被拒绝。

原ENTRY的168个、tests的172个及scientific adapter的16个顶层函数/类AST均保持；原SF49中其余47个路径逐字不变，集合未扩大。前序3176个保存路径逐字保留，实际F结果树及其父目录仍不存在。保存核验会重新读取P1全部683文件并调用前序检查，不重跑科学replay。

## 单次费用观察

`profile_10`外部3.828s/8s，固定先full capture再projection；操作计时排除import/setup，外部帽包含它们。见[原始观察](checks_01/projection_profile.json)。

| 一次数据准备 | full capture | expectation projection |
| --- | ---: | ---: |
| P1内容读取次数 | 683 | 53 |
| P1读取字节 | 2,950,863 | 94,323 |
| selected-source读取次数 | 174 | 233 |
| selected-source读取字节 | 3,546,750 | 4,910,128 |
| source catalog读取次数 | 0 | 1 |
| wall s | 1.117072 | 0.801252 |
| CPU s | 1.093750 | 0.812500 |
| lstat / fstat | 19836 / 1710 | 5744 / 570 |
| scandir / stat | 98 / 50 | 196 / 50 |

两次caller image均437717B，SHA `aaffd03d7a9fd4f03afa18d34ab119b10408b82d5e4ab3f8fc83d9a950600031`，被禁科学effect调用为零。两次各读外锚2次/255914B；其他读取原样保存在JSON。selected-source增加59次，不能由P1节省推断source6500已满足。

这是一次固定顺序观察：projection可能受full capture预热的文件系统缓存影响，计数探针开销也不同。该wall差异不构成稳定加速比、whole-F节省、OS物理I/O或RSS证据。execution record保存了canonical三源epoch及SF49前后相等，但没有执行瞬间的profile/helper脚本pin；本包support pins只建立保存raw与当前helper字节的机械关联，不倒推严格execution-time helper binding。

## 预算、采用边界与下一步

普通开发预算200s，pytest≤160s、collection/静态/保存核验≤40s。profile结束时静态已用20.047s；最后包装和保存核验另由终态`*.exit.json`累计，最终汇总以saved_checks输出为准。无自动retry，无新的模拟小时、native owner、solver或实际saved actor。

若未来两个独立H0/B0 expectation均按此接通，成功条件账本可由13419减去两次683并加两次53，得到含host末次full的12159；不含host末次为11476。原12500帽未放宽；这是条件算术，不是actual F整链计数。source6500、完整失败读数、180s逐边deadline/episode handoff、合法最大wire record、external arming/quiet和host I/O硬停止仍OPEN。

下一轮先登记操作内source原字节复用合同：在同一次验证内保留已绑定49源字节供code比较，减少重复读取，并证明失效窗；随后补全生产传递依赖认证与trusted-role/G0结构性门禁。不可跨进程缓存P1或减少G0–G3、parent/fresh hold及replay末次库存。完成完整调用和费用证明后，才可制定具体driver及实际F申请；本轮不授予该权限。

保存核验：`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_expectation_v1_non_authoritative/checks_01/saved_checks.py`。本文件及[交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_expectation.md)只保存draft开发事实，不生成official verdict、receipt、seal或run authority。
