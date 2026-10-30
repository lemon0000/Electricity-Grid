# F：host Win32 resource provider 源码准备

2026-10-30，DRAFT_NONAUTHORITATIVE。继承host preentry v1；本步写实际Win32 API调用body，并在仅替换DLL/clock的私有ordinary域连到完整host协议。它是完整provider中的resource组件，公开WindowsResources/open_windows_resources/mechanical发行者仍关闭；source-authenticated issuer、文件publish/checkers、broker accept/cancel仍未实现。

新增 `host_windows_resources_v1.py` 与独立 `full_role_host_preentry_v2.py`。后者从provider取得 `(six original resources, pending responsibilities)`，用原acquisitions恢复cleanup；完整六键含None的责任映像传给terminate/identity/quiet。缺损镜像不能覆盖原Native持有值。原host v1/Core51及历史字节保持。

物理body使用与原normal_process相同的七组ctypes字段；普通测试另用Win64 size/offset常数核Basic64、IO48、Limits144、Startup104、StartupEx112、ProcessInfo24、Accounting48及MBI48。CreateFileMapping/Mutex返回既有对象时会带ERROR_ALREADY_EXISTS，故保留取得的HANDLE后拒绝，不能清零或修改既有mapping。[CreateFileMappingW](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-createfilemappingw)、[CreateMutexW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexw)定义这些语义。

endpoint按Core51固定名称、noninherit、69632B布局创建，初始内容双读为零；mutex下先写header body/hash，再最后写8B marker，完整readback和mutex release成功才header DONE。abandoned仍取得所有权，须release一次并拒绝；timeout不release；release不明不重试。header publication有独立ISSUED/UNCERTAIN账本。

Job设置kill-on-close、process1GiB/job2GiB commit；JOB_LIST属性值与buffer保留到DeleteProcThreadAttributeList。flags为NO_WINDOW/EXTENDED_STARTUPINFO/CREATE_SUSPENDED/UNICODE_ENVIRONMENT，实际process/thread HANDLE、PID/TID/creation、membership、noninherit及child image均核对。[UpdateProcThreadAttribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)说明Job-list和属性值寿命；[CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)定义参数与输出结构。本文不由这些文档推导caller在API执行中被杀时的完整结果保证。

预分配PROCESS_INFORMATION在Native调用前存在；恢复observer仅单向capture原输出，再返回所有已知资源及未决责任。constructor/attribute/header/stop不确定都不能被空镜像抹掉。mapping等标量HANDLE在Native返回到首次Python持有之前仍有窗口；普通test39明确模型化未捕获句柄、保留UNRESOLVED，不称无泄漏。完整真实broker寿命、外部guardian和Native失败/停止专项必须继续解决该边界。

ResumeThread期望返回原suspend count1；Resume/Terminate/Close/Unmap及attribute delete均调用前ISSUED，不确定时不重试。[ResumeThread](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread)定义返回含义。HANDLE关闭后以ERROR_INVALID_HANDLE核验，view以VirtualQuery MEM_FREE核验；这些是即时观察，地址/HANDLE复用与观察窗口不能转成永久证书。[MEMORY_BASIC_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-memory_basic_information)给出layout/state语义。

成员HANDLE按每次取得的独立generation保存，不能以裸数值复用旧close状态；primary process record独立于aux。记录上限1024是本组件保守metadata帽，原member handle上限1024保持，整链适用性待预算审查。active census不允许sticky失败后扩大责任。stop前census最多0.5秒并受原global deadline限制；失败也必须继续issue TerminateJob。quiet再取host给定<=5秒且不越原deadline的绝对窗口，贯穿每个PID/open/identity/wait与最终双accounting。

成功quiet条件仍为retained handles全部signal、原child身份在完整member集合中、active0/final pids空、total==observed count且两次accounting稳定。Job-only需零成员quiet；thread-only/身份未知保留所有资源。短命descendant若在census间出生退出，total增加但无法取得HANDLE/creation，必须UNRESOLVED保留；本host尚未接active monitor或completion port，故该成功条件不能解释为一般完整F树都能完成quiet。test24覆盖缺失成员反例。

provider强持当前thread对象、PID/ident和opaque owner；还没有source-authenticated owner seal。descriptor/limits的closed-keyset依赖host exact producer，provider没有独立完整schema authority。Native/clock回调新增reentry会拒绝，已有poison允许best-effort recovery/cleanup；每次cleanup以入场baseline区别新增错误，provider reentry/census failure通过snapshot pending传给host，不能因本地物理关闭而抹去。provider/root/CodeType协调破坏、完整TCB/check-use及真实Win32 ABI交互/时序/路径/Native等价仍OPEN。各关闭域独立尝试；已知失败和未知责任不退款、不转为成功。

验证仅接受 `host_win32_resource_source_and_private_protocol_synthetic_only`。只替换DLL/clock与显式memory-write故障；ctypes buffer都是测试自建。完整request/OFFER/ACK、manifest/header/binding/release与这些resource body同进程连接，但context、manifest/transport checker、文件publish和外部host acceptance仍为synthetic旧fixture。完整F/Guard2/context载入/实际profile、whole-workflow wall/RSS/storage和运行授权保持OPEN；NFC12不重跑。
