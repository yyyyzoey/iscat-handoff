# iSCAT v069：v068审查裁决、受控后处理与观测量资格审查

> 执行者：Codex；审查与后续决策：GPT。
> 已审固定提交：`yyyyzoey/iscat-handoff@4a8820cf89f9c681bafda50a554866ce0f6822fe`（v068）。
> 本文件是下一轮执行指令，不是新的MATLAB/BEM结果。所有“审查端复算”均为源文本、表内算术或数学推导，未运行工作站求解器、未重新验证原始物理场。
> 最终目标仍为真实反射式iSCAT中磁纳米颗粒的观测量—粒径关系。现阶段是 `LITERATURE_MATERIAL_EXPLORATION`，不是实际批次、实际仪器的标定。

## 0. 本轮总令

**保留三尺寸已完成BEM解；本轮新磁材料/金球BEM为0。不要再仅生成一份新的“六条件稳定性表”后结束。必须兑现此前尚未完成的公共后处理、q、角度、Bessel四组对照。**

完整阅读后，自动连续执行所有前置满足、资源允许、预算内的任务；不每步停止等GPT。某分支失败只暂停有真实依赖的任务，其余继续。不能把物理前置失败、接口不可执行或归档缺失改成PASS；不能为方便导出重求BEM。

优先级：

```text
A  单一评分/保存入口：修正K2、恢复原数组、实际读回与失败拦截
B  已有均匀解补导fm与真实身份（零BEM）
C  完成原定6条件×4诊断配置，共最多24个新增侧render
D  同区域分解、残差投影与观测量误差来源报告
E  主表/孔径表归档补齐、实验提取器输入核对、既有独立支线
→ 一份ZIP、一个当前可读汇总；全部可执行工作统一交回
```

不要把E的全部历史整理当C的统一前置。A先使六个指定条件可复用并可持久化，B可并行做轻量导出，随后立即进入C。其余27条件原数组归档可以在C后继续，以免本轮再次只做归档而未执行研究对照。

## 1. v068审查裁决：保留哪些结果，哪些不能签通过

### 1.1 这次平表修复有可核对成果

审查端按连接器原文重建以下5份文件，全部Git blob与固定提交一致。没有改变源数据再进行验收。

| 文件（tables/） | 字节数 | Git blob |
|---|---:|---|
| v068_27condition_clean.csv | 7408 | a2181df90a065d9750e1b0a9079325ac3e9aa7e7 |
| v068_aperture_dependence.csv | 18009 | 3dc652eb4710e5504de55f0add53419efd205fb5 |
| v068_six_key_observations.csv | 1625 | 1b44e93265e3bd2d9f5450c5c0baa9b94e4d35a3 |
| D30_homog_full_precision.json | 341 | 9b4abbea3129b2e7557410c81070bc3490914377 |
| D100_homog_full_precision.json | 341 | 61bb181b44bdcdf76fa20d2524608673b39b192f |

实际审查范围：195行CSV（27+162+6）和2份JSON、完整v068驱动及原生日志。

- 主表27×15、孔径表162×8、六条件表6×14，行/列数、精确键集合、数值有限性与控制字符检查通过。
- 主表27个 numerator/denominator 复算与表列Frobenius在本地双精度下相同，范围为 **0.005137840781999895—0.006922562704262311**，表报原2%数值门槛均通过。
- 162孔径记录中27条41像元记录，与主表的积分和Frobenius列一一相同。
- 162条生产侧正负积分相加与总积分对账，按正负绝对量和归一化的最大残差约 **4.80e-16**。
- 六条件的chi1从正/负积分复算，最大绝对差约 **2.27e-13**，相对精度一致。

**接受结构修复和表内算术验证；不把它们写成审查端已读取原始图、复场、sol并重新执行物理验证。**原v067坏CSV保留在历史中，不能再说当前三张新平表也有同样损坏。[S03–S07]

### 1.2 两个均匀基准三截面可以复核，第四项仍缺全精度导出

源JSON原值复算：

| D/nm | 散射相对误差 | 吸收相对误差 | 消光相对误差 |
|---|---:|---:|---:|
| 30 | 0.008242036020553727 | 0.003921133910361484 | 0.004172651334842122 |
| 100 | 0.007713323341846603 | 0.004577515681323401 | 0.006542914993084271 |

三项都小于0.02，保留原求解的报告通过。不要重求30/60/100均匀BEM。

