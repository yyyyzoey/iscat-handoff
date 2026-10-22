# V134 执行摘要

- C-map 前向在 D>80nm 非零 xy 时混淆 D 与 h（M02-M04 err>50nm）
- M01 (D=53) err=-3.0nm 达标；M06 (D=187) +13.0nm 在 10% 目标内但撞边界
- 报告able_D=null all 6（C-map 前向不足以区分未知 h 下的 D）
- 关键发现：C-map 不能用于未知 h 的盲反演，必须用复场前向
- 全部 CONDITIONAL/SYNTHETIC；EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false
