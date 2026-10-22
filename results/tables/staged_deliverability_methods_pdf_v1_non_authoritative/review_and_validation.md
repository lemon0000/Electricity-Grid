# 方法章离线阅读版核对

2026-10-23。DRAFT_NONAUTHORITATIVE，文档排版与只读审阅记录。未运行科学模型、solver、Highs或主实验，未改变协议、B1—B3、门禁、P1权限或D/E状态。

## 交付与内容

[PDF阅读版](../../../paper/drafts/staged_deliverability_methods.pdf)为8页、512455 B，SHA256 035e4cd1344d24d37682ea97698debdd85d47a7470699f86d4a0faab5949295a；来自[方法正文](../../../paper/drafts/staged_deliverability_methods.md)原始24333 B、SHA 2152f85ad2b81a0fe65497e699f7b5760e6b3b239e42bc0d339182e11764e246。正文与63e58da2及上一轮领域审阅的字节相同。

166处数学表达式含23个display和143个inline，原TeX按顺序交给本地KaTeX。中文正文字符顺序与PDF提取相同，PDF公式编号1—23恰好出现一次。无KaTeX错误、页面横向越界、空白页或替换字符。PDF包含MicrosoftYaHei、KaTeX和Arial字体；61项本地JS/CSS/字体资产起止SHA一致。

root查看八页联系图和公式/表格放大图，修订公式及表格引导段换页，未见裁切、叠印、缺字或编号丢失。最终八张PNG与已视觉检查的最新排版逐字节一致；[收集核对](collection_checks_01.json)保存逐页hash，[最终生成记录](render_report_01.json)保存源、renderer、引擎与浏览器检查。临时PNG不作为独立科研结果，最终PDF可重新栅格化。

英文、数字正文与整体观感经视觉审阅；中文序列及公式结构检查不宣称机器证明了全部英文/数字语义等价。排版检查不提供公共网络数值或论文结果证据。

## 路径与只读审阅

[独立renderer](../../../paper/render_staged_methods.py)使用Python Markdown、Node导入已有Gradio KaTeX0.16.27、Chrome CDP及本机PyMuPDF。旧介绍renderer未执行。页面阻断HTTP/HTTPS依赖请求；控制器使用127.0.0.1 HTTP/WebSocket CDP，不是全机网络隔离。资产记录是本机所见字节，不是上游许可或外部资料资格的重新审查；没有下载依赖。

只读sol_reviewer /root/c_final_domain_review提出两项并读回闭合：入口在任何import/临时目录/输出前显式拒绝优化Python，避免关键assert被移除；网络字段分开记录页面阻断与controller loopback，cleanup范围限定为自建direct Chrome child。实际-B -O --help按预期exit1且未创建目录，见[日志](../../../results/logs/staged_methods_pdf_v1_non_authoritative/optimization_rejection_01.txt)。读回无剩余High/Medium R2 finding，无official verdict/seal/receipt。

审阅者未执行Python/Chrome或视觉审成品；最终页面由root核对。任意异常下全部Chrome后代退出尚未证明；本次结束后另查进程，不能推广该次观察。

## 保留的观察

首轮exit1：Gradio CSS scope未应用，检查在生成PDF前拒绝；[stderr](../../../results/logs/staged_methods_pdf_v1_non_authoritative/render_attempt_01_stderr.txt)、[Chrome日志](../../../results/logs/staged_methods_pdf_v1_non_authoritative/render_attempt_01_chrome.txt)与[未应用样式HTML](render_attempt_01_unstyled.html)保留。三个成功预览的记录见[02](superseded_render_02.json)、[03](superseded_render_03.json)、[04](superseded_render_04.json)，在公式/表格引导段与审阅修订中被后继替代。最终第五次文档渲染exit0；这些预览不是数值实验或独立样本。

既有只读核验器本轮exit0，确认B1—B3共118文件和历史绑定；另按保存checkpoint检查685条唯一已有路径，包括cost/business/evaluation、原介绍MD/PDF和P1注册，见[保存核验日志](../../../results/logs/staged_methods_pdf_v1_non_authoritative/preservation_01.txt)与收集核对。日志中的旧测试数只核对保存记录，没有重跑这些测试。

## 重建

此命令只创建新的系统临时目录，不发布/覆盖PDF；视觉核对后再复制生成的methods.pdf。PyMuPDF可通过--pdf-deps指定已有本机依赖目录：

    & 'D:/Miniconda3/envs/compute/python.exe' -B 'paper/render_staged_methods.py' --katex-js 'D:/Miniconda3/envs/compute/Lib/site-packages/gradio/templates/frontend/assets/katex-CnjCUzRs.js' --katex-css 'D:/Miniconda3/envs/compute/Lib/site-packages/gradio/templates/frontend/assets/katex-BPqSrETq.css' --pdf-deps 'C:/Users/Psychobabble/AppData/Local/Temp/electricity-grid-intro-20261017-qsjrsttc/deps'

字体、浏览器或库改变后重新排版和视觉核对。参数来源目前仍是组级边界，逐字段登记缺口见[来源审查](../../../docs/literature/staged_parameter_source_gap_20261023.md)。

本轮尝试删除五个专用系统临时目录时，命令在执行前被工具自动审批拦截，仅返回blocked by policy。未执行删除，也未改用其他工具重试；[后续只读观察](temp_cleanup_01.json)确认目录保留且没有相关渲染/科学进程。此限制不改变已交付PDF和保存核验。
