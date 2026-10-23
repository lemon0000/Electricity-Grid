# C：P2机械检查层的调用量与收尾预算

2026-10-23，DRAFT_NONAUTHORITATIVE。适用[机械检查合同](staged_deliverability_c_p2_package_check_contract_v1.md)的新模块；不修改原P2七输入、guard v2、prepared packet或P1/B1–B3。这里只补机械检查层在完整DAG中的位置，不授予native或长实验权限。

## 完整路径与读取会计

外部调用者先持有context原字节/SHA及parent直接取得的process/startup记录。检查器依次核context、预期启动参数与完整Job quiet；quiet未知立即返回，不读取worker。quiet已知后，核输入→worker metadata上限→完整有界文件读取→成功/诊断协议或失败库存→完整第二库存→输入第二书挡→返回独立机械状态。错误不补文件、不重试、不改writer终态。

每次`read_inputs`有76次`codec.read_bytes`：三packet＋一registration＋68来源（55准备＋7 kernel＋6 outer）＋三个已加载模块的额外同字节核验＋一executable；其中73个不同绝对路径。首尾共152次，三个模块额外读取仍保留。`context_bytes`是独立准备步骤，另有registration/context/六outer/executable的9次读取及一次76次核验，共85次；不能把它漏入未来launcher全路径。

设worker库存有N个文件、D个目录（含根），文件i的完整祖先目录数为a_i，worker根路径祖先链长度为A。单遍inventory含：

| 阶段 | 调用量 |
|---|---:|
| 根祖先ordinary检查 | A |
| 目录metadata及末尾identity | 2D |
| 文件metadata、读取前path、关闭后path、最终identity | 4N |
| 每文件前后全祖先directory identity | 2Σa_i |
| 内容open/read | N |
| HANDLE fstat | 2N |

两遍各项加倍，另有`inspect_package`的worker/parent目录链和物理路径互不重叠检查。该表是源码调用量，不能当实际系统调用或wall测量。每遍先以metadata界定depth≤12、entries≤16384、files≤8192、总bytes≤64MiB及单文件≤8MiB，随后才读内容；不删除任何path/fstat/目录书挡。六个根排除项仍被完整库存读取。

成功协议保留原319点/138合同行/10个actual-state引用的全部比较，包括journal累计CAS、state/prefix/head、每point raw/log/query/result/typed-wire引用、父经济点、accepted-state、prepared evidence、串行events与fresh/report metrics。每个point及fresh Job核完整成员集合、owner、HANDLE、quiet、exit/stop/error和各自帽，内部集合两两不交；outer residual如实单列。科学重审、实际argv、完整runtime闭包与进程亲缘证明仍是另外的路径。

## 两处受限实现调整

库存reader只将固定8MiB＋1请求改为已观测size＋1，并在读前绑定metadata identity；全部旧书挡保留。摘要长度预走使用单次调用局部container memo，再生成原规范JSON bytes/SHA；不跨调用缓存、不减少digest或任何科学检查。适用exact plain/string-key域，最大展开8MiB及depth512，临时str＋bytes最多约16MiB，输入、memo和两份库存另计。实际入口先受冻结packet或codec/WireView解析范围约束；该helper不是已批准的通用不受限序列化API。一般输入域硬化及整个checker内存峰值仍须在资源包中审查。

旧测试若干次触及120s wrapper上限；保存stack_03在首库存观测5837文件/41.9896802s，之后栈落在journal的逐token摘要。这是普通合成fixture定位信息。调整后的units_10以真实文件系统走两遍库存及完整协议，exit0，pytest1项/58.55s，wrapper59.5799774s。两者来源、运行条件及覆盖不相同，不构成提速比、warm/cold结论或公共P2资源测量。

独立旧iterencode对照记录P1全部403个wire根/9790308B规范字节，以及合成319完整协议7582个实际digest入口/81683242B规范字节；每次新旧bytes相等，根类型为NoneType/dict/list。后者直接使用预构造snapshot，不包含真实库存，不能与真实双库存测试混为同一条证据。7582次调用和81MB逻辑编码量没有因本层长度memo而省略。

## Job收尾记录的条件空间缺口

独立标准库[复算脚本](../../results/tables/staged_rts24_p2_package_check_v1_non_authoritative/postcheck_01/process_record_budget.py)读取原P1的33个保存process记录，单遍26301B并在末尾逐字节复读。原outer为66成员，31个point Job各2成员、fresh Job2成员，32组两两不交共64且均在outer内。余下两identity为(23748,134371984628013733)及(24064,134371984628243527)，第一项是outer owner；第二项的程序身份及父子边没有记录依据。

仅在“P2仍有两个residual、319 point＋1 fresh各有两个成员、FILETIME仍18位”的条件下，outer历史成员投影为642。单成员PID至少一位时规范记录48B，单成员数组至少31459B，已比原guard固定16384B reserve多15075B，尚未计其他字段。保留原P1外围字段、采用642个五位PID的静态示例记录为34658B，多18274B。这些是结构算术，不是实际P2记录，也不表示实际包必然超限：reserve是边界余量，不是记录长度上限。

未来需版本化地确定parent记录预算、按可证明成员上界计算reserve或独立预算收尾记录，并核实guard最终storage会计；不能原地改guard v2或把固定16KiB视为已保证足够。642也不能替代真实进程树/额外调用的核验。

## 保持开放的准入项

实际outer launcher、registration/启动事实的父端绑定、独立科学采用、父记录持久化及失败窗口尚未闭合。真正P2的昂贵失败、十小时state/CAS/摘要增长、quiet后全部读取/重审/保存、内存/存储和全wall/no-progress仍需代表性有界证据；fresh60s＋最多5s收束相对65s无进展帽没有父端余量。普通129项测试范围及原P1五小时成本不能替代这些证据。

RTS-24公共主比较及两母线机制方向保持；139/F-X时序、C整体及D/E现实输入、有限方案、选择、敏感性、冻结后留出与总预算继续OPEN。原P1一次native授权已使用，新native需具体包和专项授权。