但v068导出循环只拷贝顶层标量，`fm`是结构，因而其 `raw_complex_relative_L2` 没有导出；两份JSON也不含从已解对象取出的n/κ/ε等实际读回。`export.material`和`export.medium`是驱动写入的说明字符串，不能当实际对象读回证据。原日志仍只有rawL2约0.0039。下一轮显式导出已存fm字段与原sol身份，而不是对整份对象使用“只保留标量”的通用过滤。[S02,S06,S07,S08]

### 1.3 新K_S2列的数学定义没有实现正确

v068写的是：

```matlab
K_f=sqrt(N41)*norm(tmp_f,2)/abs(sum(tmp_f(:)));
```

`tmp_f`是41×41矩阵；MATLAB矩阵二范数是最大奇异值。原像元L2条件因子应使用 `norm(tmp_f(:),2)` 或Frobenius。这是独立的K指标实现错误，**不影响已经正确使用展平L2的主表评分，也不推翻chi1的算术**。[S02,E01]

令 `Apx=65^2 nm²`，主表denominator为参考ROI的像元L2范数，故无需原图也能作表内交叉核对：

\[
K_{2,R}=\frac{41\,\mathrm{denominator}}{|S_R|/A_{px}}.
\]

| D/zf（nm） | 原K_S2_fine（矩阵谱范数） | 审查端按主表分母复算的像元K2_fine |
|---|---:|---:|
| 30/450 | 13.9906372817 | 15.4387095803 |
| 30/550 | 13.6068722653 | 15.3465885575 |
| 60/450 | 11.2007371736 | 12.4922284421 |
| 60/550 | 10.6881327016 | 12.0954577170 |
| 100/450 | 962.9579493990 | 1268.8400914733 |
| 100/550 | 78.6029587119 | 104.6300321652 |

这些是源表数学关系的复算，不是原场重评；生产侧的正确K2需由生产原图另算，不用参考侧范数冒充。旧列保留为 `K_spectral_diagnostic`，新列 `K_pixelL2` 从数组生成，不改旧数值标签。[S03,S05]

### 1.4 chi1确实高，但不是已定位的误差来源

D100/z450、41×41：

- 生产：S+=368322.166160569、S−=−370068.57077720895、S=−1746.4046166400562 nm²，chi1≈422.8062213660。
- 精细：S+=370487.59251968155、S−=−371484.66813700722、S=−997.0756173256880 nm²，chi1≈744.1484354484。
- 两侧积分绝对差749.3289993144 nm²，相对精细积分差0.7515267511（约75.15%）；同ROI图像Frobenius约0.59426%。

高chi1支持“有符号积分强抵消，对某类图像扰动敏感”。它不证明求和函数算错、机器舍入是主因、某一物理机制唯一负责，也不证明实际噪声/粒径误差已经知道。不要通过把S改成abs(S)、sum(abs(C))、删除负像元或改孔径来让chi变小后沿用旧测量定义。[S03,S05]

### 1.5 孔径依赖现在有直接证据，但孔径长表仍未包含所有约定量

同一D100/z450精细侧，孔径21/31/41/51/61/65的积分分别约：

```text
-7154.827596, +7530.820307, -997.075617,
-8478.634947, -7380.096105, -1606.311530  nm²
```

这可支持“在这些固定有限孔径上，积分大小乃至符号随孔径改变”，不是仅凭P/R根不同推论。不能推出无限孔径收敛，也不授权选31像元取代原41像元。

另有D100/z575/ap61：生产−350.659824、精细+436.448905 nm²，符号相反。应保留，不删为异常样本。[S04]

但162行目前只有生产侧S+/S−，没有全套精细正负项、Cs/Cint孔径积分、chi/K2及必要的原数组。六条件表只补了这六格两侧正负项，不能把它当全162格完整诊断。数据字段缺项与物理失败分开。

### 1.6 最关键的执行偏差：此前的受控后处理并未完成

v068原任务是：

```text
六个条件：D60/z512.5、515；D100/z425、435、437.5、450
四种诊断：P_common、F_q7、F_angle200_301、F_bessel8001
```

实际新驱动却选了 `D30/60/100 × z450/550`，仍使用各自原配置，并再次render这六个主条件，计算chi/K。源码、日志和文件树未提供原24个受控配置的执行证据。**六个已有主条件的描述性统计不能替代六个既定异常条件的单因素实验。**[S01,S02,S08,S09]

本轮开始即标：

- `descriptive_six_condition_metrics = COMPLETED_WITH_K_CORRECTION_NEEDED`；
- `controlled_postprocess_24 = NOT_ESTABLISHED / NOT_STARTED`，按实际工作站检查更新；
- 原24项额度仅扣真实同身份已完成项，不因为名为“six key”而认为已用或已完成。

### 1.7 归档和根因解释的证据仍有限

