# iSCAT v063 审查正文

## 完成
- A1 严格类型重聚合：r6_per_trial_quality_fixed.csv（1000 行，显式布尔解析，写后回读断言 PASS）；分层统计 B01=19+81、B04=4+96 与 GPT 预测一致；SSE 对账 B01 用相对容差 1e-12 PASS（绝对 1e-20 容差错误，已记录）。
- A2 状态语义：12/12 机器检查 PASS（CP/Wilson 公式自检精确一致）；r5_val CP_U95=0.009936081944457708 已填入；status_semantics.json 顶层拆分。
- M0a：确认目录内无真实提取器源码（仅历史 FFT 产物）；M0b：**16/16 解析参考测试 PASS**（ANALYTIC_REFERENCE_ONLY：显式离散求和 vs FFT rel~1e-14；exposure sinc 因子 0.9973701827725034 精确；双频/相位/背景归一化全覆盖）。
- M1：**Fe3O4 材料合同完成**（refractiveindex.info/Querry 1987，CC0，612 点；520nm n=2.349 k=0.083；文件+来源哈希登记；LITERATURE_MATERIAL_EXPLORATION 模式）。
- M2 60nm Fe3O4 均匀介质 BEM vs Mie（1444/rule3）：**复远场 rawL2=0.0039 PASS**、散射 0.0079 PASS、消光 0.0078 PASS；吸收截面对比 1.99e305 = 作者 miesolver absorption() 不支持复 n 吸收颗粒（TOOL_LIMITATION，已诊断）。
- **B1 十新条件泛化验证 PASS**：B01–B10（xy 至 ±617nm）前向 0.69%–1.20% 全部 <2%；拟合 D +0.09~+0.16nm、定位 ~0；零边界命中。

## 未完成
- M2 30/100nm：DEFERRED（吸收对比工具限制待 GPT 处置决策；复远场主门槛 60nm 已 PASS）；M3 分层三尺寸：NOT_STARTED（6 笔预算未动）；A3 4-seed 重建：NOT_STARTED；A4 完整匿名驱动：PARTIAL；B2 profiles：NOT_STARTED；P0 Hook 覆盖/贡献审计/1e-10：OPEN。

## 下一步
1. GPT 处置：M2 吸收对比工具限制（以复远场为主门槛继续 30/100nm？或先修 miesolver 吸收接口？）；
2. M3 分层 60nm 两笔（576+1444）在放行后启动；
3. P0 Hook 捕获与批量候选（队列空闲）；磁材料实测输入仍需用户提供。
