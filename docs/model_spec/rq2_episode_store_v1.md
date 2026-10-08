# 连续episode本地事务日志与开发恢复

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE，限定开发验证完成。

`episode_store.py`面向既有短预算EpisodeSession，提供同一规范目录内合作进程的排他执行、
求解前意图日志、结果原子提交和独立来源重放后的开发续跑。不是production lease、seal、正式运行授权或工程认证。

## 输入与范围

调用方独立提供typed common/四臂初态、完整预定EpisodeHourInput tuple及selector/spec/budget。
整窗身份绑定全部输入；每次结果archive另用有序已消费prefix的身份，不混用不同长度tuple。
运行只将当前小时交给EpisodeSession；未来输入只进入注册源身份，不进入当前决策接口。
header绑定完整规范目录、实现身份、SQLite版本、整窗来源和genesis状态。复制或移动数据库不构成有效续跑。
每个结果archive必须逐字节保留此前已提交的attempt prefix，末attempt.before_identity须等于前驱snapshot身份；
不能用另一条同样可重放的合法历史替换既有提交。intent与result追加均重核前驱commit head。
唯一性只限同一store root；不同目录上的相同输入不宣称机器全局exactly-once。

仅接受本地固定NTFS卷，拒绝reparse路径、非普通文件和多hardlink文件。
每次操作检查目录、锁文件和数据库identity；合作进程以外的恶意文件替换或管理员篡改不构成真实性认证。
SQLite sidecar同样拒绝reparse和多hardlink；WAL/SHM不在DELETE合同内。
进程内registry和Windows固定byte-range锁共同持有到连接关闭；不按PID清理、删除或截断锁。

## 事务顺序

1. 获取目录lease，核schema/header、完整连续日志和独立来源。
2. 在任何advance前完成当前小时纯admission和预算检查。
3. SQLite `BEGIN IMMEDIATE`插入唯一ordinal/predecessor的intent并commit，关闭连接、重新打开核对exact intent。
4. 只在intent核对完成后调用一次当前小时advance。
5. 完整archive BLOB、SHA256及commit head在同一结果事务提交，再重新打开重放核对。

SQLite采用DELETE journal、synchronous=FULL、foreign_keys、STRICT表及exact schema/user_version/application_id检查。
intent/result分别append-only，禁止REPLACE/UPSERT；序号或提交链间隙、额外schema、损坏记录均拒绝。
初始化采用create-only；空库或半schema保留并拒绝自动修复。
SQLite的系统崩溃一致性依赖本地文件系统和存储实现遵守同步语义；进程退出测试不等于断电硬件认证。

## 未决与恢复

已有intent但无result时，不能知道原生执行是否开始；永久禁止自动重跑或跳过该小时，不退还预留。
任何提交异常使当前owner进入indeterminate；关闭后可用inspect重新对账，不直接在原owner中再执行。
inspect不调用业务/solver，不返回执行游标；SQLite打开时可能进行自身journal recovery，因而不是磁盘只读接口。
完整结果已提交时，独立typed输入下全链重放通过且外部保留的expected_head匹配，才可重开并继续下一小时。
terminal、partial、interrupted或未决intent均不提供下一小时执行能力；缺失调用数保持unknown。
结果commit完成但响应丢失时，可inspect确认已提交head并由调用方独立保留，再进行显式重开；不重做该小时。

为复用重建结果，episode_replay私有_verify返回(report, reconstructed snapshot或None)，
公开replay_episode_archive仍只返回诊断；不从SQLite JSON直接制造执行状态。
所有正式、容量、安全和完整履约门保持关闭。
StoreInspection另显式标记native_execution_authenticated=false；续跑能力只针对已声明的开发合同。
沿用原EpisodeBudget的120次调用/60秒总预留上限及各selector短预算，尚未覆盖正式网络规模与连续多日实际求解预算。

## 验收

开发测试覆盖真实短预算继续执行、同进程/跨进程排他、stale head、输入与schema篡改、复制目录、
提交前后异常，以及意图前、意图后、advance中、结果前、结果commit后五个子进程os._exit窗口。
另覆盖可独立重放但重写旧提交历史的archive、无attempt返回、unlock异常、真实NTFS junction、
hardlink与sidecar、PRAGMA漂移、唯一predecessor及未完成初始化拒绝。

最终独立31项targeted通过（360.92s，exit 0）。主线程同一最终字节三文件101项相关回归通过（562.22s，exit 0），
包含本层31项、episode_replay 39项和episode_coordinator 31项。git diff --check通过。
此前20项（262.82s）和history/no-attempt/unlock三项（70.16s）仅为开发中间验证，不替代最终101项证据。
独立pre-seal确认历史前缀、前驱head、result输入、handle释放等findings闭合，限定范围无开放实质问题。
本次没有formal run、production lease/seal、official receipt、外部下载或仓库清理。

测试命令前缀：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`；
三个文件为`tests/test_rq2_episode_store_v1.py`、`tests/test_rq2_episode_replay_v1.py`和`tests/test_rq2_episode_coordinator_v1.py`。

开发SHA256（非production seal）：

- store source：`872f32a632c83b084139973d7aa38249dfc1099dea14e447902c23429873af8b`
- store test：`f249ff3c97a6b867eb9c22196698443f2c3820490663f11a7a5b94a888c40ab2`
- replay私有重建接口source：`793605f81cc816c3466d28e6f671e2ef6003a7b1a484e2f676397b41b77014ed`

下一项核对正式网络规模与连续输入适配；完整数据、训练容量/固定策略绑定及恢复/right-censoring科学验收仍未完成。