当前源码没有条件级数组save/检查点；主27重render后只写标量，随后又重render六个重复条件。numeric_inventory只声明工作站有render，不含每文件变量/shape/hash，分支也没有原数组包。先查实际是否另存，不能断言丢失；但不能据目录说明标 `evidence=COMPLETE`。

status报告I/O隔离测试，但本提交未提供对应测试脚本和逐项原生日志；“嵌套＋混合字段＋复数”联合根因暂保留为执行者解释。接受新平表实际可解析，不自动接受每个根因均已证明。原v067主记录各标量是否涉及复数与复数写入演示是否相关应分开。

根材料合同、manifest、旧主汇总/任务账仍有历史累积版本；补当前active清单，不让旧错误1987/0.0831i等覆盖实际参数。不得为了合同更正重求BEM。[S09]

## 2. A：共享评分与原数组持久化，先通过一个小型闭环

### [放行条件]

核对工作站实际root/run/进程；固定NANOBEM原基线不改。只使用已知源码路径，不对全部历史目录做genpath。读取sol的来源和物理身份，不单凭文件名、当前cfg字符串或新建材料对象替旧解签证。

### [必查项]

**先评分、保存、读回一份小夹具，再开始重后处理。**成功的数值数组写出并读回后才算计划完成；CSV失败不得消耗第二次render。

统一 `score_observable(C,roi,pixel_nm)`：

```text
c = C(roi), 并立即展平为像元向量
s = sum(c)
L1 = sum(abs(c))
L2 = norm(c,2)
chi1 = L1 / abs(s)
K_pixelL2 = sqrt(numel(c))*L2 / abs(s)
S_area = pixel_nm^2*s
S_plus = pixel_nm^2*sum(max(c,0))
S_minus = pixel_nm^2*sum(min(c,0))
```

只有有限、实数、shape合法的C进入此函数；参考强度I0需由同一后处理对象取得并检查有效。输出chi/K前处理真零及算术不可分辨分母，返回null及reason，不用realmin补分母。原 `64*eps*sum_abs` 仅作算术诊断，不是噪声、物理精度或D门槛。

必须实跑的轻量测试：

1. `eye(2)`：N=numel(C)=4，chi1=1、像元K2=sqrt(2)≈1.41421356237；错误谱范数版本给1，必须被拒绝。此夹具专门防止K指标再退回矩阵范数。
2. 非零矩阵应满足 `K_pixelL2 >= chi1 >= 1`，按原工程容差比较；全零和和为零不套此分母判断。
3. 负缩放/正缩放改变S但不改变chi/K；只用于数学夹具，不引入生产自由缩放。
4. 27/162/6键和跨表对应、旧损坏CSV拒绝、False解析、NaN/Inf及hash错的拒绝。
5. 保存成功—导出失败—再次启动：BEM与render真实调用计数不得增加，只补导出。
6. requested配置与evaluated配置不符、只有cfg角度改变而far/lens沿用旧缓存，必须阻止该诊断结果登记完成。

新增或修改的评分代码与生产入口一起调用，不能把测试另写一套未使用公式。MATLAB原生运行与审查端Python复算分开记录。本轮明确授权最多2轮定向评分/持久化轻量修复，旧修复账不清零；超限交最小复现并继续无依赖工作。

### [保存与身份]

每个侧render保存普通数值：`C,I0,Cs,Cint,x_nm,y_nm`，必要时子像元Es/Er或公共远场另存；不要只保存MATLAB类对象。与数组同时保存：D、zf、gap/中心h、n/κ/ε实际读回、λ、收集介质、NA、偏振、pixel、q、ntheta/nphi/Bessel实际值、source_sol_hash、solver及render源码身份、phase约定。

临时MAT/NPZ写完并读回校验后原子提交。缓存键含物理配置、数值配置和源sol/源码hash；存在但身份不符不能复用。已有符合全部身份的数组必须直接用；不为根名、表名、绘图再render。

### [失败处置]

身份或存储闭环失败，停受影响render分支；补导出与已有表复核可继续。所有失败保留，不能把计划配置写成“实际已用”。无新增BEM资格。

## 3. B：均匀基准第四项和真实读回补齐（零BEM）

### [放行条件]

v067已有D30/D100真均匀MAT可读；v064正确D60的已有证据继续保留。没有某个场不等于原BEM物理失败。

### [动作]

显式读取：`fm.raw_complex_relative_L2`、原比较分子/分母（如已保存）、bs/as/ba/aa/bx/ax、原passed、实际材料与几何。不要用泛型“只拷标量”过滤掉fm，也不要手写material字符串冒充读回。

