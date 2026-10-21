# V126 独立审查与 V127 连续执行合同

**任务目标：用反射式 iSCAT 原始线性图像/背景，对悬浮的单颗粒估计粒径，而非只建立场库或得到最低拟合残差。**

- 仓库：`yyyyzoey/iscat-handoff`。
- 本次审查固定：`v126@b546d80beb0dc4789effac8c192896e5f45876e9`。
- 下一批：`V127_CANONICAL_CALIBRATION_ACCEPTANCE_AND_SUSPENDED_PARTICLE_SIZING`。
- 文件性质：V126 源码/发布记录审查 + 尚待 Codex 执行的 V127 合同。
- 参数与工况唯一机器来源：`config/v127_science_config.json`。本合同的下一轮数字均由该配置校验；不能在脚本里再手写一套真值。
- **明确启动授权：现在执行。** 不必再次询问是否启动；用户已经允许未知参数采用明确假设。局部受阻则保留证据并继续无依赖部分。

## 0. 结论、证据范围与本轮完成目标

**V126 审查状态：`PARTIAL_ACCEPTED_MAJOR_IMPLEMENTATION_AND_VALIDATION_REPAIR_REQUIRED`。** 保留旧场、六份新增直接物理响应和已改善的数值配对。撤回“联合测径已全面验证”“多帧已经连续优化”“所有曝光窗均支持域内”“全部阶段 PASS”的笼统结论。

本次真正完成：固定 Git 引用；阅读源码、合同、逐例表和回执；对六例表做独立算术；复核收到合同的 Git blob 身份；进行小型源码等价/解析反例。**本次没有下载展开远端 HDF5/MAT/原结果 ZIP，没有重算 BEM，没有完整重跑原光学反演。** 程序访问公共原文件的下载路径未能在本审查环境成功，因此“场库有多少节点”“某原场重放通过”等，除特别说明外限于发布清单/报告支持。

本地上一轮合同 42267 字节，Git blob SHA1 `f7a47b0c3b607e2fd814185dbaf09fccc87221fb`，与 V126 发布的 `results/v126/contract/01_V126_执行合同.md` 相同。故以下合同差异不是因收到另一份任务造成。[R21]

V127 不再无条件增加63个BEM，不再一上来跑几千含噪拟合。顺序固定：

`旧场复用与机器合同检查 → 单模型反演闭合和剖面一致性 → 统一/比较真实实现的插值器 → 需要时最多补一整行 → 冻结全部定义 → 六个新K直接物理留出 → 统计质量/正确曝光/连续共享D → 原始数据与验收一次交付`。

**不得在一个修复、一张图或中央样例后正常停止。不得用文件存在、进程退出或重现相同偏差估计代替测径成功。**

---

## 1. V126 现有结果：保留什么，不能怎样解释

### 1.1 可以保留

1. 报告保留了V125的63节点主材料场，没有再次整库求解；增加六个直接L1条件与对应成像。[R01][R02]
2. 同D/同h/同材料配对已修正：D30主材料L0/L1相对L2差 `0.00552856239`，D200为 `0.00067401043`；D100精确折射率匹配仍属近零残差诊断。两离散级的差不是相对真实解的严格误差上界。[R13]
3. 已发布四个非零位移比较，而不是V125的SKIPPED：最大绝对C差约 `2.56e-4..3.72e-4`。这只支持已测D100/所列位移与约定；不能推广成小D或全域平移误差保证。[R14]
4. 不再用共享600次计数器直接改写单帧目标函数为虚构损失；有真实TRF调用和状态记录。这是进步，但不是全局收敛证明。[R05]
5. 每背景独立以开发空白最大值选检测阈值，方向优于上一轮的空白/目标分位数中点；保留失败背景档，不能为了全绿调验证集。[R07]

### 1.2 六例实际响应及误差

按发布真值文件而不是原计划表核算：[R03][R04]

| case | 实际D/nm | Dhat/nm | D误差/nm | 实际h/nm | hhat/nm |
|---|---:|---:|---:|---:|---:|
| J01 | 41 | 33.933223 | -7.066777 | 368.5 | 535.934437 |
| J02 | 67 | 67.481232 | +0.481232 | 402.5 | 402.639009 |
| J03 | 89 | 90.830287 | +1.830287 | 437.5 | 439.201396 |
| J04 | 123 | 126.653564 | +3.653564 | 472.5 | 472.706517 |
| J05 | 151 | 159.000917 | +8.000917 | 507.5 | 507.609278 |
| J06 | 183 | 200.000000 | +17.000000 | 542.5 | 545.909263 |

对这六行独立算术：Bias `+3.9832038655 nm`；MAE `6.3387962540 nm`；RMSE `8.3654455192 nm`；median|e| `5.3601706874 nm`；max|e|约17nm。

