# 受控四臂连续episode开发owner

状态：DRAFT_NONAUTHORITATIVE。`scale_episode.py`连接完整UID selector controller、归档回放及四臂事务。固定输入窗口、初始reference请求与四个规范ArmSetup；不修改旧episode/store或冻结结果。

## 调度与记账

在新NTFS non-authoritative root持有唯一lease。窗口包含连续source hours；四臂business机制与physical origin相同，capacity及其declaration可不同，actual selector/spec相同，预算只允许规范role差异。reference和四臂绑定同task、resource contract及UID。

入口现要求原始`resource_plan`声明，与实际窗口、来源audit、envelope及五role预算重算绑定，header完整保存该声明。详细资源算术及证据边界见`rq2_scale_episode_resources_v1.md`。所有绑定在创建root之前检查。

header固定worker、controller进程工具、资源/lease及native replay传递源码依赖身份。每phase前后检查，不能以新算出的phase pin替代窗口固定实现。调用环境先复制并验证，仅以摘要写header；实际值不落盘，每次检查重新比对摘要。这里仍是调用者显式提供的开发环境，不构成正式受控环境验收。

每小时先独占写入完整五phase累计调用/秒数预留intent并exact回读，再逐个调用现有受控Job父控制器。整个Job静默之后取得归档内容，绑定receipt/store/result并做数值回放。共同reference publication只生成一次，按规范四臂顺序执行；business拒绝或前一小时已halt的臂不创建actual task，但仍占用预留。

小时result含规范五phase evidence清单：执行项记录相对task root、controller/process身份、receipt/store/result/record及replay身份，和已消费result/receipt/SQLite文件pin；跳过项记录明确原因。所有臂结果准备完成后写小时result并回读，随后发布内存publication/cursors。中途异常保留intent和已执行子任务，owner变为不可重试；不把缺少结果解释为零调用或数学不可行。

收集工件时先持有task-root existing lease，再嵌套持有archive lease，直到文件pin、controller result exact比较、receipt SHA和record二次回读交叉核验完成。后续owner检查所有已消费工件的文件身份与摘要。close与advance使用同一非阻塞guard，推进期间不能释放episode lease。

## 范围边界

result是可审计开发观察记录，不是可恢复checkpoint。当前没有重开继续执行入口或production seal；独立全episode离线核验已由`scale_episode_replay.py`提供。文件一致性核查为合作式本地保护，不认证恶意篡改或原生执行事实。预算预留计算不替代controller整体wall/内存/目录大小验收，也不是硬磁盘quota。

所有数值示例是合成机制输入；normal来源/最优性、实际公共数据、右删失、完整资源与正式科学验收仍各自需要证据。`observation_window_consumed`仅表示观察窗口被消费，不表示恢复完成或完整履约。formal、whole_task_resources_verified和resume标志保持false。

## 验证记录

初轮4项通过（36.47秒）；真实两小时及后续task中断2项通过（54.67秒）。增加phase evidence及消费归档漂移后7项通过（113.13秒）。独立pre-seal指出phase证据关联、读取至pin窗口、传递实现闭包和环境值落盘问题；修复后8项新增故障反例通过（40.04秒）。最终全套15项通过（152.28秒、exit0），git diff --check通过。

端到端小例第一小时五个实际Job，第二小时四个实际Job；CFE-only已halt不再求解，但累计预算仍22 calls/22 solver seconds预留。JOINT债务由1/3到2/3。late failure保留已完成的actual:0归档但不发布整小时结果。篡改已消费SQLite、读取后替换receipt/result、store/process/resources/lease/codec源码漂移均拒绝推进。伪token值不出现在header，环境变化被摘要检查拒绝。测试工件仅在pytest临时目录，不是H25或正式运行结果。

最终限定独立pre-seal复核闭合，scope内无剩余实质finding；不构成official verdict或正式运行授权。
