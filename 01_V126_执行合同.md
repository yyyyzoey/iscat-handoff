# V125 独立审查与 V126 连续执行合同

**项目：反射式 iSCAT 悬浮磁纳米颗粒单颗粒粒径测量**  
**仓库：`yyyyzoey/iscat-handoff`，不是 `ustbfjw/keyan`**  
**审查固定提交：`v125@36a231ec8319ae47906664bdc8b54c166727af5a`**  
**下一批：`V126_RECONSTRUCTION_ERROR_SEPARATION_AND_PARTICLE_SIZING`**  
**文件性质：已发布 V125 的审查结论 + 尚待 Codex 执行的 V126 合同。不是已完成的新仿真。**

## 0. Codex 先读：任务目的、当前裁决、这次做完什么

最终目标：从同一颗悬浮磁纳米颗粒的线性原始图像及背景中，估计该颗粒的直径；高度、横向位置和曝光不能被误当成尺寸。现阶段材料与光路仍有明确假设，输出是指定模型下的均匀球光学等效直径，不能叫真实磁芯绝对直径。

**V125 总裁决：`PARTIAL_ACCEPTED_REPAIR_REQUIRED`。保留 63 节点场库和 6 份直接物理留出；撤回“联合反演全部验收通过”的结论。** 已完成的计算不等于实现、误差、可辨识性和交付全部通过。V125 的六个 H01–H06 今后全部转为开发诊断集，不再叫新盲测。

V126 按以下顺序连续执行，不在一个小修复后停止：

`旧场接管 → 修状态/预算/坐标/比较器 → 用现有场分离优化误差与插值误差 → 统一前向与连续单/多帧反演 → 必要时只补一整行高度 → 冻结模型 → 六个真正新的直接 L1 留出 → 独立空白与含噪评价 → 正确曝光/多帧研究 → 原数组与唯一 ZIP 返回`。

本批优先利用现有库，**不再开启 63 个系统的无条件重算，不同时扩大到三种材料，不改变用户已准许的模型以凑结果**。新 BEM 最多 16 次尝试、新 render 最多 128 次、合成相机曝光最多 6000 次；失败重试也计数；最多 12 小时，最后 30 分钟收尾。预算使用必须事前预留、实际累加。

用户不需要再补齐参数才允许这批条件研究启动。若某条数值物理路径确实不合格，暂停它的依赖分支，保留原因，其余可离线研究与交付继续。不能产生假图样或以参考场自由缩放填补缺口。

---

## 1. 本次审查的证据边界

本次已读取固定分支引用、源码、配置、训练清单、逐例 CSV、资格记录和外部回执。对六例发布估计做了独立算术统计，并对归档误判与曝光粗采样索引进行**最小源码等价复现**；这些复现及 JSON 已放在本交接包中。

**本次没有独立打开完整训练 HDF5、原始 MAT 或原结果 ZIP，没有运行 MATLAB/BEM，没有重新运行全部原反演。** Git 树存在二进制数组，不等于本次已经验算其内容。文中的“库已交付”“资源计数”“原场重放”等，若无特别说明，指 V125 发布清单/报告所支持的范围。

固定树给出了约 48.1 MB 训练 H5、4.57 MB 留出 H5、56.3 MB 平移表 H5。本次取得了原 ZIP 回执，未取得 ZIP 本体；回执自带矛盾，不能凭其 `true` 验收。[R14][R15]

所有源引用见末尾 R01–R24；本交接包中的 `tools/reproduce_v125_review_checks.py` 是**审查辅助工具**，不是 V126 电磁前向或反演器。下文列出的 `v126_*` 入口是要求 Codex 实现并运行的任务，不宣称它们已经存在。

## 2. V125 可保留的进展

1. 主库清单为 `D=[30,50,70,100,130,160,200] nm`、`h=350:25:550 nm` 的 63 节点；每个节点列有宽场。最终清单为 **14 个 V124 复用节点 + 49 个 V125 来源节点**。入口曾验证 15 个可复用节点，但 D100/h450 后来重算，不能将“15+48+1”误当成 64 个独立训练节点。[R02][R03]
2. H01–H06 是不同粒径、非节点高度和非零横向位移的直接 L1 条件，确实比固定高度的旧研究向最终任务前进了。场文件和失败结果要保留。[R04]
3. `v125_mie_fixed.py` 已使用 `psi=z*j_l`、`xi=z*(j_l+i*y_l)` 等相容复数公式；发布的无吸收能量和匹配小例改善成立。不能继续把 V124 错误 Mie 公式当成当前版本。[R11][R20]
4. 新平移函数已固定源坐标、仅对散射场查询平移并保留相机参考场；旧“源/查询坐标一起移动导致原数组不变”的具体错误不应继续指责新函数。可是非零位移数值资格仍未真正验完，见第4节。[R08][R11]
5. 运动单位已加入 `1e9` 转成 nm，生成三维 1.25 μs 细路径，已不像 V124 那样在曝光内必然读取同一位置。中位数等统计定义也已修复。[R09][R11]

**保留这些成果，不等于给整个反演授予资格。**

## 3. 六个直接留出：实际误差与不能得出的结论

只统计 `AT_TRUE_OFFSET_BLIND` 六行，不把另六行居中诊断算作独立样本：[R04]

