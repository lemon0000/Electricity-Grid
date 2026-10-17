# H1 路径检查优化开发合同

2026-10-17，DRAFT_NONAUTHORITATIVE。对应里程碑 2 的整链性能修复。

## 问题与范围

现有六次 common arm 剖析中，1,340,616 次 nt.stat 占 92.206 秒自身时间。
历史重放在每次文件观察时重新解析路径及全部祖先。当前 chain_07 的代码和进程不修改。
本后继只优化 episode_store._path 的祖先路径检查，保留全部文件字节观察、数值重放、
common/Parent/Rref 校验次数、失败优先级、回调和提交顺序。

跨 common/Parent 调用复用完整验证结果仍需另行证明完整动态闭包；本候选不声称已解决。

## 优化条件

- 仅 Windows，明确给定 canonical roots；相对路径、dotdot、短名称和非覆盖路径走旧实现。
- 第一次仍执行原路径校验；按顶层向叶端持有所有现存祖先目录的 LIST_DIRECTORY/READ_ATTRIBUTES 句柄。
- 句柄不共享数据 WRITE/DELETE，阻止祖先替换和重命名；新文件创建和内容修改仍允许。
  FILE_WRITE_ATTRIBUTES 不受该共享限制，真实 FSCTL_SET_REPARSE_POINT 反例表明它能原地改写
  junction，因此每次使用仍通过持有句柄重新检查全部祖先 reparse 与 case-sensitive flags。
- 持有句柄并再次完成原校验后，才允许后续调用复用该路径的祖先结论。
- 每次重新 lstat 最终分量并拒绝 reparse；文件内容、文件身份及其余校验由原调用路径照常执行。
- 缓存键与 root 覆盖范围均使用大小写敏感的精确路径分量，避免 NTFS case-sensitive 目录混同。
- 无法取得目录保护、目录尚不存在或达到容量上限时回退，不据此缓存路径。
- 作用域单进程、单线程、一次使用；异常或退出恢复原函数并关闭全部句柄。
  清理绑定独立保存在私有 registry，不依赖可被替换的 instance 字段；关闭失败尝试其余句柄，
  保留失败句柄并显式记录 cleanup_failed，同时保留主体异常。
- 这不是正式 execution lease、缓存数值结果、科学验收或资源准入。

## 有界验证预算与停止条件

先做真实 Windows 句柄、rename/junction、叶端替换、内容变化、fallback、线程和异常清理测试。
首轮窄测试最多 120 秒、单进程、512 MiB RAM、64 MiB 新增工件；超限停止该测试并保留终态。
通过后使用同一 chain_06 保存 arm，对原入口与新路径入口各执行一次；每成员最多 300 秒，
总预算 12 分钟、并发 1、1 GiB RAM、新增存储上限 128 MiB，不创建 Job、不调用 native。
测量前固定实际执行路径、代码/fixture/input hashes；保存完整 science/audit 输出及调用计数，
复核代码和保存工件未变。比例只支持该保存 arm，不能直接外推完整链或正式预算。

只有窄测试、等价对照、独立只读 PRE_SEAL 审查闭合后，才考虑整合新的有界完整提交与重开重放验证。
完整 common 证据复用或真实整链入口需要单独满足整体性能审查，不能由本局部结果代替。

## 首轮反例

unit_01 为 7 passed / 3 failed，终态保留。实测属性专用访问权限 0x80 的目录句柄
没有阻止 rename；采用参与 share-access 检查的 LIST_DIRECTORY 权限 0x81 后重新验证。
该反例针对属性目录句柄单独保护的设计。补测旧 validation_io_optimization_01 的完整
CodeReadLease 后，代码文件的不共享 DELETE 句柄仍阻止了祖先 rename；不能据前者
推断旧固定包整体失效。旧固定包原样保留，新路径候选不持有数据文件排他句柄，必须
依靠已验证的目录权限并补充真实 rename/write/junction 检查。
依据：[Microsoft CreateFile 文档](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)。
