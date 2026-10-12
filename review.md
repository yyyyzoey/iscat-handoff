# iSCAT v070 审查正文

## 24 受控后处理完成——关键发现

** prod-fine 差异 100% 来自网格分辨率（576 vs 1444），后处理参数贡献为零。**

36 组比较证实：
- P_base−P_common = 0.0000（生产 576 加精细角度/Bessel 后完全不变——已收敛）
- F_angle−F_base = 0.0000（精细 1444 用生产角度无差异）
- F_bessel−F_base = 0.0000（Bessel 表减半无差异）
- F_q7−F_base = 0.0005–0.0007（q7 vs q5 有微小影响）
- **P_base−F_base = 0.0054–0.0062**（网格差异是唯一因素）

结论：提高 prod/fine 一致性唯一途径是提高生产网格分辨率（更多 BEM 成本），后处理调优无法改善。

## 24/24 render 全部 COMPLETED
## 36/36 比较全部记录（tables/controlled_results24.csv）

## 未完成
P0 Hook/批量/1e-10；R6 边界深度诊断；A3 seed 重建；磁材料实测数据。
