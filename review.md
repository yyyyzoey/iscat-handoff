# iSCAT v061 审查正文

## 完成
- A0 报告订正：r4_camera_summary_rechecked.csv 由 200 行逐次以 repr 精度重算（Bias/RMSE/双口径 Std；恒等式残差 ~1e-17）；状态字段保留为 fit_scope_label，未改标定语义；边界计数单列。
- R5 检测开发→冻结→独立验证：100 开发空白（tau=-0.73833935560801289，threshold_freeze.json）→ 300 独立空白 **0 误报，CP U95=0.009936 ≤ 0.05 PASS**（与合同自检 0/300 值精确一致）。
- R6 独立盲测：预注册 B01-B10 十条件（28.9-85.1nm × zf 381.7-573.1 × 大位移 xy）→ 10 笔 1444/rule3 精细参考（230-288s/笔）→ 1000 采集/9000 帧/1000 拟合 → **逐条件 100/100 检出，Wilson L95=0.9737 ≥ 0.9 全部 PASS**；尺寸 Bias +0.096~+0.160nm、RMSE 0.118~0.299nm、定位 ≤0.176px（双口径 Std 在表）。
- synthetic_detection_validation=PASS（范围限定：中央 41×41 + 预注册搜索 + 合成金球）；experimental_validation/calibration 仍 false。

## 未完成/开放
- P0：Npair=1 独立参考一致性（测试工具额度已用 2+2，记录保留）；Hook 捕获；批量候选；1e-10 分块等价性（2.58848e-7）；rule7 参考未放行。
- 磁接入：材料数据缺失留空；提取器合同 NOT_STARTED。
- R6 的 B01 trial601 记录在崩溃重试后由磁盘补齐（1000/1000 完整）。

## 下一步建议
P0 Hook 捕获（生产队列已空闲）→ 布局一致性 → 批量候选 → 1e-10 三矩阵 → rule7 参考；磁材料输入向用户索取。