| case | 真 D/nm | 估计 D/nm | D误差/nm | 真 h/nm | 估计 h/nm | 重要状态 |
|---|---:|---:|---:|---:|---:|---|
| H01 | 37 | 32.761629 | -4.238371 | 362.5 | 350.000000 | 高度下边界 |
| H02 | 63 | 42.122424 | -20.877576 | 387.5 | 384.199863 | 600次计数耗尽 |
| H03 | 93 | 99.829418 | +6.829418 | 412.5 | 410.150837 | 600次计数耗尽 |
| H04 | 117 | 118.846824 | +1.846824 | 462.5 | 461.124078 | 600次计数耗尽 |
| H05 | 147 | 154.269195 | +7.269195 | 487.5 | 487.353836 | 600次计数耗尽 |
| H06 | 177 | 200.000000 | +23.000000 | 537.5 | 540.238487 | 粒径上边界 |

独立重算 CSV 算术：Bias=+2.304914924 nm；MAE=10.676897477 nm；RMSE=13.451950895 nm；median|e|=7.049306577 nm；max|e|=23 nm。

**阈值说明**：此前 V124/方案中出现过 `max(5nm,0.1D)` 工程比较尺度。按这个尺度六例为4/6，但本次核读的 V125 交接 Markdown 与有效 JSON 并未将这个数值明确写成新的机读成功门，因此这里不把4/6冒称“严格复现 V125 冻结验收门”。这也不是四个已接受、无歧义、数值合格的测量。V126 将其作为新的显式目标登记。

发布报告把六例全部记为 ambiguous；源码实际使用 `n_basins>1`。每例安排三个起点，就自然全部“有歧义”，这不能证明存在三个等价物理解。另一方面，当前搜索和剖面也不能证明不存在多解。[R10]

主状态对 S0–S7 全部记 PASS，并声称联合测径已验证；这不受当前错误、边界、预算和失败记录支持，应改为**已评估但未建立可靠联合测径**，而不是说物理上永远无法测径。[R01]

## 4. 需要关闭的确定缺陷

### 4.1 优化目标被预算逻辑改写，多起点并未公平执行

`_objective_exact` 的600次计数由三次 Nelder–Mead共用，每个启动又请求400次。耗尽后函数返回 `1e6`，相当于把同一个物理参数的损失随调用次数改变。多个替代解确实记录了 `1e6`；`success/message` 没有保存。[R05]

修法：预算与目标函数分离。每个起点有独立预算；总预算用异常/明确状态停止，并保存最后真实计算的最佳点；不得用虚构大损失伪装未评估点。未完成的盆地不算高残差竞争解，也不算成功排除。

### 4.2 当前 D 曲线是切片，不是 nuisance 最小化剖面

实际 `d_profile` 固定最佳 h/x/y，只改变 D。正式尺寸剖面必须是：

\[
Q_p(D)=\min_{h,x,y} Q(D,h,x,y).
\]

固定 h/x/y 切片可以另存为诊断，不能作为排除其他粒径的充分证据。每个 D 上都须保留 nuisance优化是否完成、竞争盆地和边界。[R05]

### 4.3 M2 只有7个可返回粒径，不是连续共享粒径拟合

实际 M2 只遍历 `[30,50,70,100,130,160,200]`。对于生成 D55/115/185，单由候选集限制，最小可能误差就分别是5/15/15nm。发布的100μs/25μs MAE分别37/53nm，是这条受限估计链的结果，不能据此认定多帧物理信息无用。[R02][R05]

V126 必须把 D 设为同一个**连续**变量，多帧联合估计或真正剖面优化，并使用统一的平方残差/明确统计损失。不能将各帧未经加权的范数之和称作高斯最小二乘。

### 4.4 平移资格的8项SKIPPED被写成PASS；坐标调整用了留出信息

S1表中的四个非零平移与四个相机/颗粒比较均写 `SKIPPED`，却设 `passed=True`。零位移重放只验证原数组关系，不能替代非零位移精度。[R08][R11]

另 `_camx_flip` 注释明确以六个留出的一致x方向反号为修正依据。全局坐标重新标记可能有合理物理依据，并不自动等于非法逐例翻转；但**已使用留出定位和修正实现，就必须将这六例降为开发集**。[R06]

下一轮必须在旧训练D100或专用软件哨兵上独立固定坐标。统一应用于训练、观测、真值单位与输出；不能再用新留出择优方向。主库保持物理第一轴camera_x、第二轴camera_y的显式合同。

### 4.5 三种前向表示混用，`forward_exact`并非电磁精确解

`c_table` 对 C 图做D/h/xy多线性插值，`wide_fields` 对四角复场插值再求强度，正式优化使用后者。两种函数一般不相同；这个差别需要量化，不能假定是同一个目标的快慢计算。`forward_exact` 应改名为 `forward_field_interpolated`，不能称直接BEM真值。[R06]

接口还会把域外D/h/xy通过 `np.clip` 压回边界。正式公开入口应拒绝域外和非有限值；优化器本身使用合法bounds，不靠静默clip掩盖出域。[R06]

### 4.6 数值资格比较对象错误

S2源码存在四个具体问题：[R07][R12]
- 旧文件glob少了中间身份段，导致有记录的V124参考没有被实际读入表。
- D100的±1e-5折射率试验，与D30的精确匹配残差作比较，不是匹配尺度的对照。
- 所谓D30/D200的L1–L0差，实际把 **n=1.38的L1** 与 **n=nwater的L0** 相减，混入材料差别。
- `norm` 被列为RMS，且信号分母缺失。