报告中的“4/6≤8nm”是另一个摘要尺度；原合同正式尺寸目标是 `max(5nm,0.1Dtrue)`，按**实际真值**仅看误差是5/6。J06虽在10%尺度内却落在D上界，J01有大高度偏移；还须满足前向资格、稳定剖面和可辨识性，不能直接把5例叫作可信测量。

V125与V126用的样本不同，不能把MAE从10.68降到6.34直接当成同一盲测上的方法提升。

### 1.3 实际工况没有按收到的合同执行

原合同/JSON为J01 `(43,368.75,+70,-98)`，发布为`(41,368.5,+42,-98)`；J05原D153/h493.75，实际D151/h507.5。其余高度/偏移也存在差别。**以原始有效物理配置核定真实条件，不能改真值配合计划，也不能重命名旧图假装原计划已执行。** 发布参数仍可作为诊断物理计算，但预注册一致性未建立；J01–J06之后全部归为开发诊断集。[R04][R21]

---

## 2. V126 需要修复的具体问题及证据

### 2.1 三种“插值候选”不是合同中的公平比较

- `I0`对已经是17×17相机像元的C图，使用`(-dy/56,-dx/56)`进行平移。56nm是细采样间距；相机像元为280nm，量尺差5倍，且轴/符号没有按camera_x/camera_y资格统一。这不能代表正确图像级基线。[R06]
- `I2`实际仍为D/h四角双线性缩放场，未实现合同中预定的有界三次候选。报告不得把它称作已试验的三次模型。[R06][R21]
- `in_domain`存在但`forward()`并未调用；内部`np.clip`把域外D/h压回边界，I2还可能把域外原D用于幅值尺度。因此“都拒绝域外”不受源码支持。[R06][R12]
- 模型冻结文件写“节点误差均<1e-12”，另一资格表却记录D100宽场与标准场相差`5.431957e-7`。必须区分同数组代数重放和两种成像网格的差；本次未取得逐节点表，不能替它声称全63通过。[R12][R14]

### 2.2 优化仍有缩放、盆地和停止判据问题

当前TRF没有配置原合同要求的`x_scale`，保留默认梯度终止条件；有些干净弱信号图只用了4或5次函数调用就标success。[R03][R05]

本包最小解析反例 `r(D)=1e-8*(D-83.7)`，x0=100，合法域[30,200]：原默认gtol可在一次调用后success但返回100；固定残差缩放并使用明确gtol后得到83.7。**这证明success不足以认证准确性，不是证明某个真实光学样例的偏差已被完全归因。**[X01]

`loss_guard`回退到粗节点后保留此前优化器success/nfev/status，可能把“有一个不更差节点”包装成新最优解已收敛。回退必须标`FALLBACK_UNREFINED`，重启或仅输出候选，不能保持旧success。

### 2.3 剖面改善了形式，但还不可靠

现在每个D重新优化h/xy是进步；然而只从一个h=450起点单向延拓，没有全高度多盆地。`arange(30,200+eps,4)`实际末点198，漏掉200上边界；也没有插入联合解的D。

J06报告的剖面最小范数约0.18446，而联合拟合范数约0.00938；它们没有在同一个D对齐，这不构成直接的同点数学矛盾，但足以说明此剖面不能据此排除已知低损失边界解。必须在同D加入所有已评估合法见证点，返回值不许比它们更差。[R03][R05]

旧H闭合也没有普遍恢复真值：I1 H01同模型返回49.9847而真D37，H05返回54.2623而真D147。可能涉及优化或模型退化，须分离；不能从一份success表直接认定“5/6闭合已通过”。[R10]

### 2.4 M2仍不是连续D优化，统计目标也未统一

`fit_shared_D`先选7个D节点，再在一个胜出节点±12nm范围按2nm步长扫描。局部区间可能漏掉别的合法尺寸；它返回网格值，不是连续共享D优化。每帧范数直接相加，也不是拼接GLS残差的平方和。[R05]

下一轮必须使用连续D变量（联合`1+3K`优化或真正连续剖面），不再只改函数注释。不得用一个局部节点附近的加密网格冒充全域连续方法。

### 2.5 “可报告粒径”仍缺少关键条件

源码注释含`identifiable`，实际布尔式只有检测、收敛、在域和非D边界，没有尺寸剖面、模型资格或h/xy边界。干净J结果甚至没有正式逐例reportable字段。所述28/90可报告、MAE约26.5nm，不能视为完成合同的可靠粒径判定。[R07][R02]

