# C：上游数据合同 archive successor 范围与预算

2026-10-25，DRAFT_NONAUTHORITATIVE，起始HEAD/origin `d458c35cfe6b537853d3ff7aee3314f4fd5d5147`。接续[失败检查点交接](continuation_handoff_20261025_saved_fresh_upstream_contract.md)。前轮是有证据的进展：10域/59节点/21项设计结构结果与两个保存失败已发布；本轮完成其独立机械保存复核。root唯一writer，既有reviewer独立只读PRE_SEAL；无seal/official receipt/run authority。采用已读karpathy-guidelines，修复与实测针对具体失败。

## 固定范围

独立新根 `results/tables/staged_rts24_saved_fresh_upstream_archive_v1_non_authoritative/checks_01`。旧upstream root的47个文件、31-file execution freeze、14-file failed package、root checkpoint、两次失败、4058前序路径、Source49、科学adapter与原F参数保留原字节。不改旧handoff/report或旧checker。新checker为旧terminal checker的独立successor，保留其审计范围，闭集识别saved_05/terminal_06两个exit1/accepted=false及固定stderr/空stdout；其他四条须仍exit0。逐record核epoch、helper snapshot、source/history digest、design outputs、原时间账、支持清单与prior pins，不吞旧verify异常，不重标历史失败。

四导航修正为 `原header + b'\n\n' + 新prefix + 已发布single-LF header后的完整body`。新manifest保存原header、before full/body pins、prefix与after full/body pins，可逆重构已发布字节。CLI核当前完整导航pin；archive要求双LF header固定且完整body suffix保持，只允许header后的前置段落。旧migration中的single-LF body suffix继续保持。旧handoff/report已在两次失败后添加状态说明；它们以旧checkpoint的post-terminal pins核当前字节，并从完整冻结正文suffix加旧prefix重构旧migration pin，不能追认为当时执行通过。

新checker不调用原失败terminal checker的verify；它独立重做该审计，只动态装载exact SHA已核的旧design oracle和原direct-entry archive oracle，并让原oracle在真实当前导航上执行到返回。目标包括冻结282 pytest节点/8普通cold probes、P1全683、current Source49匹配、10域/59节点/21设计负例及两类旧失败原bytes；本轮新pytest/probe/模拟小时均0。完整传递核验通过只建立mechanical successor保存证据，不赋予真实bootstrap、G0/hold、issuer/owner/Job、科学采用、资源或正式权限。

## 命令与资源预算

新预算独立于已耗尽的前轮6次/90s，不改其27.9873943s或terminal状态。最多4个ordinary stdlib static captures：计划check_01、saved_02、terminal_03，另reserve_04仅为前三次同字节成功后的可选重复核验，不是helper修改后的失败补跑。每次target timeout≤25s，capture charge≤30s，总charge≤120s，所有失败照计且保留，不覆盖记录。固定顺序逐record核完整exact前序集合、累计账和独立重算的fixed digest；不自动增加第五次。超时或Source/历史pin漂移停止dependent动作，保留原输出与终态。

capture以最初monotonic计入helper读取/snapshot、pre/post全部pins、target启动/退出和写raw logs；0.5s未实测尾部reserve分列。最初wrapper Python启动、编辑/审查/Git不在窗口；不将这个账称完整F工作流或OS硬墙钟证明。单次25s相对前轮7–10s保存检查留有余量，未开展研究实验、native校准、外部数据或付费查询。

新checks≤24files/4MiB：capture/checker两个helper、两个helper snapshot、一个baseline（Source49、4058前序+旧root47闭集、helper pins）、导航manifest、support pins、最多4次各3个stdout/stderr/exit；总≤19，余量留给必要的draft材料。新scope/handoff/report≤3files/1MiB，另一个终态checkpoint JSON≤64KiB；新增总≤28files/6MiB。逻辑帽不等于RAM/RSS或实际磁盘allocation准入。四既有导航只按规定插入前缀，header和历史body保持；archive固定本轮prefix+旧body构成的after-body suffix。执行目标审计guard禁止嵌套process与project/science imports；不import当前ENTRY或可变project helper。

## 保存、验证与下一步

first check前，合同、helper和预算固定，baseline与导航manifest留pin。first check的完整成功重放先形成证据，再冻结最终handoff/report及support；saved与terminal共用同一预算，successor oracle先核baseline/support/helper字节再调用旧stdlib oracle。内部仅报告oracle body/support验证，不因support存在宣称完整保存成功；外部terminal exit确认后才生成终态checkpoint。support自引用与本次尚未发布的exit不作自证，后继原record与最终Git逐blob承接。新record明确区分old两失败和new成功/失败，逐次charged含尾部reserve，任何机械通过都不改变旧失败记录。

执行前完成独立只读审查，完成后做diff/link/process/hash核验；按既有授权精确commit/push，核remote hash及空porcelain。宽目标持续active。后续继续三种exact data-only validator与角色上游/真正bootstrap，actual fresh/最终父端采用、整包科学采用、资源与正式门禁继续false。