两端点原sol存在但远场缺失，沿原 `sphere_rule(48,97)` 各允许最多一次公共远场后处理；保存eB/eM、方向、权重和规范，不自由相位/幅值对齐。匹配缓存扣除调用。三截面与raw复场四项仍分别<0.02，按未舍入值计算。原同一数据的能量等式只作代数检查。

实际读回常数容差沿原1e-12。达不到须报原差值，不静默放宽。没有原sol时保留摘要PASS_REPORTED、evidence=PARTIAL，不重求解。当前工程身份仍需区分均匀Galerkin与玻璃/水分层，禁止错误homog命名重新进入。

### [完成后]

输出`homogeneous_four_gates.csv`与普通数值远场包；源数组无法取回则字段明确缺失。该归档缺项不自动取消其余已有分层后处理；如发现共享材料/场景实际错，按影响范围暂停。

## 4. C：本轮必须兑现的六条件×四组受控后处理

### [放行条件]

A通过；六条件P_base/F_base原数组可重读，实际分层参数身份核对；不存在活跃重复任务。条件为**原v068已规定、尚未证明完成的开发诊断**，不是新盲测。

固定条件表，禁止换成D30/60/100×450/550：

| case_id | D/nm | zf/nm |
|---|---:|---:|
| K01 | 60 | 512.5 |
| K02 | 60 | 515 |
| K03 | 100 | 425 |
| K04 | 100 | 435 |
| K05 | 100 | 437.5 |
| K06 | 100 | 450 |

原基线：P_base为576解、50/51角度、Bessel2001、q5；F_base为1444解、100/151、4001、q5。既有两基线只复用或按缺项恢复，不能偷偷被新精度覆盖。

| task_suffix | 边界解 | ntheta/nphi | Bessel表 | q | 新侧render上限 |
|---|---|---|---:|---:|---:|
| P_common | 原576解 | 100/151 | 4001 | 5 | 6 |
| F_q7 | 原1444解 | 100/151 | 4001 | 7 | 6 |
| F_angle | 原1444解 | 200/301 | 4001 | 5 | 6 |
| F_bessel | 原1444解 | 100/151 | 8001 | 5 | 6 |

必须从既有sol重建所需far/lens采样对象。只改cfg而缓存仍是旧角度/旧表的不算执行；严禁调用build_system、bem反斜杠求解或创建新BEM以绕过后处理接口。q7只改变固定65 nm像元内部积分，不能把相机像元或光子数改变。

同一D/sol的公共远场和镜头数值对象可在其不同焦面复用，但每个D/zf/配置只产生一次正式侧render。修改数值分辨率时，物镜NA、玻璃侧收集介质、背景归一化和物理光路必须仍相同。所有来源hash按真正使用对象登记。

### [对照与证据]

每个条件输出以下比较：

1. P_base−F_base：原总差；
2. P_base−P_common：生产后处理组合变化；
3. P_common−F_base：相同后处理下的边界解侧剩余差；
4. F_q7−F_base；
5. F_angle−F_base；
6. F_bessel−F_base。

前三个向量检查望远镜式恒等关系，但不可对几个范数/百分比直接相加减。第3项在材料、装配规则、相同几何及其余参数没全面一致前，不能简称“纯网格误差”。后三项各是单一数值因素的有限增量，不是绝对误差上界；没有联合加密，不排除交互项。

全部比较保存C、Cs/Cint/I0的原数值，原41×41全图指标、中心量、同孔径有符号积分、chi1、正确K2和绝对变化。相对标量在非零且可分辨时照实输出，不能因大于2%改原门槛，也不能因全图PASS写标量稳定。

每完成一个配置，通过持久化及读回即自动进入下一个。全部24计划应有逐项状态；输出中不允许用一个“six_key_observations PASS”覆盖它们。若接口不能执行，写明具体缺失API/对象、调用栈和零BEM限制，继续其他可执行配置。

## 5. D：把抵消与误差来源分开解释

### [同一空间支持的场强分解]

以实际像元积分算子P_j为准：

\[
I_{0,j}=P_j(|E_r|^2),\quad
C_{s,j}=P_j(|E_s|^2)/I_{0,j},\quad
C_{\mathrm{int},j}=P_j(2\operatorname{Re}(E_r^*\!\cdot E_s))/I_{0,j}.
\]

先形成子像元强度后积分，不先平均场再平方。检查

\[
\frac{\|C-C_s-C_{\mathrm{int}}\|_2}
{\|C\|_2+\|C_s\|_2+\|C_{\mathrm{int}}\|_2}\le10^{-12}.
\]

