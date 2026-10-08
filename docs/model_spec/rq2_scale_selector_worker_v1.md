# Selector固定worker与受限请求传输

状态：DRAFT_NONAUTHORITATIVE。实现为`scale_selector_worker.py`，使用已有selector store；Windows Job监督复用`normal_task_process.py`。本文件描述开发接口，不授予正式运行权限。

## 请求与实现绑定

请求为完整`SelectorRequest`的canonical JSON，只接受代码列明的输入dataclass、精确有序字段、tuple、有限hex float和基本标量。限制16 MiB、32层和100000节点；解码后要求完整字节roundtrip。文件读取检查外部SHA256及regular single-link文件身份。输入传输仅重建外部声明，不证明normal最优性、前驱来源、真实观测或执行许可。

worker identity绑定自身、reference selector、actual selector、网格状态、codec、store、资源合同、workload及solver等依赖源码和运行依赖。调用前、结果返回后、回执写后复核实现与请求。源码固定不等于受控正式环境；开发测试使用继承环境并显式限制数值库线程。

## 一次执行与回执

只创建新的`*_non_authoritative` store，执行一次并关闭后写新回执。回执以exclusive create写入，检查写入长度、flush/fsync、文件身份、exact bounded readback，再核验源码和请求。回执中保留store binding、结果identity及inspection，formal与whole-task resources标志固定false。

回执不是原子发布或恢复授权。中断、短写、错误内容和读取失败均不能当作成功；已提交store保留供检查，不能因此重新求解。缺失回执不能推出零调用。父进程必须先确认整个Job静默，再检查工件，并独立持有请求和实现pin。当前尚缺持久父控制器的启动意图、子进程身份登记及完整资源/episode事务集成。

## 验证

17项worker测试通过（16.40秒），覆盖两种输入roundtrip、封闭类型/字段、结构与文件限制、reference selector源码漂移，以及回执no-op、短写、错误字节、读取失败。失败后store保留结果且同一请求位置不能重执行。

其中两个真实Windows Job小例分别完成reference 3阶段和actual 2阶段；suspended状态不创建store，退出后确认whole Job quiet再读回执和store。每例30秒/768 MiB仅为合成验证预算，不证明H25、完整四臂或正式环境认证。复用进程工具的期限、commit/disk reserve停止及存活后代静默4项回归通过（2.07秒）。未启动真实规模或正式实验。