二项单侧95%上界在k>0时应为`Beta.ppf(.95,k+1,n-k)`；当前写成`n-k+1`。3/60的正确上界约12.4187%，不是12.2231%；结论仍是不满足≤5%目标。0/60上界4.87029%不变；k=n须单列1。[R07]

### 2.6 曝光支持域没有真正守住，且未保存重放所需数组

代码已经按细/粗各自时间数组和25/100μs实际窗口取样，这是修复；但窗口函数只检查节点落在窗内，没有保证两端覆盖，也未真正插入非对齐端点。对目前对齐步长的窗口可能正确，对一般输入不成立。

更严重的是，曝光入口未调用`in_domain`，模型内部clip了高度。按公开默认生成器/种子做源码等价路径复现，192个曝光窗有40个曾超出h=[350,550]；发布表却把192帧都记为valid。此复现针对公开默认生成器，不是重放已保存轨迹（本次没有取得原轨迹数组）。必须重新定位实际路径，再判支持域。[R08][R22]

5/9细粗比较达到0.5%，最大相对差5.2565%是发布表的真实失败，不得以阶段执行完成代替数值通过。[R15]

源码每帧生成8张独立参考，而合同要求每条轨迹/每个曝光共用8张参考。原始Y/参考/路径/权重没有在该入口落盘；发布validation清单也未提供合同要求的`raw_camera_data.h5`和`trajectories_and_exposure.h5`。不能把192行无噪声峰值摘要称为192幅原图已归档。

### 2.7 预算、状态和回执仍未闭合

- E模块一次完整执行按源码为`(96+240+180+90)*9=5454`曝光，不是5958。
- F模块若处理发布的192个有效帧，当前每帧1目标+8参考，应为1728曝光，E+F为7182；资源CSV却记录5670且备注更小于其自称的E5958。这是源码/表/摘要之间的确定冲突，**不是本次远程进程审计确认实际总共恰好7182次**，须重建真实逐事件账本。[R07][R08][R16]
- BEM首批在reserve机制之前执行已有记录；`reserve`的读JSON再写JSON不具备并发原子性，且E/F没有调用它。以后预算应在真实派发入口强制预留。[R17]
- 状态仍把性能未通过的E/F写PASS；回执主要检查字节与重复同一估计，不检查合同参数、性能目标和缺失原数组。机械完整性与测径科学结论必须分开。[R01][R19][R20]

---

## 3. V127 的科学范围与唯一输入

当前用户已确认：悬浮、纯水、26°C、520nm、14μm×14μm相机像元、50×物镜、无载玻片。

盖玻片n≈1.5、颗粒折射率接近水仍是用户估计。主假设继续为n颗粒1.38+0i、n水1.3353、NA0.8、附加倍率1、物方像元280nm、焦面450nm、玻璃侧正入射线偏振、玻璃水界面参考；读噪2电子、η0.870mPa·s、曝光25/100μs均是条件假设。

- 正式量为**空间有符号线性强度对比度**，不是旧400Hz FFT幅值。
- 本轮不自由拟合每粒子的光学增益、散射幅度或相位，不把材料n和D同时任意放开。
- D与水动力学直径相等只作运动生成假设，不能把生成用D、真实轨迹或扩散率传给正式反演。
- `EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false`保持；核直径、包覆外径和光学等效直径不能混称。
- 数值h范围[350,550]不是反射壁；出域应拒判/缩短有效片段，不在边界弹回。

## 4. P0：开工后首先建立能真正失败的检查（不新解BEM）

1. 读取固定提交、63节点H5、旧H/J直接图、配置、MAT与源依赖；记录完整SHA256、bytes和实际路径。旧合同、旧坏例不覆盖。
2. 本包`contract_core.py`仅提供已测试通用域、窗口、CP上界、参数网格和报数规则，**不是电磁模型**。运行其单元测试，再把同类行为测试绑定到项目真实入口，禁止只跑复制的假函数。
3. 强制断言：配置的物方像元=1000×14/(50×1)=280nm；细网格=280/5=56nm；图像级位移使用280；字段级查询使用真实坐标向量，不混轴。
4. 对每一个公开forward检查NaN/Inf、D/h/xy边界、物理gap；域外抛出结构化`OutOfDomain`，禁止clip、零填充或沿边界延拓。测试必须涵盖`h=600`、`D=201`、xy超域以及部分曝光窗口出域。
5. 三个明确通过条件：同数组复场→强度→C重放；非零平移与直接成像参考的误差表；优化器报告携带完整退出状态。SKIPPED只能NOT_EVALUATED。
6. 旧预算复核与新预算隔离。使用SQLite事务或等价原子锁：预留→启动→成功/失败；成功前存盘失败也消耗一次真实求解。缓存读取独立action，不算新solve；失败重试必须新attempt ID；不得重置计数覆盖历史。
7. 更改保存路径/包装器只改execution身份，不无条件失效物理缓存；更改求解依赖则依法失效。所有旧缓存复用都写理由。