V126先复用已经存在的场重组正确的同D、同h、同材料、同光学条件配对，再决定是否补解。不得以这些当前数值作真实网格误差或低信号地板的定量结论。

### 4.7 噪声阈值不控制误报；被检测不等于粒径可靠

冻结阈值0.0197406010取了开发空白p99=0.0340739899和目标p01=0.0054072121的中点。两分布重叠时，这会把阈值降到空白高分位之下。发布验证空白误接受21/100、含噪目标接受51/90，应保留，不能写“检测验证通过”。[R13][R02]

当前接受字段只检验delta阈值，不检验参数误差、边界、求解收敛或尺寸多解。V126分别输出 `detected` 和 `diameter_reportable`，不得混为一项。

### 4.8 曝光单位已修，但粗细路径资格未完成

1.25μs路径是真的新进展；剩余问题是：[R09][R07]
- `coarse_subsample`更换时间/位置数组却保留细网格frame_windows索引。最小复现：后续粗路径窗口出现空值或IndexError。
- S6构造粗路径却不用于光学积分比较，不能据“子采样数组相同”认定曝光结果收敛。
- 有效帧按±100μs的整帧窗口判断，而不是实际±50或±12.5μs，可能过度丢掉短曝光合法帧。
- 曝光节点等权平均包含两个端点，不是明确的梯形积分；运动参考帧遗漏了同一读噪配方。

发布表可记录为曝光方法诊断；尚不能用它确认真实的曝光-测径收益。

### 4.9 状态和回执有确定假阳性

S1存在 `PASS if ... else PASS`；S2/S3/S5/S6默认函数返回就mark PASS。归档判定为 `'PASS' in output.upper() or returncode==0`，连JSON字段名`passed`都会触发。[R07][R16]

外部回执的 `bundle_checker` 详情已经包含 **缺命令日志** 与 **预算105>64** 错误，却仍 `passed=True`。科学回执只是重放两个节点及H03返回99.83，与已发表偏差结果一致，不证明H03的真93nm被准确测得。[R14][R15]

预算记录105与报告“62独立科学节点”必须分开。源码又将cache_hit混入attempt计数，需按实际action重建真实次数；**本次不冒称已逐行独立证明105次全部是新BEM调用**。不过，以62个独立节点排除失败和重复执行不符合合同。当前预算合规未建立，原“全部PASS”必须撤回。[R01][R07][R17]

---

## 5. V126 参数和正式范围：不再向用户重复索取

| 字段 | 本批取值 | 身份 |
|---|---|---|
| 悬浮、纯水、26°C、520nm、14μm像元、50×物镜、无载玻片 | 保留 | 用户已报告 |
| 盖玻片n≈1.5、颗粒n接近水 | 保留估计等级 | 用户估计 |
| 主n颗粒=1.38+0i；n水1.3353；NA0.8；relay1 | 保留 | 条件假设 |
| 物方像元280nm；焦面450nm | 保留 | 条件推导/假设，非校准实测 |
| 训练D30–200nm；h350–550nm；xy各±500nm | 以原库实际支持为准 | 数值域，不是物理约束悬浮粒子 |
| 原17×17场、评分中央13×13 | 固定 | 不按样本选更有利mask |
| 曝光25/100μs；5000Hz；η=.870mPa·s；读噪2e | 保留 | 合成实验假设 |

径向物理边界 `h≥D/2+gap_min` 与数值库支持域分别检查。数值高度350–550nm不是反射壁；粒子出域就拒判/结束可用片段，不能反弹回模型域。

本批主观测是有符号静态/曝光图像C，不是旧400Hz的FFT幅值。旧FFT算子可保留接口，但不能把本批静态标定直接应用到FFT幅值。输出径类型为 `UNIFORM_SPHERE_OPTICAL_EQUIVALENT`；`EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false`保持。

## 6. 阶段A：先用现有场把误差来源分开（零新BEM）

### A0 接管与缓存

读取上述固定Git版本、训练/留出H5、原始render、solve缓存和配置。验证SHA、H5可读、63键集合、D/h/xy轴、材料与参考场、wide支持。保存逐文件证据而非只比较文件名。旧场经验证后复用；不重算同配置物理场。

拆分三个身份：`physics_key`（材料/几何/边界/求解依赖）、`imaging_key`（NA/焦面/采样/成像依赖）、`execution_identity`（完整本轮源码及日志）。只改保存路径或包装器，不应使相同物理解全部重算；但必须通过依赖diff证明物理代码未变。不可随意忽略真实求解改动。

使用短目录与内容寻址短文件名；开工先做小型临时MAT写入、原子rename和回读测试。路径测试不调用BEM。一次存盘失败优先抢救已在内存的解，不再次执行相同昂贵系统。

### A1 正确数值配对与坐标

从现有记录恢复每个实际case的D/h/n/mesh等，不以坏glob判缺失。至少输出D30/D100/D200在h450的同材料L0/L1；独立列精确匹配、±1e-4与±1e-5，底噪比较必须同D同h。