全零单独记绝对残差。旧最大范数闭合另列诊断。每个孔径的S_s、S_int与S必须同一区域相加；65×65全图均值不能解释41×41积分。干涉项不是吸收项，不将此分解当做改变κ的因果实验。

### [线性提取误差的审查框架]

对固定孔径令 `c=vec(C_R)`、`delta=vec(C_T-C_R)`、`w=Apx*ones(N,1)`，则

\[
\Delta S=w^T\delta,\quad
\frac{|\Delta S|}{|S_R|}\le K_{2,R}\,\frac{\|\delta\|_2}{\|c\|_2}.
\]

可再记录投影系数（新诊断量，不新增通过门槛）：

\[
\eta=\frac{|\mathbf1^T\delta|}{\sqrt N\|\delta\|_2},\qquad
\frac{|\Delta S|}{|S_R|}=K_{2,R}\,r_F\,\eta.
\]

delta为0时直接标零差；S_R为0时相对量无定义；不能做除零填0。实图条件下0≤eta≤1；检查此代数关系只是同一数组的一致性，不是物理独立验证。

审查端由D100/z450已发表标量得到K2≈1268.8401、rF≈0.00594260、eta≈0.0996693，实际相对积分差约0.7515268。该例表明高K只是允许强放大；实际差还取决于残差方向。不能把chi744直接解释为误差必放大744倍。

同理，若分量扰动满足|delta_i|≤epsilon*|c_i|，才有相对积分界chi1*epsilon；没有分量扰动界，不把chi当已知误差条。

### [结论必须按量和来源给]

- 高chi：报告有限孔径抵消，标数值敏感区域；不删除该点、不把积分改为绝对值、不优化孔径追求好指标。
- q/angle/Bessel某增量明显：报告该受控配置的图像与标量变化，不直接宣布唯一原因。
- 公共后处理后剩余明显：报告边界解侧差异仍在；没有更细网格/规则真值不能签收敛。
- 相对标量很大而绝对量小：同时给绝对差、源信号大小和符号，不事后伪造统一的标量2%门槛。
- 缺关键原数组/设置证据：结论为INDETERMINATE，不填“正常”“稳定”或“全部完成”。

单颗粒D误差还需S对D的可靠局部响应、相关光路/几何约束及提取器定义。本轮只有三尺寸探索和焦面诊断，禁止从chi、相对图误差或零点差直接给粒径误差。

## 6. E：归档补齐范围与本轮明确预算

### [新的、有限的恢复范围]

为避免再次把整个45条件反复计算，本轮只对**主27条件＋受控对照所需的4个内部焦面点**给出一次性缺失数组恢复授权：

- 主条件：D30/60/100 × zf375:25:575；
- 额外已有点：D60/z512.5、515；D100/z435、437.5；
- 共31个唯一物理条件，P/R两侧，最多62个侧render。

这是**本轮明确的新归档恢复上限**，不是抹去v067/v068已经消耗的后处理成本。必须先找实际保存的数组/场，命中即不render。源驱动没有save不证明工作站必丢失；反过来仅有目录声明不等于有可读数组。

其余旧D3内部14点不新增恢复render：有实际归档就直接导出；只有旧舍入JSON就保留相应精度和证据状态。这里是本轮明确缩小恢复范围，将计算资源优先交给未执行受控对照，不是宣布余点已验收。无新D/zf采样、无进一步二分零点。

### [预算表]

| 任务 | 本轮上限 | 授权/来源 |
|---|---:|---|
| 新磁材料/金球BEM | 0 | 不重求三尺寸，不建密库 |
| 两端点原解远场补证 | 各≤1次 | 继承原未完成后处理，缓存扣除 |
| 缺失原条件数值恢复 | ≤62侧render | 本轮明确一次性新上限；31条件，已有数组则0 |
| 六条件四配置 | ≤24侧render | 继承v068尚未证明完成的24项，不清零实际完成账 |
| 主表、孔径、K2、分解归约 | 复用数组，不单独render | 原孔径6种 |
| 评分/保存轻量修复 | ≤2轮 | 本轮明确授权，旧账保留 |
| 新D/λ/gap/材料/孔径/焦面扫描、相机噪声 | 0 | 不放行 |
| P0 rule7 | 原条件余量≤1 | 只在独立专属前置全满足后；非本轮新额度 |

磁材料图像后处理最坏上限62+24=86次，不含原均匀解的非成像公共远场操作。不是要求跑满86；一份数组要同时服务归档、评分、孔径和图表，不能每一种用途重复render。

### [其余旧分支]

