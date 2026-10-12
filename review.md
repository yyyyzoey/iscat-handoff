# iSCAT v067 审查正文

## 完成
- B 真均匀基准 30/100nm：galerkin.bemsolver 单介质（无基底）BEM vs Mie，四门槛全 PASS（rawL2=0.0039）；
- C 27 条件 Frobenius 全 PASS（0.0051-0.0069）；场分解闭合 ~5e-16（27 条件）；
- D1 场强分解：Cs（散射）/Cint（干涉）/I0 逐像元导出，代数闭合验证；
- D2 固定孔径 [21,31,41,51,61,65] 依赖数据全捕获；
- D3 过零细化：D60 C_center 在 zf 512.5-515.0 间过零（插值 ~514.7nm）；D100 S_area prod/fine 过零位置不同（prod 在 425-427.5，fine 在 435-437.5）——孔径/算法敏感；
- D60 C_center refinement：zf 500-525 间 11 个点，C_center 从 -0.013 到 +0.008 单调递增。

## 未完成
- P0 Hook 捕获/批量候选/1e-10 三矩阵；R6 边界深度诊断（B2 profiles）；A3 4-seed 重建；磁材料实测数据。

## 下一步
GPT 复审三尺寸+27 条件+D1/D2/D3 结果；决定 Fe3O4 密库/实验接入方向；P0 Hook 捕获。