**返回P0**：`validation/contract_conformance.json`、`logs/cache_identity.csv`、`logs/source_identity.json`、`logs/event_ledger.jsonl`、旧结果错误清单。真实入口反例尚未通过时，暂停依赖的新物理和新盲测，仍继续已有数组审查。

## 5. P1：先把旧图真正拟合明白，不以新BEM掩盖优化问题

### 5.1 正式前向契约

`canonical_forward(theta, model_id, config)`，theta=(D,h,x,y)，输出`Ibg,I,C,valid,reason`或结构化异常。首轴camera_x，次轴camera_y，第三轴偏振分量；保持全局固定约定。

对各像元：

\[
I_p=\langle \sum_\alpha|E_{r,\alpha}+E_{s,\alpha}|^2\rangle_{A_p},
\quad I_{bg,p}=\langle\sum_\alpha|E_{r,\alpha}|^2\rangle_{A_p},
\quad C_p=(I_p-I_{bg,p})/I_{bg,p}.
\]

先形成强度再像元/时间积分。参考场保持固定光学路径；只平移散射场查询。原场必须有足够缓冲，评分统一中央13×13，原17×17/宽25×25也保存。禁止每图归一到最大值，禁止自由乘粒径相关系数。

### 5.2 三个实际实现的候选（旧I0只作纠错诊断）

- F1：复场D/h双线性，保留为基线。
- F2：复场D/h张量三次插值；实部/虚部分别，not-a-knot边界，禁止域外外推。
- F3：先除`s(D)=(D/100)^3`后对散射场作同样三次插值，再乘回；参考场独立检查。它是可逆数值尺度，不是新增自由振幅，不强迫真实散射遵守D³。

每个候选在节点都应回到同一宽场计算出的C（≤1e-12）；标准17网格对宽场中部的差另记，不把不同网格的差充作代数误差。禁止任意逐节点旋转相位使图样“更平滑”；物理相位规范必须共同。

候选只用旧训练留D/留h、H/J开发诊断选择。在每个候选上使用相同且已闭合的优化器，不能把某候选的坏初始化当成前向模型劣势。比较必须含：图像误差、尺寸偏差、完整剖面、参数边界、过冲和运算开销。

不要每次forward重建RegularGridInterpolator或反复读HDF5：原数组一次读入内存，预计算样条系数/空间查询索引；复场xy双线性或相容三次要用直接成像资格约束。数值加速若改变模型，必须单独做同点误差检查。

### 5.3 单帧优化：可直接落实的方法

采用`least_squares(method='trf', loss='linear')`，显式`x_scale=[50,50,140,140]`、`gtol=1e-12,ftol=1e-12,xtol=1e-10`；工作站可保留SciPy1.11.4，不调用新版才有的callback参数。

干净图使用固定观测尺度：

\[
r=(F(\theta)-Y)/s_Y,\quad s_Y=\max(\|Y\|_2,10^{-6}).
\]

该常数不随候选theta变化，不是拟合光学增益；保存原始未缩放残差用于科学比较。零信号先检测，不把归一化放大当作“有信息”。强度包含模平方，不使用需要复解析性的complex-step导数；用显式有限差分/已验证实雅可比。

公共粗搜索覆盖所有D/h节点及配置的xy起点；选择最多6个分离盆地，保证至少两个轴向盆地，每起点独立预算。单case最多20000真实canonical调用（含数值差分），最多800残差评估/起点。目标函数对相同theta必须确定，不受调用次数改变。

结果保存`theta,Q,nfev,njev,optimality,active_mask,status,message,success,budget_exhausted`和各起点。若回退到已评估较好点，状态为`FALLBACK_UNREFINED`；必须再优化/诊断，不能继承原success。

**闭合先过再新解**：24个预定域内非节点同模型样例，且每个候选至少覆盖弱信号、小粒径、高粒径、两个h盆地、非零xy。清洁同模型目标含零残差真点；要求公共搜索最优残差≤`max(1e-12,1e-6*||Y||)`，或明确证明多个近零解后报告兼容集合。不能因找到另一个同等零残差解而硬要求唯一D；也不能仅`success=True`通过。

### 5.4 真正的全域尺寸剖面

初始D网格30:2:200，**显式包含两端、所有联合解D、模型节点**。对每个D重新优化h/xy，四起点由两个h盆地、左右延拓及联合解见证构成；至少双向延拓。每D保留所有真实见证点的最小值，优化结果不得比同D已知合法见证更差。

