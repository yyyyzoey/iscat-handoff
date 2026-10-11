# iSCAT v062 审查正文（收口）

## 完成
- A1：r4_camera_summary_schema_fixed.csv（case 列恢复，12 字段全对齐，csv_schema_checks 11/11 PASS）；原表保留。
- A2：R5 dev 100/100 + val 300/300 ID 完整（0 重复、0 误报维持）；R6 1000/1000 行从 fit_record.json 全量重建；边界标记 B01=19、B04=4（与 GPT 推断一致）；双总体统计（全合法 D 返回 vs 检出且可报告）分列；trial601 溯源=崩溃首跑的 observation 重拟合；匿名协议缺口如实记录（路径含 D，无证据真值进入拟合参数）。
- A3：threshold_freeze 原件未动；freeze_lineage_recovered.json 区分同期/事后/缺失；R5 原始帧 original_raw_available=false（当轮未持久化）；开发日志 1 样本阈值=幂等续跑 bug（同会话修复，验证加载的是 100 样本冻结——日志顺序已记录）。
- B：R6 边界证据=逐行标记（B01 zf 下界 375、B04 zf 上界 575），深度场级诊断延期。
- P0：参考工具修复完成（2/2 额度用尽）→ 独立标量参考与基线 Npair>=2 位级一致（refSL=0）；候选 Npair=1 三模态修复（差 1.27-4.37e-11）；基线 Npair=1 OOM 三模态确认；**昨日 duffy1 OOM 今日未复现（diag-expansion fill 跑通，duffy1 未被调用）→ 判定环境内存压力假设**；rule7 参考仍被 1e-10 门槛阻塞。
- M：仪器模板在位；磁材料数据缺失留空；M2/M3 阻塞（预算 9 笔 BEM 未动用）。

## 未完成
- rule7 参考（1e-10 门槛未过）；批量候选（待需要）；边界深度场级诊断；磁 M2/M3（等输入）；extractor 源码未定位。

## 下一步建议
1. 向 GPT/用户索取磁材料常数与提取器源码/合同输入；
2. P0：1e-10 分块等价性攻关（blocked-vs-unblocked，与 expansion 无关的纯浮点顺序问题）；
3. 磁 M2/M3 在输入到位后按 9 笔预算执行。