所有比较固定方向；global axis规范由旧训练场或独立几何哨兵决定。在旧D100宽场上检查±28、±140nm x/y及(70,-98)nm非对称位移；直接成像参考可复用同散射解，记render预算，不算新BEM。zero-shift只是一项，SKIPPED必须 `NOT_EVALUATED`。

### A2 对每个旧H01–H06做四类诊断

真值只进入单独诊断器，正式反演器仍只读匿名观测。

- `F(theta_true)`对直接L1图：量化替代模型/数值前向差。
- 同一替代模型自己生成 `Y=F(theta_true)` 后从公共初始化反演：隔离优化器错误，标 `SAME_MODEL_CLOSURE`，不是独立物理验证。
- 固定真h/xy只拟合D，以及固定真xy拟合D/h：仅作误差归因的oracle诊断，不混进正式性能。
- 全未知D/h/xy反演：保存真参数损失与返回损失。返回损失高于已知合法点说明优化未找好；返回损失更低而D有偏，才进一步分析前向偏差补偿/多解。

比较三种当前表示在**同一参数**下的输出：原C表、场级插值、节点直接场；`C_table`与`forward_field_interpolated`的差必须记录。任何真值引导的单case结果都独立列栏，不能称正式改善。

输出：`diagnostics/error_separation.csv`、`diagnostics/objective_at_true_vs_returned.csv`、`qualification/corrected_pairwise_numerics.csv`、`qualification/axis_and_nonzero_shift.csv`。

## 7. 阶段B：统一前向与最多三个插值候选

所有正式估计器、噪声评价和运动生成调用同一个 `canonical_forward`；允许独立更精细生成器作为真值，但必须标签清楚。

候选预先限制为：

- **I0**：原有C图多线性插值，只作继承基线。
- **I1**：复场D/h双线性插值，散射场按正确xy移位，参考场固定在相机网格，再算强度及像元平均。
- **I2**：确定性尺度化复场插值。先定义 `s(D)=(D/100nm)^3`，插值 `Es/s(D)` 的实部与虚部，再乘回s(D)；D/h方向采用有界域内的三次插值候选。参考场单独保持物理来源。

I2是**预设数值基底变换**，不是把30–200nm物理曲线强制设成D³，也不是增加每颗粒自由幅度。节点必须精确回到原场；域外拒绝；边缘过冲和相位变化必须验证。只有原成像代码支持明确的传播因子时才允许物理相位去嵌入，不能猜一个`exp(2ikh)`对所有角度套用。

候选选择仅用训练留行/留D诊断及旧开发H01–H06；留节点不是新物理验证。预定排名：先满足节点复现/域安全/坐标与位移资格，再按开发最大图像偏差、最大D偏差、总体误差和计算量依次选择；不按新留出选择。最多三个候选，避免无边界试模型。

如使用双/三线性近似表加速，它只允许初始化；最终损失与阈值用统一前向。若想把近似表用于最终大量噪声拟合，须先在训练域外点的开发集合给出误差资格，并把它正式冻结为唯一统计模型，不能无说明混用。

**何时补一个新高度行**：原训练内部7个高度依次留一行。对每个内部行j，计算 `e_j=max_D ||F_without_row_j(D,h_j)-C_node(D,h_j)||_2 / max_h||C_node(D,h)||_2`，均用固定13×13；分母为零或非有限时，该D先标无资格，不用随意小数补齐。每个原高度间隔的分数取两端可用e_j的最大值（边界间隔只有一个可用端点）；选分数最大间隔，并列选较小高度。尺寸敏感性另外报告，不改变这个选点规则。新h为该间隔中点，七个既有D均计算，新增最多7系统。选点只用旧训练/旧开发；规则及选中h写`augmentation_freeze.json`后才开新留出。若无需补点，不为用完预算而新增。禁止只加零散点却仍假装是无缺口矩形插值网格。

如果场类型/量纲/坐标根本错误使旧63节点不可继承，16次预算不足以重建全库：只能做有界物理定位和保存原诊断，联合全域验收阻断。不能默默扩大系统配额。

## 8. 阶段C：连续优化、真实尺寸剖面与多帧共享D

### C1 单帧主估计器

使用残差向量的有界最小二乘，主选 `scipy.optimize.least_squares(method='trf', loss='linear')`；显式 `x_scale=[50,50,140,140]`，bounds与实际库一致。已有SciPy1.11.4可用这些参数，不强制升级库，也不使用它不支持的新callback参数。TRF是局部算法，不保证全局最优，所以保留多盆地。

先在所有训练D/h与固定xy候选上搜索，选最多6个互相分离的起点。每起点最多800次残差评估；数值差分的实际forward调用另计，单case正式求解上限12000次canonical forward调用，剖面另账。每个起点各自计数，停止后保存真实最佳点与 `success,status,message,optimality,nfev,njev,budget_exhausted`。不返回虚构1e6；不根据真值缩边界或初始化。

干净图采用 `r=F(theta)-Y`，比较平方和。权重/评分mask在开发阶段冻结，所有候选相同。至少两种非真值初始化给出一致最优盆地才可声明优化稳定；不稳定则输出 `OPTIMIZATION_UNRESOLVED`。

### C2 真正的D剖面

预扫描 `D=30:2:200`；每个D上重新最小化h/xy，最多4个nuisance起点（来自至少两个h盆地及邻D暖启动），每起点最多100次残差评估。单case完整剖面上限200000次canonical调用；若达预算，未完成的D位置写未评估，不补大数。保留全部已实际评估值。