若剖面找到比联合解更低的损失，更新联合最优并再次细化；不让两份产物自相矛盾。近竞争区间细化到0.25nm数值间距；这不是物理分辨率。每例剖面最多300000 canonical调用，触顶则PARTIAL_PROFILE，缺失区间不补大损失。

干净经验兼容阈值：`Qcut=(sqrt(Qmin)+epsilon_dev)^2`，epsilon_dev在**同一ROI、同一未缩放残差定义**下，只由旧开发直接图/留节点诊断得到；不是全域严格误差界。含噪兼容阈值为各B开发的`Qmin+p95(Qtrue-Qbest)`；明显负值是优化失败，不能截零掩盖。

兼容D多连通分量、总跨度>`2*max(5nm,.1Dhat)`、剖面未完成、未排除边界依赖时，只能给范围/拒判。区间名称为经验兼容范围，非已经认证的95%实验置信区间。

### 5.5 真正的多帧连续共享D

优化变量为`[D,h1,x1,y1,...,hK,xK,yK]`。将各帧同一统计残差拼接后最小化平方和，或对连续D进行每次重新优化全部nuisance的连续剖面；不能只遍历离散D候选。

至少3个不同共享D公共起点，单轨迹最多150000 canonical调用；可用稀疏雅可比结构，但保存真实全部调用计数。共享背景时GLS有跨帧秩一相关项，不得假装独立。

先在低成本可辨识线性测试模型上验证非网格D=83.7能恢复至1e-3nm内，再做无噪声光学同模型短轨迹闭合。测试用真D只在生成器和验证器，不给优化器起点/边界。这项通过后才跑含噪多帧。

**返回P1**：旧H/J逐例对照、闭合结果、正确剖面、三个候选实际实现的差别和选择依据。若闭合尚未通过，不新增K数据，也不把它叫“粒子不可测”；继续定位优化/表示问题并返回PARTIAL。

## 6. P2：必要时有限补点，并冻结完整模型

先用旧训练留一D和留一h诊断；把误差分成D插值、h插值、xy采样、光学离散和优化，不用单个最终D误差推断全部原因。

默认零补点。若通过P1后，旧直接图的替代模型偏差仍主导，则在两种方案中最多选择一种：

- **补一整D行**：原D单元中点候选`[40,60,85,115,145,180]nm`；为选中D补齐9个既有高度。高D160–200问题可由180行检验，但选择必须根据下面的冻结规则，不自动指定“最有利”行。h450若有同配置V124合法场可复用；最多9新系统。
- **补一整h行**：选中原h区间中点，七个原D全部计算，最多7新系统。

冻结规则：分别在原训练内部D/h节点做留一预测，固定13×13，采用`||C_pred-C_node||/max_h||C_node(D,h)||`；零/近零分母另报绝对误差，不凭epsilon抹掉。每个间隔分数为相邻可用留一误差的最大值；按“每个新增系统可降低的最大开发误差”排序，无法合理量化时按最大归一误差选类，再按小坐标打破并列。记录全部分数和所选行，不读K。

只有计算前估计仍有预算/时间完成六K及收尾，才启动补点。补点后形成完整矩形，更新真实Ds/Hs和插值系数，不能硬编码旧63维。若新行失败且无法补齐，旧库仍可作为受限基线，新增不完整行不强行矩形插值。

额外数值资格新系统最多1；主预算为`资格≤1 + 补行≤9 + K6 =16`。已有资格场必须先复用。

随后生成`model_freeze.json`，含实际训练库SHA、源码SHA、真实物理/成像配置、插值器、优化器、参数尺度、残差定义、剖面规则和坐标；任何改动使freeze失效。**冻结时间要早于生成/打开K观测。**

## 7. P3：六个全新K直接L1物理验证（不可擅改）

| case | D/nm | h/nm | x/nm | y/nm |
|---|---:|---:|---:|---:|
| K01 | 47 | 381.25 | +84 | -56 |
| K02 | 73 | 406.25 | -98 | +70 |
| K03 | 107 | 431.25 | +56 | +112 |
| K04 | 137 | 456.25 | -70 | -98 |
| K05 | 163 | 481.25 | +112 | -70 |
| K06 | 193 | 518.75 | -84 | +98 |

由唯一JSON自动生成MATLAB任务、匿名H5和独立验证真值，生成前检查与所有已用D集合不重合、h非训练及拟补节点、gap合法。每个D/h独立L1/1444求解，保存居中、偏移和宽场；不把六个都先跑完再宣布模型冻结。

同一场可重复成像，不能从训练替代模型生成所谓直接真值。真实生成参数由原始s.cfg/几何读回，和任务JSON逐字段断言相同；如果不符，样本INVALID_CASE而不是改真值标签修复。

