# V156 review

12组per-pixel Jacobian全部使用真实历史候选theta完成（非默认[200,450,0,0]）。
每个候选theta来自V152保存的6起点中Q_joint最低的完整记录。
关键发现: 正确候选处的局部信息与默认参数处显著不同。
reportable_D全null; EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false。