先用缓存/向量化减开销，不能在目标回调调用BEM或新render。所有近最小盆地、两端边界和平台都要纳入；固定hxy切片另存，不替代剖面。尺寸细化可以到0.25nm的数值搜索间距，但**间距不等于物理分辨率**。

清洁诊断默认采用可直接计算的经验兼容阈值：在选定插值器和固定13×13评分区下，令 `epsilon_dev=max_i ||F(theta_i)-Y_direct,i||_2`，i仅取旧开发物理图与训练留节点诊断，绝不取J01–J06。冻结 `Q_cut=(sqrt(Q_min)+epsilon_dev)^2`，保存 `{D: Q_p(D)<=Q_cut}` 的全部连通区间。这个最大值只覆盖已测开发集合，**不是连续域严格上界，更不是95%置信区间**。没有可审查的epsilon_dev，兼容范围只作未经校准的残差剖面，不输出已认证唯一D。

含噪版本按每档开发目标计算 `Delta_i=Q(theta_true,i)-Q_best,i`，冻结其经验95%分位数作为该档 `Q_min+Delta_dev` 的兼容阈值。明显负Delta说明优化未完成，必须保留失败并修复/标不可校准，不能截零掩盖；仅容许预注册浮点容差内的负零修正。这个有限开发分位阈值仍是经验pilot范围，**不称已验证95%覆盖区间**。新留出只评估覆盖与宽度，不调阈值。

近最优区间触及D/h/xy支持边界要标域受限。存在分离的可行D区间，或兼容D总跨度大于 `2*max(5nm,0.1*Dhat)` 时，`diameter_identifiable=false`，只返回范围/拒判。尺寸位于原区间但对应另一高度盆地，也须保留。不能用起点数量、全候选平均或最高峰高度代替这些判据。

### C3 多帧连续共享D

参数为一个连续D和每帧h/x/y，共 `1+3K` 个变量；残差按帧拼接，不能每帧独立D再简单平均，也不能只在7个D节点选类。使用稀疏Jacobian结构/交替剖面或TRF，至少3个共享D起点，各最多1000次残差评估；记录全局实际forward开销，单轨迹最多100000次canonical调用。耗尽则清楚标记，不伪装高残差正常解。

多帧平方残差/GLS与单帧同一统计定义。图像共同参考帧造成的跨帧相关性按第10节处理。主方法不使用生成用真D、真实h/xy、Dh或真实轨迹作为先验；oracle结果只另列上限诊断。

若有限曝光图由运动产生，而逆模型仍使用帧中心瞬时模板，必须标 `INSTANTANEOUS_TEMPLATE_UNDER_BLUR`；这可以量化模糊偏差，但不能称实现了精确运动补偿。仅当利用观测图像估计的速度/轨迹构造曝光预测并独立验证后，才升级曝光感知逆模型，不能把真轨迹直接给反演器。

## 9. 阶段D：新物理配额与六个真正新的留出

V125的H01–H06已经用于修正坐标和分析误差，V126是开发诊断集。新留出只在模型、坐标、插值器、统计方法、搜索及门槛冻结后生成/打开。

| 新case | D/nm | h/nm | x/nm | y/nm |
|---|---:|---:|---:|---:|
| J01 | 43 | 368.75 | +70 | -98 |
| J02 | 67 | 393.75 | -98 | +42 |
| J03 | 89 | 418.75 | +98 | +70 |
| J04 | 123 | 468.75 | -42 | -98 |
| J05 | 153 | 493.75 | +126 | -42 |
| J06 | 183 | 531.25 | -70 | +98 |

这些D不属于V124/V125已经打开的训练与留出D集合；h不属于原25nm网格，也不等于拟加的12.5nm中点行。使用直接L1/1444分层求解，同一解保存居中、已知非零偏移和宽场；正式观测只有匿名case、图像、公共配置，真值只在validator文件中。

若新实现问题在打开J01–J06后暴露，修复可以继续，但该批必须降级为开发，不得换噪声种子重称独立验证。剩余预算不允许新增一整轮“更好看的”真值。

**新V126工程目标，明确不是追回V125门限**：六个模型内清洁估计每例 `abs(Dhat-Dtrue) <= max(5nm,0.1Dtrue)`；同时要通过前向资格、优化完成、无未解决竞争尺寸、无不合法边界输出。满足误差但有歧义不自动成为可报告测量。目标失败也是必须保留的科研结果，不删除。

物理资格诊断配额最多3个系统，优先补确实缺失的同参数配对；不重新求已经有效的7个V125资格样例。新系统总池：`资格≤3 + 一整高度行≤7 + 新留出6 = 16`。代码修复导致缓存缺失或失败重试从同池扣，不额外开“基础设施池”。优先保留足够预算给新独立留出；没有足额时如实PARTIAL。

## 10. 阶段E：检测、粒径质量与噪声必须分开

### E1 主统计目标

模拟在电子域生成：`Y~Poisson(B*(1+C))+Normal(0,sigma_read)`；8张空白各有Poisson与同样读噪。Poisson均值必须物理非负且有限，模型负均值是错误而非clip后继续；相机读噪后的Y允许为负。

主拟合使用固定的近似GLS权重，不在优化中偷偷改变权重而忽略归一项。一个可直接落实的低对比度近似为：