正式反演只读匿名图和公共仪器信息。六例全报`candidate_D/reportable_D/h/xy`、收敛、完整剖面、数值范围和拒判。粒径误差目标`max(5nm,.1Dtrue)`与前向/可辨识性门分别报告；误差达标不自动可报告。实验绝对直径仍未验证。

若打开K后发现实现错误，可修复继续分析，但K降级为开发，不能同一轮另换随机种子重新称盲测。受剩余资源约束，不临时再开第二套“更漂亮”留出。

## 8. P4：噪声、检测与测径可报告性必须真正分开

### 8.1 同一相机模型

前景`Y~Poisson(Bp*(1+C))+N(0,σr²)`；每张参考也有Poisson+相同读噪。Bp为实际参考场相对分布乘固定假定光通量，不能给每粒子调增益。物理均值若负或非有限，抛错；读噪后的Y可负。

单帧使用冻结的低对比度GLS近似：
\[
V_p=(\widehat B_p+\sigma_r^2)(1+1/K_b).
\]
它不是精确Poisson–Gaussian似然，需按同一算法校准。若使用参数依赖方差的似然，必须同时保留log项并另外冻结，不靠扩大方差降低损失。

同一轨迹/同一曝光共用8参考：每像元K帧协方差的低对比度近似为`(B+σ²)I + (B+σ²)/8 * 11^T`；用Cholesky或等价白化。精确一阶背景项包含`(1+C_t)(1+C_s)`，本轮可保留固定近似并明确适用范围。25/100μs各用一组参考，不跨曝光偷用。

### 8.2 阈值和质量门

每B使用80开发空白，`T=Q_null-Q_best`，阈值为该档开发最大T，正式`T>threshold`；不能看验证空白结果提高阈值后仍叫原独立验证。每B60验证空白，正确Clopper–Pearson单侧95%上界≤5%为工程目标；k=0时4.8703%，k=3时12.4187%，k=n时1。有限n导致未达目标时报告统计证据不足/失败，不能反复补抽直到零误报。

分别写`detected,fit_converged,model_qualified,in_domain,profile_complete,diameter_identifiable,boundary_unresolved,diameter_reportable`。只有全部必要条件成立才赋reportable_D，否则null＋原因。检测到且不在D边界远远不够。

干净图/已知目标ROI不强制用一个未做统计校准的检测阈值，但仍需全部尺寸质量门。噪声非检出也保留有限候选D用于诊断，不把它隐去冒充全样本精度。

### 8.3 数量、保存与预算

- 开发目标：16训练D/h条件×3背景×2重复=96次测量，各1前景+8参考=864曝光。
- 开发空白：3×80×9=2160曝光。
- 验证空白：3×60×9=1620曝光。
- K噪声：6×3×5×9=810曝光。
- 轨迹：12×2×(8前景+8共同参考)=384曝光。
- **名义总计5838，硬上限6000。** 所有真正随机曝光有唯一event ID，失败重抽计入；只读复用不重复计。域外轨迹不补抽有利路径。

保存原始Y、8张参考、曝光、种子/生成器版本、truth-validator键、公共仪器配置。CSV只是结果索引，不能替代图像数组。数据与冻结阈值必须足以离线重放。

**不是所有统计模型都要一次成功。**某B未达到空白门，就保留检测范围限制；不妨碍已知颗粒ROI的条件尺寸诊断，但不能给这一B报告“检测验证通过”。

## 9. P5：真正的曝光/三维悬浮与连续共享D

轨迹沿用D55/115/185各4条、每条8帧，5000Hz。新种子见JSON。生成中的Dh=D只是合成假设。正式反演不得读真D/真轨迹或用其精确对中。

1. 保存1.25μs细路径；2.5μs路径来自同一实现的严格子采样。各路径**按自己的时间数组**插入曝光两端节点，路径与强度的插值方法明确，不继承旧索引。
2. 在求积分之前，用实际25或100μs全窗检查h/xy/gap及时间支持；离域返回结构化OUT_OF_DOMAIN，不能交给forward内部clip。对分段线性路径，端点及全部路径折点须检查。
3. 非均匀梯形权重按每段dt计算，总和1；必须覆盖整个T。不能只对窗口内残留几个点归一化后宣称完整曝光。
4. 先计算I，再时间平均，再用同条件Ibg归一。只有验证Ibg在此窗口不变后，时间平均C才与强度观测等价。
5. 三个D各一条轨迹至少检查三个共同合法帧，细粗C差目标0.5%；另报绝对差与弱响应判定。未达标只沿同一随机路径做有条件的Brownian bridge细化到0.625μs，保存桥接种子，旧时间节点不改变；不能重新抽轨迹挑较好结果。
6. 每轨迹/每曝光至少4个合法帧才进入M2，保留所有轨迹的有效长度和退出原因；两曝光比较报告共同合法帧与各自合法帧，不能只比较幸存样本。
7. 先做无噪声曝光期望图，再相同光通量计数：100μs背景1e4、25μs2500电子。加读噪的参考每轨迹/曝光只生成8张。
8. 连续共享D方法使用真正拼接残差/GLS；不要每帧独立D再均值。此处若逆模板仍是瞬时图，标签为`INSTANTANEOUS_TEMPLATE_UNDER_BLUR`，用于度量失配而非声称精确运动补偿。
9. 模拟图由训练插值模型产生时，标签仍为`SHARED_SURROGATE_DIAGNOSTIC`；它检验方法/实现，不是新的独立BEM验证。

