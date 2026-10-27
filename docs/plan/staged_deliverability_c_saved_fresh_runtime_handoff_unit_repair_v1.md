# runtime handoff：一次显式 unit timeout repair

2026-10-27，DRAFT_NONAUTHORITATIVE。原scope已声明unit主组12s及唯一repair15s、共享static75/unittest35/total110，不改帽。原17 nodes首次capture在11.342903s超时，stderr恰15个成功点，没有完整report；费用保留。父process HANDLE关闭、reader/pipes终态，无cleanup、truncation。该次为第16条累计意外不接受记录；不能称17组通过。

本次不修改任何已执行helper、test、parent、probe、原driver或结果。另建core v6、import helper/parent/probe/tests各v2、repair_driver_v1.py、repair_registration.json、repair_helper_snapshots.json及独立unittest_repair admission/report/exit；namespace v2复用。原registration、transport和helper snapshot全部逐字核验。两个registration合计≤3s，两个unit合计≤35s；唯一repair单次≤15s。原failed exit不改accepted。

版本后继关闭PRE_SEAL剩余finding：bootstrap validator验证完整B_S源码/导入根/闭keyset后生成expected-binding tuple；runtime强持proof并在prepare/pending/entry核验，factory/loader首次依赖helper globals之前用held CodeType/native defaults核验，audit内用无code-getter的identity reader避免重入。boundary terminal bookend放在external raw读后，final commit异常同时保留原primary和close_commit secondary并强制FAULTED。

新unit共20个固定node，追加coherent B_S globals同步替换、已有primary+final digest failure及external读后terminal mutation三项。普通owner/namespace逻辑fixture只强持ENTRY raw，以避免17次重复Source49磁盘书挡；adapter global图正例仍用完整49 raw/map。该优化只减少逻辑fixture I/O，cold生产factory仍强持并重核原49，不能用unit替代完整Source49实际证据。新controller后续阶段须unit修复通过且独立PRE_SEAL must-fix关闭后接续。

同目录仍≤40文件/8MiB，stdout/stderr/cold次数、caps及所有false gates沿原scope。无cold启动、native模型、solver、P1、科学replay或F授权。本文件补充原scope，不改其已经登记的字节。若再次超时/失败，保留并停止当前执行路径，不追加第三次unit或自动扩帽。