\[
\widehat V_p=\widehat B_p+\sigma_r^2+(\widehat B_p+\sigma_r^2)/K_b.
\]

它是C≈0的固定方差近似，不宣称精确Poisson–Gaussian似然；后续阈值在同一实际算法上校准。如果实现参数依赖方差的高斯似然，应同时包含 `r^2/V + log V`，并冻结为另一明确模型，不能只把分母放大来降低损失。

多帧共用8张参考时，不能认为背景误差独立。主固定GLS近似每像元的K×K协方差：对角为前景Poisson+读噪，加公共参考方差的rank-one项。精确一阶因子是 `(1+C_t)(1+C_s)`；主低对比度近似可固定为1并标出近似。每轨迹/曝光一组参考，不能重复假装每帧新增独立空白。

### E2 阈值冻结与新的误报目标

采用 `T=Q_null-Q_best`，保留负值。每个背景档分别用80次独立开发空白确定阈值，主规则为该档开发空白统计量的最大值，正式判断 `T>threshold`。目标开发样本用于报告检出能力，**不用于把空白阈值降低到弱目标分位数**。

然后每档独立60次验证空白，只评估，不调阈值。新增工程目标为该档误报率的**单侧95%二项上界≤5%**。60次全零时上界约4.87%；出现误报可能无法通过，必须如实报告。三档结果分别报告，不把一档合格推广到全部光子数或真实设备。没有足够验证次数只能叫pilot。

尺寸质量门与检测门分开：
`detected → fit_converged → model_qualified → in_domain → diameter_identifiable → diameter_reportable`。

未收敛、边界依赖、多解或模型不适用，即便检测到信号，也只输出候选范围/拒判，不报唯一有效D。已知单颗粒ROI测径与全图检测属于不同对象；本批空白为单ROI分布，不声称全视场误报率。

### E3 预注册数量与数据保存

- 16个开发条件：D=[50,100,160,200]、h=[375,425,475,525]；3背景档、每档2重复，**96目标测量**，各1前景+8参考=864曝光。
- 开发空白：3档×80次×9=2160曝光。
- 验证空白：3档×60次×9=1620曝光。
- J01–J06含噪：6×3档×5次×9=810曝光。
- 多帧：12轨迹×2曝光×(8目标+8共同参考)=384曝光。
- **名义总数5838，统一上限6000，余量162。** 域外轨迹减少实际数，绝不补抽有利路径。

背景档 `[1e3,1e4,1e5] e-/pixel` 均指100μs假设；25μs固定光通量下为其1/4。轨迹主档为100μs时1e4（25μs时2500）。2500e没有独立单ROI空白验证时，轨迹使用已选择目标的条件测径诊断，不给该档检测FPR保证。

所有原始前景、参考、噪声种子、条件、成功/失败和拟合状态保存。噪声样本不只留CSV。不同估计器复用同一观测；统计主报所有尝试及接受子集，不能只取幸存粒子的平均误差。5重复是有限敏感性研究，不足以给每条件可靠95%单颗粒区间覆盖率。

## 11. 阶段F：修正曝光和运动试验，保持目标是单颗粒测径

1. 细路径1.25μs，粗路径2.5μs为同一实现的严格子采样。每条路径按自己的时间数组、实际曝光T重新计算窗口，不能沿用原索引。
2. 帧有效性按该T的真实 `[t_j-T/2,t_j+T/2]` 全窗计算，不用200μs整帧判断；两曝光对照另外报告共同合法帧与各自合法帧。
3. 插值到窗口端点后采用梯形积分或有明确权重的求积，权重和为1；先算强度再时间平均；保存节点、权重、细/粗曝光图与C差。
4. 生成12轨迹，每D=55/115/185四条、各8帧；这三个D属于共享库生成的开发运动测试，不是新电磁盲测。明确 `SYNTHETIC_Dh_EQUALS_D_ASSUMPTION`。
5. 支持域超出就标记、不得clip。多帧主结果要求至少4个有效帧；不足者记insufficient_frames。保留有效长度分布，不把未入选路径从分母删除。
6. 不从真轨迹取精确中心后称实验定位；图像反演估位置。oracle对中仅作为另列上限。
7. 优先完成无噪声同路径的25/100μs比较，再加入固定光通量的计数噪声。曝光短信号少和模糊减轻分开解释。
8. 细/粗光学积分实际对照至少3个D各1轨迹。推荐目标：固定有效帧的C相对L2差≤0.5%，另报绝对差；近零分母不比较相对差。未达标可细化已有同一路径/连续表示，但不能重新抽路径凑过关；实际生成相机噪声重算要扣预算。

多帧D必须连续并保存D剖面。若运动图由训练替代模型生成，所有多帧结果标 `SHARED_SURROGATE_METHOD_DIAGNOSTIC`。模型内表现改善也不能升级成新的独立BEM验证或真实实验精度。

## 12. 合同执行、预算和严格停止条件

| 项目 | 上限 | 实际计数 |
|---|---:|---|
| 新BEM系统调用 | 16 | 启动前原子预留，失败、存盘失败后的重解都计；纯缓存读取不计 |
| 新render | 128 | 新偏移、NA/焦面/积分设置每项计；batch按内部实际次数 |
| 合成相机曝光 | 6000 | 前景/参考/空白均计，每个独立随机曝光有ID；复用观测不重复 |
| 重物理并发 | 1 | 绝不新开第二批重复系统 |
| 计算时间窗 | 12小时 | 预留最后30分钟收尾，不承诺固定完成时间 |

