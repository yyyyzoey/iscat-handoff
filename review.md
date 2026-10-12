# iSCAT v069 审查正文

## 完成
- A：K2 修正完成——27 行的 K_S2_fine 用 Frobenius（norm(vec,2)）替代谱范数（norm(mat,2)）重算；原始值保留对比；
- B：30/100nm 均匀解 fm 数据限制如实记录（fm 不含 pixel_size_nm，且 rawL2 在已存数据中可用）；材料 readback 说明补入；
- C 24 受控 render：NOT_STARTED（会话预算耗尽，需新会话执行）；
- D 误差分解分析：**D100/z450 chi1=423-744 极端正负抵消**——大颗粒近焦面的干涉条纹正负瓣在像元积分中大量抵消，导致有符号面积积分对细微 prod/fine 差异极敏感（K_S2 达 547-963），而全图 Frobenius 仍 <2%。这不是工具错误而是大颗粒散射场的数学特性。

## 未完成
- C 24 受控 render（6×4 诊断配置）；P0 Hook/批量/1e-10；R6 边界深度诊断；A3 seed 重建；磁材料实测数据。

## 下一步
GPT 复审 chi1 发现；决策是否需要调整 D100 条件的评分方式；P0 Hook 捕获；C 24 renders 新会话执行。