P0的正确相对SL/DL、完整direct/reflected/total各<1e-10、真实目标路径Hook与原<0.005参考增量继续保持。独立P0未闭合不自动挡住未受影响rule3；确实发现共用实现问题则按影响范围暂停。危险分配前诊断停止，不反复制造OOM；大型P0不与重后处理并发。

R5确定性4-seed恢复、R6边界32份/4×21剖面及提取器解析补项仅继承真实未用额度，不因版本号增加重置。本轮没有新金球统计批次。

恢复真实提取器仅用已确认的test.m/原工程线索；不存在源码就保留NOT_FOUND及检索证据，不重写成实测合同。明确区分演示65 nm/520 nm配置和历史实验数据。材料文献值不是实际批次数据；真实仪器和动态400 Hz处理没有接入时不输出实验绝对粒径。[S10]

## 7. 返回与自动判定要求

先staging后发布，所有状态由真实任务表聚合。三元状态保持：execution / validation / evidence。建议根overall为PARTIAL，只有本轮全部前置、计划和证据按定义齐备才改为相应完成；允许“表内数值通过、原数组证据部分”。

必须交回一份ZIP，至少包括：

```text
iscat_v069_return.zip
  00_README.md / 00_全部文本汇总.md      # 当前结果，不是v059旧汇总
  00_Codex_v069_执行指令.md
  status.json / review.md / active_contracts.json
  tables/
    score_and_cache_tests.csv
    source_runtime_identity.csv / solve_and_render_ledger.csv
    homogeneous_four_gates.csv
    primary27.csv / primary6.csv / aperture162.csv
    scalar_condition_metrics.csv
    controlled_postprocess_plan24.csv
    controlled_postprocess_results24.csv
    common_field_comparisons.csv
    observable_error_attribution.csv
    task_status.csv
  numeric/
    primary27_arrays.mat
    key6_baseline_arrays.mat
    controlled24_arrays.mat
    homogeneous_farfield_evidence.mat
    numeric_inventory.json
  source/                             # 实际驱动、score、save/restore、所需render/helpers和差分
  logs/                               # 实际前置、单因素、失败/恢复原件
  history/                            # 旧错指标/坏表/历史合同，不覆盖
  manifest_sha256.csv
```

数组必须是可由独立程序读取的普通数值，不只给类对象。material/solver读回数据包含来源身份，不能新建一个正确材料对象来证明旧sol采用正确材料。大sol可继续留工作站，但本轮普通C/I0/Cs/Cint与数值远场至少要有可读小包；只返回目录描述不得标evidence=COMPLETE。

CSV校验：27主键完整；孔径162键完整；受控24键精确为K01…K06×四后缀；不存在的配置必须有NOT_EXECUTABLE原因而非缺行；六条件摘要只从主表筛选，受控六条件表使用另名，不混淆。

JSON不写NaN/Inf，null配reason；数字由未舍入数值导出。manifest对最终字节计算，不能复用旧manifest。实际上传后下载关键文件重验schema/hash。仅发布已授权合成数据；实验原帧、凭据、个人信息不擅自公开。

每个可运行阶段通过后自动继续。不要在重复计算chi后请求GPT是否处理高chi；本文件已经决定：**保持观测定义、补正确K、完成误差来源对照，不直接增加BEM或改积分定义。**

## 8. 本轮结束后应能作出的决策

本轮未授权完整Fe3O4密库。交回时应回答：

1. 已有固定场景/波长/材料的三尺寸均匀与分层结果，哪些原门槛和证据真正闭合？
2. 在相同孔径上，中心量与积分量的数值差由哪些受控后处理增量支持？哪些仍只是边界解侧剩余或不能归因？
3. 实际实验程序最后提取的是静态中心、积分、DoG还是FFT/复数解调？哪些源文件已取得？
4. 只有上述匹配后，才提出下一轮D节点/留出/噪声和测径误差预算，不能三点拟合D³、依据标称值强锚定或认为高chi能直接给出D误差。

## 9. 证据索引与外部核验范围

所有S01—S09取自固定v068提交，源文件完整路径相对仓库根：

| 编号 | 来源 | 支持内容 |
|---|---|---|
| S01 | status.json、review.md | 执行者报告及本轮解释 |
| S02 | source/run_v068_comprehensive.m | 正确主表范数、错误K范数、标量过滤、重复render、实际条件集合 |
| S03 | tables/v068_27condition_clean.csv | 27条件分子/分母、有符号响应 |
| S04 | tables/v068_aperture_dependence.csv | 162条固定孔径记录 |
| S05 | tables/v068_six_key_observations.csv | 六条件正负项、chi与旧K |
| S06 | tables/D30_homog_full_precision.json | D30三截面全精度标量 |
| S07 | tables/D100_homog_full_precision.json | D100三截面全精度标量 |
| S08 | logs/matlab_run.log | 本轮实际可读运行输出，不含单因素配置 |
| S09 | 完整目录树、numeric_inventory.csv、00_Codex_v068…md | 可读产物范围与原任务合同 |
| S10 | 已上传progress(2).md | 长期科研目标/冻结约束，不覆盖新的执行结果 |
| E01 | MathWorks norm官方文档 | 矩阵2范数为最大奇异值，Frobenius等价展平像元L2 |