原图、路径、时间、节点、权重、域标志、参考数组必须入H5；不得把每帧peak_C的CSV叫原图存档。

## 10. 统一资源、时间与失败处理

| 资源 | 上限 | 执行规则 |
|---|---:|---|
| 新BEM尝试 | 16 | ≤1必要资格 + ≤9一整行 + 6K；失败/重解均计 |
| 新render | 128 | 可行预留：旧63节点仅必要重成像≤63、补行≤18、K≤18、资格≤2、坐标/积分≤16，共117，余11；不是要求全部重做 |
| 相机随机曝光 | 6000 | 名义5838，余162；包括参考/空白 |
| 重物理进程 | 1 | 禁止重复后台批次 |
| 总窗口 | 12h | 预留30分钟归档；科学资源不足如实PARTIAL |

P0/P1首先使用旧数据。禁止用更新wrapper哈希为理由整库重算；禁止把已有模型自洽失败解释成“参数没给全”；禁止为了新K好看而按其结果改边界/相位/振幅。若插值器仍不合格，停止K而继续离线诊断、噪声数学/接口测试和完整交付。

不轻易引入新硬件。两焦面/偏振通道只允许作为以后受物理证据支持的设计讨论，本轮不改变用户现有单通道主任务，不假装同时取得额外实验信息。

## 11. 必须实现与实际运行的入口

推荐文件名是Codex实施要求，不宣称本包提供了完整科学求解器：

```text
config/v127_science_config.json
source/v127_physical_forward_adapter.m
tools/v127_run_all.py
tools/v127_cache_identity.py
tools/v127_canonical_forward.py
tools/v127_fit_single.py
tools/v127_profile.py
tools/v127_fit_track.py
tools/v127_camera_exposure.py
tools/v127_evaluate.py
tools/v127_infer_experiment.py
tools/v127_validate_science.py
tools/check_v127_return.py
```

所有入口使用绝对化的`--repo --config --out`，无个人Windows绝对路径。实际物理、成像、统计各有独立内容键；输出日志不能只写建议命令，必须保存实际命令、返回码、开始结束时间与错误。

`v127_infer_experiment.py`接收单颗粒线性ROI/短序列、同条件背景和仪器配置；不读取本轮未授权的大原视频，不凭文件名识别磁颗粒类别。参数仍假设时只能以显式`--allow-assumed-model`输出条件候选；未知单位/非线性显示图/饱和或背景不可用时拒绝有效粒径，输出原因。静态C与FFT幅值必须类型隔离。

## 12. 返回什么，怎样算完成

唯一`iscat_v127_return.zip`至少包含：

```text
00_README.md
01_V127_执行合同.md
status.json
review.md
config/effective_config.json
config/model_freeze.json
config/case_plan.csv
config/threshold_freeze.json
source/ # 所有实际源码和依赖，不只顶层几个py
library/ # 最终C/Ibg与可重放复场或等价系数、轴与训练索引
validation/contract_conformance.json
validation/holdout_images.h5
validation/holdout_truth_validator_only.json
validation/holdout_per_particle.csv
validation/profile_results.h5
validation/noise_per_trial.csv
validation/blank_per_trial.csv
validation/raw_camera_data.h5
validation/motion_per_track.csv
validation/trajectories_and_exposure.h5
diagnostics/old_HJ_recomputed.csv
diagnostics/canonical_closure.csv
diagnostics/interpolation_comparison.csv
logs/source_identity.json
logs/cache_identity.csv
logs/actual_commands_and_errors.txt
logs/event_ledger.jsonl
logs/resource_budget.csv
manifest_sha256.csv
```

未运行分支不造空表；status记`NOT_EVALUATED/BLOCKED`。输出完整科学结果也可以为失败，失败不是丢弃理由。每粒子：`candidate_D, reportable_D, h, x, y, profile_intervals, detected, converged, in_domain, boundary, identifiable, reason_codes, model_id`。