新render的可行预留上界：旧63节点重新成像最多63、增高行7×2=14、新留出6×3=18、资格3×2=6、坐标/平移/积分对照16，总117，余11。实际旧场可直接用就不重render。这个表不是授权把所有项都重跑；选用步骤从同池扣。

原V125的预算先按`solve_start/solve_finish/cache_read/render`等真实action重计。105为发布口径，不能不核对就把cachehit当新solve，也不能以唯一case计数隐去重复求解。新V126不继承原余量、不重新定义“科学池之外免费”的计算。

一个库节点完成、一个测试变绿、一次归档成功都不是整批结束。只有全部已放行任务完成，或达到时间/资源边界，或关键物理问题阻断依赖分支，才能正常收尾。所有受阻状态注明原因、证据及影响范围；相关数据仍保留。不得删除坏例、换真值、扩大范围后不改任务身份。

## 13. Codex 必须实现并运行的入口

以下是待落实入口，不是本交接包已经提供的完整科学代码：

```text
config/v126_science_config.json
 tools/v126_run_all.py
 tools/v126_intake_and_budget.py
 tools/v126_corrected_qualification.py
 tools/v126_forward_model.py
 tools/v126_error_separation.py
 tools/v126_invert_particle.py
 tools/v126_profile_and_ambiguity.py
 tools/v126_camera_and_thresholds.py
 tools/v126_exposure.py
 tools/v126_validate_science.py
 tools/v126_archive_check.py
 source/v126_physical_forward_adapter.m
```

物理适配器最小改动复用现有NANOBEM；旧V125文件原样保留，不原地覆写失败历史。所有公共入口接收真实 `--repo --config --out`；缓存完整性、dtype、finite、单位与domain是显式检查。数据表不能用文件存在就自动PASS。

建议执行命令（实现后由Codex运行）：

```powershell
python tools/v126_run_all.py --repo . --config config/v126_science_config.json --out results/v126 --resume
python tools/v126_validate_science.py --repo . --out results/v126 --strict
python tools/v126_archive_check.py --zip results/v126/iscat_v126_return.zip --receipt results/v126_external_receipt.json
```

本包自带的只读审查自检可先运行：

```powershell
python tools/reproduce_v125_review_checks.py --out evidence/review_recomputations_replayed.json
```

该命令不建立粒径标定，不代替上面的实际科学入口。V126主动记录JSON数值不可含NaN；未评估写null和原因，不以0补齐。

## 14. 必须返回的科学数据、状态与一份ZIP

```text
iscat_v126_return.zip
  00_README.md
  01_V126_执行合同.md
  status.json
  review.md
  config/effective_config.json
  config/model_freeze.json
  config/threshold_freeze.json
  source/                         # 实际执行文件、物理依赖、diff和身份
  library/                        # 完整最终训练C/Ibg及可重放的复场或等价系数
  validation/new_holdout_images.h5
  validation/new_holdout_truth_validator_only.json
  validation/holdout_per_particle.csv
  validation/diameter_profiles/    # 真正min_hxy剖面及每点优化状态
  validation/noise_per_trial.csv
  validation/blank_per_trial.csv
  validation/motion_per_track.csv
  validation/raw_camera_data.h5
  validation/trajectories_and_exposure.h5
  diagnostics/error_separation.csv
  diagnostics/interpolator_comparison.csv
  qualification/corrected_pairwise_numerics.csv
  qualification/axis_and_nonzero_shift.csv
  qualification/positive_and_negative_tests.json
  figures/                        # 曲线、图样、误差、多解、ROC/接受率，轴单位齐全
  logs/actual_commands_and_errors.txt
  logs/event_ledger.jsonl
  logs/cache_identity.csv
  logs/resource_budget.csv
  manifest_sha256.csv
```

未执行分支不造空表假装完成；status与README写明NOT_EVALUATED/BLOCKED及科学范围。大solve文件无法放ZIP时，完整索引列路径、SHA、大小和依赖，关键可重放场仍须进入ZIP；不要只有PNG。

机械验收要求：CRC、唯一安全成员、manifest完整覆盖、必需成员、每成员SHA、当轮源码与状态身份；独立检查器从**ZIP解包后的源码/数据**至少重放1个新训练/补点场强到C和1个新留出推断。科学检查与机械检查分开；重现相同错误估计只叫replay一致，不叫尺寸准确。

必须用结构化JSON verdict+exit code+errors空集判定；`'PASS' in output`严格禁止。检查器返回非零时外层不能用输出中某个`passed`字段洗绿。PACKAGING在最终状态写入后执行，ZIP外收据记录ZIP SHA；不要求ZIP内部自包含自身最终SHA造成循环。

科学状态最少包含：

```text
execution: COMPLETE / PARTIAL / FAILED / BLOCKED
forward_qualification: CONDITIONAL / PASS_WITHIN_LISTED_SCOPE / FAIL / NOT_EVALUATED
original_exact_match_gate: FAIL / 原门真实重新通过（必须附同门证据）
optimizer_closure: PASS / FAIL / INDETERMINATE
independent_holdout_evaluation: COMPLETED / NOT_EVALUATED
independent_holdout_accuracy_goal: PASS / FAIL / INDETERMINATE
blank_false_acceptance_by_background: 各档独立结果
single_particle_D_reportable: 逐例布尔 + reason
budget_compliance: PASS / FAIL
archive_integrity: PASS / FAIL
EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED: false
```