外部仅核对API含义，不引入未提供的实验事实：

```text
https://www.mathworks.com/help/matlab/ref/norm.html
```

下面附审查端实际运行的源表复核程序。输入为固定提交的五份tables文件；它不运行MATLAB/BEM、不读原始光学数组，因此其结果仅为文件与算术审查。文件哈希不符时应停止，不自行清洗或改数据使之通过。

运行示例：

```text
python audit_v068_exports.py <固定提交的tables目录> --output v068_text_audit.json
```

```python
from __future__ import annotations
import argparse,csv,hashlib,io,json,math
from pathlib import Path
parser=argparse.ArgumentParser(description="Pinned v068 text/scalar audit; does not run MATLAB or BEM")
parser.add_argument("input_dir",type=Path,help="Directory containing the five pinned CSV/JSON files, normally repository tables/")
parser.add_argument("--output",type=Path,default=Path("v068_text_audit.json"))
args=parser.parse_args()
SNAP=args.input_dir
EXPECTED={
 "v068_27condition_clean.csv":"a2181df90a065d9750e1b0a9079325ac3e9aa7e7",
 "v068_six_key_observations.csv":"1b44e93265e3bd2d9f5450c5c0baa9b94e4d35a3",
 "v068_aperture_dependence.csv":"3dc652eb4710e5504de55f0add53419efd205fb5",
 "D30_homog_full_precision.json":"9b4abbea3129b2e7557410c81070bc3490914377",
 "D100_homog_full_precision.json":"61bb181b44bdcdf76fa20d2524608673b39b192f"
}
def load_csv(name,nrows,ncols,keys):
    b=(SNAP/name).read_bytes()
    h=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    assert h==EXPECTED[name],(name,h)
    t=b.decode('utf-8',errors='strict')
    assert not [(i,ord(c)) for i,c in enumerate(t) if ord(c)<32 and c not in '\t\n\r']
    rows=list(csv.reader(io.StringIO(t),strict=True))
    assert len(rows)==nrows+1 and all(len(r)==ncols for r in rows)
    hdr=rows[0]; assert len(set(hdr))==ncols
    vals=[dict(zip(hdr,map(float,r))) for r in rows[1:]]
    assert all(math.isfinite(v) for row in vals for v in row.values())
    got=[tuple(row[k] for k in keys) for row in vals]; assert len(set(got))==nrows
    return vals,{'file':name,'bytes':len(b),'blob':h,'sha256':hashlib.sha256(b).hexdigest(),'rows':nrows,'cols':ncols,'controls':0}
main,mcheck=load_csv('v068_27condition_clean.csv',27,15,('D_nm','zf_nm'))
key,kcheck=load_csv('v068_six_key_observations.csv',6,14,('D_nm','zf_nm'))
assert {(r['D_nm'],r['zf_nm']) for r in main}=={(d,z) for d in (30,60,100) for z in range(375,576,25)}
idx={(r['D_nm'],r['zf_nm']):r for r in main}
ratio_diffs=[]
for r in main:
    assert r['denominator']>0 and r['numerator']>=0
    rr=r['numerator']/r['denominator']; ratio_diffs.append(abs(rr-r['frobenius_relL2_41x41']))
    assert math.isclose(rr,r['frobenius_relL2_41x41'],rel_tol=1e-13,abs_tol=1e-16)
    assert r['gate2pct_frobenius']==float(rr<.02)
keyaudit=[]; chi_diffs=[]; sum_residuals=[]
for r in key:
    mr=idx[(r['D_nm'],r['zf_nm'])]
    for f in ('C_center_prod','C_center_fine','S_area_prod_nm2','S_area_fine_nm2'): assert r[f]==mr[f]
    for side in ('prod','fine'):
        plus=r[f'S_plus_{side}_nm2']; minus=r[f'S_minus_{side}_nm2']; s=r[f'S_area_{side}_nm2']
        assert plus>=0 and minus<=0 and s!=0
        res=abs(math.fsum([plus,minus])-s)/(plus-minus)
        sum_residuals.append(res);assert res<=1e-12
        chi=(plus-minus)/abs(s); chi_diffs.append(abs(chi-r[f'chi1_{side}']))
        assert math.isclose(chi,r[f'chi1_{side}'],rel_tol=1e-12)
    rf=mr['frobenius_relL2_41x41']
    # Exact algebra from reported pixel Frobenius denominator and area integral,
    # not an independent read of the raw pixel array.
    k2=41*65**2*mr['denominator']/abs(r['S_area_fine_nm2'])
    area_rel=abs(r['S_area_prod_nm2']-r['S_area_fine_nm2'])/abs(r['S_area_fine_nm2'])
    upper=k2*rf
    eta=area_rel/upper
    assert area_rel<=upper*(1+1e-12)
    keyaudit.append({'D':int(r['D_nm']),'zf':int(r['zf_nm']),'chi1_prod':r['chi1_prod'],'chi1_fine':r['chi1_fine'],
        'K_S2_fine_reported':r['K_S2_fine'],'K2_fine_from_main_den':k2,
        'K2_correction_relative':k2/r['K_S2_fine']-1,
        'image_relF':rf,'area_abs_diff_nm2':abs(r['S_area_prod_nm2']-r['S_area_fine_nm2']),
        'area_rel_to_fine':area_rel,'cauchy_bound_rel':upper,'projection_eta':eta})
ha=[]
for d in (30,100):
    name=f'D{d}_homog_full_precision.json';b=(SNAP/name).read_bytes()
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==EXPECTED[name]
    x=json.loads(b);errs={}
    for bkey,akey,ekey in [('bs','as','es'),('ba','aa','ea'),('bx','ax','ex')]:
        e=abs(x[bkey]-x[akey])/abs(x[akey]);assert math.isclose(e,x[ekey],rel_tol=1e-13)
        assert e<.02;errs[ekey]=e
    ha.append({'D':d,'errors':errs,'raw_complex_relative_L2_present': 'raw_complex_relative_L2' in x or 'fm' in x,
      'bem_energy_balance_abs':abs(x['bx']-x['bs']-x['ba']),
      'note':'energy identity only, not independent physical validation'})
result={'scope':'TEXT_AND_SCALAR_AUDIT_ONLY_NO_MATLAB_NO_BEM_NO_RAW_FIELD_ARRAYS',
 'commit':'4a8820cf89f9c681bafda50a554866ce0f6822fe','structure_checks':[mcheck,kcheck],
 'frobenius_ratio_max_abs_diff':max(ratio_diffs),'frobenius_range':[min(r['frobenius_relL2_41x41'] for r in main),max(r['frobenius_relL2_41x41'] for r in main)],
 'chi1_max_abs_diff':max(chi_diffs),'plus_minus_reconciliation_max_scaled_abs':max(sum_residuals),
 'key_observations_recalculated':keyaudit,'homogeneous_scalar_checks':ha}
# Aperture table: full file, not just selected rows.
ap,acheck=load_csv('v068_aperture_dependence.csv',162,8,('D_nm','zf_nm','aperture_px'))
assert {(r['D_nm'],r['zf_nm'],r['aperture_px']) for r in ap}=={(d,z,a) for d in (30,60,100) for z in range(375,576,25) for a in (21,31,41,51,61,65)}
apnorm=[];apmatch=0
for r in ap:
    plus,minus,s=r['S_plus_prod_nm2'],r['S_minus_prod_nm2'],r['S_prod_nm2']
    assert plus>=0 and minus<=0 and plus-minus>0
    res=abs(math.fsum([plus,minus])-s)/(plus-minus);apnorm.append(res);assert res<1e-12
    if r['aperture_px']==41:
        mr=idx[(r['D_nm'],r['zf_nm'])]
        assert r['relL2']==mr['frobenius_relL2_41x41']
        assert r['S_prod_nm2']==mr['S_area_prod_nm2'] and r['S_fine_nm2']==mr['S_area_fine_nm2']
        apmatch+=1
result['structure_checks'].append(acheck)
result['aperture41_matches_main']=apmatch
result['aperture_plus_minus_max_scaled_abs']=max(apnorm)
result['D100_z450_apertures']=[{k:r[k] for k in ('aperture_px','S_prod_nm2','S_fine_nm2','relL2')} for r in ap if r['D_nm']==100 and r['zf_nm']==450]
result['aperture_sign_disagreements']=[{k:r[k] for k in ('D_nm','zf_nm','aperture_px','S_prod_nm2','S_fine_nm2')} for r in ap if r['S_prod_nm2']*r['S_fine_nm2']<0]
args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))

```
