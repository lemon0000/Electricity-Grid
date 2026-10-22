# 领域手算与开发审查记录

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT。root唯一writer；public_necessary_model（sol_modeler）和c_final_domain_review（sol_reviewer）仅做只读核对，无Python/solver执行或文件写入。本记录是开发说明，没有official verdict、seal或receipt。

独立手算来自三个YAML与既有loader/必要条件规格：a=5/4、D=40、aux=5；before F/X/C=120/40/160、after=160/100/260。设备K/idle从h=2起由160/16变240/24；电网on_time从h=2、delayed从h=4建成。f在h<0为0，其余2/5。full-C w_hat依次只有108、delayed-before的100、after的180，actual workload为100/140且不用于该w_hat。

关键手算锚点：h=1的q_X=32、q_CFE=28分别通过，独立加总q_joint=60>D40且>f*w_hat=43.2；未知g允许上限15 MW，g10通过该松弛、g20失败。on_time/late/h2的h_hat=100、q_CFE=80>D40，上界g_max=-50保留，任意非负g都不能补救该一小时共享需求。delayed/h3的参考P0=210>C160，仅保存固定参考策略连接缺口50 MW。正g能够修复单纯设备活动>K的g0失败，不能把所有g0失败泛化。

独立手算40行预期为whole-X 12/28、normal-g0 31/9、joint-gX 8/32（pass/fail）；登记16行分别12、15、8 pass。前史8行不计入登记合取，随访16行也单列。whole-X恢复既有三个条件；新增设备诊断另存，当前固定40行设备诊断均通过，但它不是原whole-X合取的一部分。实际g、网络点、139节点、完整时序和正式结论没有在此手算中产生。

PRE_SEAL审查提出并由root修复的事项：

- M1：whole-X字段语义应等价冻结三条件。现保留三条件，新增设备诊断单列，K=0反例证明不改变原合取。
- M2：源pin必须对应实际导入。现固定root/cwd/sys.path和file-path CLI，helper/package在导入前由本地stdlib按固定SHA读取；module.__file__及关键函数co_filename再核对。拒绝预加载src/experiments/yaml及全部子模块。postcheck要求精确13项project和21项parser集合、版本、路径及非权威状态，不能接受漏掉oracle pin的报告。
- M3：补齐create-only失败窗口。pytest tmp注入existing/concurrent mkdir、mkdir/open/partial/shortwrite/readback异常/读回不一致/末端wall失败，核对保留字节与拒绝重试；没有宣称覆盖真实坏盘、掉电或阻塞IO。

测试日志targeted_01至05是同一草稿修复过程，去重为50项；related_01另95项，共145项不同普通检查。各次均exit0，旧回归产生1605条既有PYPOWER matrix弃用提示。普通回归可能构建模型，不能把算术CLI的零科学构模标签扩展到全部测试过程。

reviewer最后复核未见剩余High/Medium PRE_SEAL finding；CLI及保存后核验在该审查闭合之后执行。审查闭合不预写执行结果，最终状态及实测以同目录development_checks.json和外部报告为准；本说明不授予native或正式运行权。
