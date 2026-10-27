# 本次V163审查证据范围

锁定HEAD: 06c54419c590b6ddadc50cd6117a7a54b2cf5ddf。
直接读取了分支、状态、verification、执行真实性报告、源码身份、发布复核源码及JSON、三个组的逐点数据片段、ANON_02两个完整原始预测点。

执行器v163_run.py的Git blob `ecb06af4e4d2c61012453ede67f6aca1de160b9b` 与已上传原V163包的同文件逐字节身份相同。已阅读本地完整代码。沿用GLS/预算/辅助设计三个文件也与固定Git对象一致。

发布审计记录：247测试，273前向（70+113+72+18），454 ZIP成员453manifest；这是Codex发布的回执，并非本次ChatGPT在容器已下载完整原ZIP并重新检查全部SQLite。原ZIP下载未成功，故不作这种声明。

本次本地独立复算：ANON_02/+5点的Q变化恒等式误差6.66e-14，局部sigma10/free系数比26.22125947，已保存有限直线总距离比1.60063781。该差异不等于精度比，也不是全局剖面结果。

V164在工作站先只读全量核验原ZIP/SQLite/像素与设计再放行；不重复已完成旧光学求解。

来源（均固定HEAD）:
- results/v163/status.json
- results/v163/verification.json
- results/v163/audit/independent_recheck_v163.md
- results/v163/audit/independent_recheck_v163.json
- results/v163/audit/independent_recheck_v163.py
- results/v163/probes/100000_ANON_02/07.json
- results/v163/probes/100000_ANON_02/23.json
- tools/v163_bundle/code/v163_run.py
