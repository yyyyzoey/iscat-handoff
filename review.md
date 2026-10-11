# iSCAT v064 审查正文

## 关键纠错
- v063 M2 60nm 被确认为 MATERIAL_INPUT_CONTRACT_MISMATCH：脚本写了实数 2.4321 而非复数 2.349+0.083i。已标记 FAIL/隔离，不删除。

## 完成
- M1R：Querry 源文件 sha256/git blob 双重验证（blob match E01）；精确节点 n=2.349 κ=0.083（exact_node=true）；引用年份 1985 修正；负向夹具 2/2 拒绝；Material readback 复数保持。
- M2P：零 BEM Mie 验证——目标 Csca=73.87/Cext=237.98/Cabs=164.11（阶数收敛）；对照 complex(2.349,0) |Cabs|/Cext=5.8e-16；旧错误 2.4321 Cabs=0 诊断。
- M2R：修正材料 60nm BEM 四门槛全 PASS：rawL2=0.0039、sca=0.0079、**abs=0.0042**、ext=0.0054。
- M3：60nm 分层 prod(576)/fine(1444) 前向 relL2=0.0053（两焦面均 <2% PASS）。

## 下一步
30/100nm M2R+M3（脚本已就绪，预算 4 笔 BEM 剩余）；R6 边界深度诊断；P0 Hook/批量候选。