有数值结果但误差目标失败，是“研究已执行、性能未通过”；不能将它改成执行失败后删除，也不能称全部验证通过。单颗粒输出包含candidate_D、reportable_D（不可报告则null）、h/xy、剖面兼容集合、模型身份、误差和拒判原因，避免用户误把候选数当测量值。

## 15. 新方法与论文方向（有结果后再决定主张）

本轮可研究两项现实的方法贡献，而不更换实验装置：

1. **误差可分解的悬浮粒径反演**：区分优化不充分、D/h插值偏差和真正的图样退化；给出何时输出唯一D、何时输出范围、何时拒判的证据链。
2. **连续多帧共享D与曝光失配诊断**：在统一物理观测模型上检验多帧是否减少尺寸—高度混淆；与单帧和瞬时模板作公平对照，不使用真轨迹偷渡信息。

尺度化复场插值仅是候选数值方法，须以新直接留出证明是否有效；不能预先写成论文已达成创新，也不能称首次。已有矢量iPSF研究证明空间图样可包含轴向信息，但不自动给本装置和本粒径范围背书。

## 16. 一句话执行指令

> 固定V125提交，保留63节点与六份直接场，撤回不受证据支持的全PASS。先零新BEM修复预算/回执/比较对象，分离优化器与前向插值误差，统一前向并真正实现连续D和剖面。只有需要时补一个七粒径高度行，冻结后做六个新L1 D/h/xy留出，同批完成独立空白、含噪单颗粒和正确曝光多帧诊断。在16系统/128render/6000相机曝光/12小时统一预算内连续推进；不在一个小修复处结束，不用历史统计冒充新实验，不要求用户现在补参数。最后一次交付完整原数值、逐例粒径/拒判和可验ZIP。

## 17. 固定来源索引与参考方法

以下R编号对应本次直接读取的V125源码/报告。源文件说明与本审查推论不同处，正文已经明确指出；不把文档里的PASS直接当事实。

- [R01] [results/v125/status.json](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/status.json)
- [R02] [results/v125/review.md](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/review.md)
- [R03] [results/v125/library/train_grid_index.csv](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/library/train_grid_index.csv)
- [R04] [results/v125/validation/inversion_holdout_joint.csv](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/validation/inversion_holdout_joint.csv)
- [R05] [tools/v125_invert_particle.py](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/tools/v125_invert_particle.py)
- [R06] [tools/v125_model_library.py](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/tools/v125_model_library.py)
- [R07] [tools/v125_run_all.py](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/tools/v125_run_all.py)
- [R08] [tools/v125_forward_shift.py](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/tools/v125_forward_shift.py)
- [R09] [tools/v125_exposure.py](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/tools/v125_exposure.py)
- [R10] [tools/v125_review.py](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/tools/v125_review.py)
- [R11] [results/v125/validation/s1_regression.csv](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/validation/s1_regression.csv)
- [R12] [results/v125/validation/numerical_qualification.csv](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/validation/numerical_qualification.csv)
- [R13] [results/v125/validation/threshold_freeze.json](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/validation/threshold_freeze.json)
- [R14] [results/v125_external_receipt.json](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125_external_receipt.json)
- [R15] [results/v125_science_validation.json](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125_science_validation.json)
- [R16] [tools/v125_archive_check.py](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/tools/v125_archive_check.py)
- [R17] [results/v125/logs/v125_matlab_ledger.csv](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/logs/v125_matlab_ledger.csv)
- [R18] [results/v125/logs/source_identity.json](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/logs/source_identity.json)
- [R19] [results/v125/config_effective.json](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/config_effective.json)
- [R20] [tools/v125_mie_fixed.py](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/tools/v125_mie_fixed.py)
- [R21] [results/v125/validation/holdout_gate_summary.json](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/validation/holdout_gate_summary.json)
- [R22] [results/v125/validation/noise_per_trial.csv](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/validation/noise_per_trial.csv)
- [R23] [results/v125/validation/blank_per_trial.csv](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/validation/blank_per_trial.csv)
- [R24] [results/v125/validation/exposure_motion_per_trial.csv](https://github.com/yyyyzoey/iscat-handoff/blob/36a231ec8319ae47906664bdc8b54c166727af5a/results/v125/validation/exposure_motion_per_trial.csv)

外部方法资料（仅支持方法选择，不替代本项目数据）：
- [SciPy least_squares（1.11系列文档）](https://docs.scipy.org/doc/scipy-1.11.3/reference/generated/scipy.optimize.least_squares.html)：带bounds的残差向量优化、TRF、变量尺度和稀疏Jacobian；它是局部优化器，非全局保证。
- [The point spread function in iSCAT. I.](https://arxiv.org/abs/2006.15332)：矢量图样和轴向位置关系。其论文装置与性能不能移植成当前材料/光路的测径精度。

**范围签注：V126尚未运行。本交接包没有新BEM结果、没有新的实验粒径；辅助复现仅验证所列CSV算术及最小代码逻辑。**