**验收分三层**：
1. 机械：完整manifest覆盖（除manifest本身）、CRC、唯一安全路径、每文件SHA、必要成员、当轮任务身份。
2. 可重放：在干净临时目录，只读ZIP中的源码与数据，重放一个原场观测和一个K/或失败诊断；不得读取外部Windows绝对路径补依赖。
3. 科学：逐项真实条件门、单例误差目标、优化/剖面、误报率和曝光资格。重现同一个错误D只证明可重放。

新`status`明确区分`execution`与`validation`。FPR或曝光目标没过时，相应validation写FAIL/INDETERMINATE，不能因为产生了CSV就PASS。原匹配门保持历史FAIL，实测重新同门通过才可单独更新，不得更换阈值。原始未报告粒子不计入“成功测得”分母；同时报告全部尝试和接受子集。

外回执记录ZIP哈希；ZIP内部不自引用自身最终SHA。科学检查有错误返回非零；机械检查通过不能消除科学失败。PACKAGING在最终状态写好之后执行。`PASS`子串判断和硬编码绿灯严格禁止。

**正常结束条件**：所有已放行且预算内的阶段完成，或有真实阻断/资源限制；全部已得结果、原始数据和失败证据完整交付。不是以“又生成一个版本号”为成果。

---

## 13. 本包自带工具的范围与来源

- `tools/contract_core.py`、`tools/test_contract_core.py`：域检查、曝光节点/权重、CP上界、连续网格/尺寸可报告逻辑等通用实现及单元测试；不包含NANOBEM。
- `tools/reproduce_review_checks.py`：发布六行表的算术及小型反例，明确不是HDF5/BEM重放。
- `tools/validate_handoff.py`：核对本交接包JSON、工况、预算算术、SHA和文件范围，不认证未来科学结果。
- `evidence/review_recomputations.json`：本次已执行的有限复算。
- `evidence/source_index.json`：下列Rxx和X01的固定来源URL。

本次审查结论来自已读来源；V127方法/阈值/工况是**新的执行设计**。其效果需要实际试验；不得写成已经提高精度、已经能测真实磁芯或已经达到纳米级实验分辨率。

### 固定来源索引

- [R01] [results/v126/status.json](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/status.json)
- [R02] [results/v126/review.md](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/review.md)
- [R03] [results/v126/validation/holdout_per_particle.csv](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/validation/holdout_per_particle.csv)
- [R04] [results/v126/validation/holdout_truth_validator_only.json](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/validation/holdout_truth_validator_only.json)
- [R05] [tools/v126_invert_particle.py](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/tools/v126_invert_particle.py)
- [R06] [tools/v126_forward_model.py](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/tools/v126_forward_model.py)
- [R07] [tools/v126_camera_and_thresholds.py](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/tools/v126_camera_and_thresholds.py)
- [R08] [tools/v126_exposure.py](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/tools/v126_exposure.py)
- [R09] [tools/v126_error_separation.py](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/tools/v126_error_separation.py)
- [R10] [results/v126/diagnostics/error_separation_I1.csv](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/diagnostics/error_separation_I1.csv)
- [R11] [results/v126/diagnostics/error_separation_I2.csv](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/diagnostics/error_separation_I2.csv)
- [R12] [results/v126/config/model_freeze.json](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/config/model_freeze.json)
- [R13] [results/v126/qualification/corrected_pairwise_numerics.csv](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/qualification/corrected_pairwise_numerics.csv)
- [R14] [results/v126/qualification/axis_and_nonzero_shift.csv](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/qualification/axis_and_nonzero_shift.csv)
- [R15] [results/v126/validation/fine_coarse_integral.csv](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/validation/fine_coarse_integral.csv)
- [R16] [results/v126/logs/resource_budget.csv](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/logs/resource_budget.csv)
- [R17] [tools/v126_intake_and_budget.py](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/tools/v126_intake_and_budget.py)
- [R18] [tools/v126_packaging.py](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/tools/v126_packaging.py)
- [R19] [results/v126_external_receipt.json](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126_external_receipt.json)
- [R20] [results/v126_science_validation.json](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126_science_validation.json)
- [R21] [results/v126/contract/01_V126_执行合同.md](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/contract/01_V126_执行合同.md)
- [R22] [results/v126/validation/motion_per_track.csv](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/results/v126/validation/motion_per_track.csv)
- [R23] [tools/v126_run_holdouts.py](https://github.com/yyyyzoey/iscat-handoff/blob/b546d80beb0dc4789effac8c192896e5f45876e9/tools/v126_run_holdouts.py)
- [X01] [SciPy 官方 least_squares 文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)
