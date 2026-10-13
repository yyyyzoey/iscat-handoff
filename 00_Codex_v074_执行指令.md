# iSCAT v074 唯一执行指令：v073真实FFT验收收口、400 Hz信号资格审查与520 nm受约束动态前向试验

> **性质与角色**：这是在真实审查之后交付Codex的**执行方案**，不是已经运行的新仿真结果。Codex负责工作站执行、保存证据和打包；ChatGPT下一轮核查。所有未运行、数据缺失或数学推断，均不得提升成PASS。满足前置条件与预算时**连续自动执行**，不必每小步停止等待GPT；受影响分支失败则停该分支、保留失败，其他独立分支继续。
>
> **固定审查对象**：`yyyyzoey/iscat-handoff`的`v073`，commit **`7cee6972be5c0e361820f737093148ca6c9f4e17`**；其父提交`v072`=`e1abfed0dca0acf9e656f39775d8274ceb561a0c`。下一次提交到新的可读`v074`分支，不静默从移动HEAD读取其他版本。
>
> **用户明确确认**：真实实验激光**真空波长520 nm**。正式候选测量量选择**400 Hz单边归一化复数调制对比度的模值**；正频率目标为400 Hz，`Fs=5000 fps`、帧索引1000–3000、`N=2001`时实际离散频点为**399.80009995002496 Hz**。保留复数值/相位作为诊断；420 Hz灰度FFT幅值仅作对照。用户没有确认真实NA、总放大倍率、物方像元、曝光时间、磁场驱动波形、磁驱动参考相位、实际颗粒批次光学常数和运动轨迹/高度，**不得代填**。

---

## 0. v073逐项审查裁决：什么可以继承，什么仍需验证

本次实际读取了固定提交的完整递归树、`status.json`、`review.md`、`source/extract_fft_v073.m`、`source/run_v073_replay_corrected.m`、`source/run_v073_fft_validation.m`、`source/run_v073_verify_recheck.m`、主DFT核对表、掩码质量表、频谱邻域表、输入缺口表、缓存账本与异常历史。审查端**没有在本机MATLAB重新运行2001帧，也没有下载工作站的全部原图或大MAT**；以下“通过”严格限定于已返回源码、表格和工作站所报验证。

| ID | v073源证据及数学复核 | 评判 | 禁止扩大解释 |
|---|---|---|---|
| F0 | 正确维度抽取器`extract_fft_v073.m`对`timeDim>ndims`拒绝，三维/四维FFT核验相等；目标bin `k0=160/k=161` | **PASS within N=2001/Fs=5000 scope** | 不是任意采样频率、任意N的通用算法已验 |
| F1 | 同一7.29组2001帧，12像元显式双精度DFT与单精度FFT最大非零相对差`3.6760898156602e-7`、相位差`3.4503739332337e-7 rad`；其中2个角像元的DFT系数为精确零 | **有根据的抽点数值验证** | 不是全部10.4万像元的独立DFT，更不是磁信号物理验证；所选最亮点是按数据选择的开发性检查 |
| F2 | 41×41 ROI另一个MATLAB会话：3D/4D与保存FFT最大差为0；原始全幅的meanFloor与仅ROI重算的floor不同 | **已报告跨会话复核通过** | 不得对裁剪ROI重新估计背景阈值后冒充全幅生产掩码 |
| F3 | 掩码`93179/104192=0.894300906`，无效像元11013保留复NaN；有效`|C400|`中位约`0.00659665`，均值`0.0239810`，最大`0.9018655` | **接受表报算术，原像元值仍由工作站归档** | 最大0.9可能由低背景、非平稳和背景干扰放大，绝不是90%粒径可信度 |
| F4 | 有效像元中`82749`个的`|C400|≥0.001`，即有效区的`88.80649%` | **幅值固定门限不具有颗粒识别资格** | 不能把这82749像元报告成82749颗粒或显著检出 |
| F5 | 400 Hz bin在所选41×41 ROI的`mean|X|=0.1625668440`；六邻频点中位`0.1287806989`，比值`1.2623541` | **频谱局部增强，非因果归属** | 不能证明激励200 Hz的磁颗粒2f响应，不能推导检测FPR |
| F6 | `run_v073_replay_corrected.m`分别两次调用`extract_fft_v073`取400/420，两个调用各算一次FFT，非源码注释所述“同一次FFT” | **轻量流程与成本口径问题** | 同一组原帧是真的，不以此宣布C400数值失败；以后可复用一次频谱计算 |
| F7 | 现有三尺寸、九焦面的**静态演示**Fe₃O₄表在焦面变化下有变号与非单调排序；D100有符号积分严重抵消 | **有限条件下的可识别性风险** | 不可把`zf`扫描解释为真实颗粒的轴向轨迹，也不是400 Hz调制曲线 |
| F8 | 30/60/100 nm均匀/分层历史BEM场缓存存在；`s`不是原BEM `sol`对象，角度重新采样此前不可执行；P0完整三矩阵等价性`2.58848e-7`尚未到`1e-10` | **保留已完成场与历史局部门槛；P0 OPEN** | 不重做BEM，不升级大rule7参考，不能说生产/精细差全来自网格 |

**重要限制**：`v073`的`replay_corrected`可计算FFT，但对本实验的“颗粒存在、磁响应因果、实验几何匹配、绝对直径校准”均尚无可接受的独立验证。原归一化主观测定义不应被事后阈值/孔径调整悄悄替换。

### 固定观测定义（本轮所有脚本必须一致）

设`N=2001`，`Fs=5000`，从排序后第1000–3000帧得到像元强度`I_j(x,y)`，全幅每像元时间均值为`Imean(x,y)`。复数调制对比度为：

```text
k0 = round(400*N/Fs) = 160    # zero-based positive-frequency bin
kMATLAB = k0+1 = 161
X400(x,y) = sum_{j=0}^{N-1} (I_j-Imean) exp(-i*2*pi*k0*j/N)
C400(x,y) = 2*X400/(N*Imean)     # validMask 内；复数，不能仅保幅值
validMask = isfinite(Imean) & Imean > 0.01*median(Imean(Imean>0 & finite))
invalid C400 = complex(NaN, NaN)
primary = abs(C400)
```

时相位的起点、正负号均按原脚本；没有同时保存驱动相位基准时，`angle(C400)`仅供**同采集、同起点**内部空间诊断。原400脚本与420脚本的灰度量不同，**不能将两者通过单一倍率换算**。波长520 nm属于用户确认的真实实验输入；NA1.3、玻璃1.5/水1.33、gap5nm、65nm像元和Fe₃O₄ Querry体材料值仍分别是**演示场景参数/文献材料假设**，不能凭520 nm一致就升级成已验证的真实装置模型。

---

## 1. A：回放证据与正确观测合同收口（零BEM、优先，不盲目重算2001帧）

**放行条件**：固定v073 SHA、工作站原BMP组和`v073_return/numeric/fft400_corrected_full.mat`、`fft420_control_full.mat`、`fft400_corrected_small_roi.mat`实际可读；读取状态而非猜测。保留原v072错维度MAT（`INVALID_FFT_AXIS`），不得覆盖。

**必查项**：

1. 对保存结果和源码建立显式运行身份：完整`2001`帧的文件名/文件字节哈希、排序、ROI全图坐标、图像灰度类型、`N/Fs/k`、有效掩码来源、原脚本SHA、改编纯函数SHA、提取时间维、MAT变量的shape/class/NaN比例；复用原`input_provenance_replay.csv`及其全部2001行。前几和最后几行必须与原索引一致；相同文件名不同数据不可算缓存命中。
2. 直接按表列原数独立验算：有效93179、无效11013、两者合计104192；邻频峰比1.262354；“|C|≥1e-3”的真实82,749像元仅叫`BRIGHT_PIXELS_DIAGNOSTIC`。保留已通过的12点DFT与独立ROI复核记录，**本轮不要求再重复整体DFT**。
3. 核对`extract_fft_v073`原版入口的`N==2001`、端点频率限定、复NaN、阈值与端点频率；其有限支持不视为通用API通过。补一个**不读原帧**的轻量测试：使用已存ROI逐像元重算时仍沿用**全幅**`meanFloor`和`validMask`，不把ROI内部重新求median所得`0.00056919`代替原全幅`0.000117616`。如果需要补统计，按保存的`Xk/Imean/mask`直接计算。
4. 订正“400/420同一次FFT”叙述：原代码每次调用分别执行FFT；只为下阶段新增的邻频缓存另建**同源时序一次计算、多频点提取**接口。不得为了改日志语言再重复一次完整2001帧回放。
5. 建立出错即拒绝的保存/读回测试：相同文件身份但错误时间维、ROI局部阈值、用零填充无效像元、使用错误bin 169作为400、重复贴错行列，均不能进入`PASS`。新表CSV UTF-8无NUL控制字符，所有NaN序列化保持语义。

**失败处置**：缺某个MAT仅补那个阶段；已有完整有效的FFT不重复生成。如真正缺失原始时序/文件哈希，标`EVIDENCE_PARTIAL`，可继续独立小型数学前向任务，不以新输出冒充以前相同文件。

---

## 2. B：从“有400 Hz幅值”到“是否有颗粒相关证据”的有限实验数据检验

**这不是磁性因果验证，也不是正式检测器校准**。只在**同一7.29数据组**内开发性调查，不产生新独立采集。原记录共5000帧，仍严格以已冻结1000–3000的2001帧为主体，不跨到60fps的select2/4/5。

### B0. 预声明ROI，不在邻频结果出来后挑好看案例

根据**现有v073全幅**`|C400|、Imean、validMask`和位置坐标确定最多**8个**41×41固定ROI：

- 1个原图中心ROI（已有2001帧小例，直接复用）；
- 最多3个空间局部`|C400|`热点ROI（明示排除无效/接近掩码边界；中心分离大于固定ROI边长，不能按邻频谱择优）；
- 最多3个按`Imean`大致相当、但`|C400|`较低的对照ROI（仅为`BACKGROUND_CANDIDATE`，不称已经证实无颗粒）；
- 最多1个图像边缘、背景梯度或低光强边界ROI（用于伪影诊断）。

允许个数不足8，必须记录候选排序规则、排除条件、每个ROI全幅坐标、像素有效比例、来源hash及选择前日志；不得为了凑数从图上人工挑“漂亮”颗粒。这样选出的ROI属于**开发性、结果相关选择**，不能重新命名为独立盲测。

### B1. 多频点与背景控制，只有一批原始数据

在这些固定ROI上，从**同一原BMP时序**（或已有完整对应ROI时序缓存）提取`kMATLAB=158:164`邻域和420对照`169`。各频点采用同一时间均值、同一个**全幅**有效掩码和原`2/(N*Imean)`；不得对每个频点重新选ROI或单独改变归一化。

评价并保存：

```text
A_k(x,y) = |2*X_k/(N*Imean)|    # 只对有效像元
Rlocal(x,y) = A_161 / median(A_158,A_159,A_160,A_162,A_163,A_164)
```

若邻域中位为零/非有限，`Rlocal=REL_UNDEFINED`并保留原值和标志，不用`realmin`使它看上去显著。按固定ROI比较局部峰超出、背景区域谱形、空间紧致度、不同位置的相位相干性、低光强相关性、0/255灰度饱和/裁剪情况。空间相位只能是同一采集窗口内相对相位；没有驱动参照，不称绝对磁相位。

对2个时间子段（1000帧与1001帧）可以**仅做开发性稳定性诊断**：以相同物理`f*=399.800099950025 Hz`做显式复数解调，记录各段起止时标、归一化分母、幅相及矩形窗长度；不能分别选各自最近FFT bin后直接比较相位，也不能将这两段当两次独立实验。只允许将整帧公共模态的扣除作为**附加诊断分支**；主C400从不被覆盖。

### B2. 不允许的结论

邻频比、空间峰、相位一致性和时间重现都无法单凭这一组数据证明颗粒身份或磁驱动因果；最终标签仅为`SPECTRAL_EXCESS_OBSERVED`、`LOCALIZED_CANDIDATE`、`BACKGROUND_LIKE`、`AMBIGUOUS`或`INSUFFICIENT_DATA`，不得制定正式FPR/检出率，更不得反演绝对粒径。

**预算**：从原5000帧**最多一次单进程顺序只读扫描**以恢复缺失的ROI时序；最多8个ROI；每ROI最多8个固定频点；最多2个已划定的时间子段；无新采集/独立样本，不输出2001张重构BMP。必须保存ROI时序、FFT与掩码、频点、频谱表、背景诊断、失败记录和SHA；大原始帧仍在工作站，GitHub不发布私人实验图像或可识别原路径。

---

## 3. C：520 nm、真正承接磁材料光学场的**有条件**动态前向（本轮新研究主线）

**目标**：回答“特定运动与背景条件下，静态Fe₃O₄复散射场经时变成像和相同400 Hz提取程序，产生怎样的复调制信号”，而**不是**将静态`C(D,zf)`直接放大成实验`|C400|`。

### C0. 物理模型与不得偷渡的假设

对给定Fe₃O₄材料/几何、真实520 nm波长、指定焦面和**预设**颗粒轨迹`q(t)`，使用已保存的**矢量复场**定义即时强度：

```text
I_pix(t;D,eta) = P_pixel {|E_ref(x,y)+E_sca(x,y;D,q(t),eta)|^2}
I_frame_j = (1/tau) * integral_over_exposure [I_pix(t) dt]
C400_sim = FFT400_normalized_complex(I_frame_j; same N,Fs,mask convention)
```

严格先复场相加、再取模平方、再做65 nm演示像元内积分，随后对强度积分曝光；不可先平均复场再平方，不得删纯散射项、任意对每个D重新缩放散射幅度，不能逐案例选择转置/反相得到“更好拟合”。实际曝光`tau`未知；`tau=0`仅表示理想瞬时采样，`0.1ms/0.2ms`只属**假设敏感性**，不是已知相机曝光。若需要时间变背景，必须另外标注为纯光照伪影模拟，不视作磁驱动。

C的磁场与颗粒力学尚未知，故只允许两种明确标记为**处方轨迹**的光学敏感性实验：

```text
M200: x(t)=x0+a*cos(2*pi*200*t+phi)  # 几何非线性可能产生400Hz二次谐波
M400: x(t)=x0+a*cos(2*pi*400*t+phi)  # 直接400Hz轨迹对照
```

探索位移幅度`a=5 nm,20 nm`，`phi=0`仅作为建模坐标约定；**都不是用户真实测得运动**，也不能宣称真实200Hz交流磁场必然让颗粒以此方式运动。真实磁偶极驱动、磁力、布朗轨迹和轴向高度在没有证据前均不纳入已验物理链。

### C1. 复场平移资格：前置不通过则停止物理光学动态分支

重用已有Fe₃O₄ **D30、D60、D100** 三尺寸`1444/rule3`精细分层系统和固定法向照明、平整玻璃/水层。只考虑保持颗粒到界面间隙不变的**横向平移**，不是改变高度。理论上平层与法向均匀照明下，移动散射源可在相应角谱/成像域处理；但旧金球的平移测试不能自动认证新Fe₃O₄所有场。

1. 查看真实`sv.far`、`sv.lens`及`render_system`接口和先前横向平移回归；在Fe₃O₄ **D60,zf450**先验证可以从保存的复场**而非BEM `sol`**生成不同`x`的散射光场和不变的参考光场。不得改写`cfg.particle.xy_nm`后仍使用未改变的旧far就宣布“已移动”。
2. 比较连续平移的两种独立实现/已冻结有效算子，或用直接复场角谱相位与像面正确坐标哨兵对照。必须遵循冻结**IDENTITY轴**，不做逐位置的转置/幅相自由对齐。
3. 如果实际对象不支持可信平移、或验证失败，记录`PHYSICAL_FORWARD_NOT_EXECUTABLE_FROM_S_CACHE`，**不新增BEM**也不拿平移静态强度图替代正确复场。可执行下阶段仅限单独的`ANALYTIC_SIGNAL_OPERATOR_FIXTURE`（例如全场光强调制），不能贴标签`Fe3O4_DYNAMIC_PHYSICS_PASS`。

### C2. 有界运动前向计划：不逐帧求BEM，不逐帧完整渲染

前置通过后，只取演示参数`D=[30,60,100] nm`，`zf=[450,550] nm`，两个运动类型M200/M400，两个预设振幅5/20 nm，共**3×2×2×2=24个时域轨迹条件**。原有`D/zf`静态图与复场可匹配即复用；不同焦面不是高度运动。

**高成本上限**：最多用`x=[-20,-10,0,10,20] nm`固定位置的复光场锚点（6套D/zf×5=30侧render），外加`x=[-5,5,-15,15] nm`的最多24个**只做留出误差比较**的直接光场render，**本轮最多54侧render（新增BEM 0）**。角度、Bessel、q和65 nm物理像元全部保持冻结1444精细设置，不得用修改镜头/网格给运动插值擦边通过。

- 在锚点之间对**矢量复场**而非有符号强度作有界插值；留出位置验证复场/强度相对像元L2、中心与41×41积分**绝对差**，并公开错误时的条件、分母与掩码。新增`0.001`复场/强度插值相对指标可用作**本轮预先声明的工程研究门槛**，**不是历史已冻结的2% P/R门槛**；数值过大即只保留方法开发数据，不继续认定时域结果为物理准确。近零中心量与有符号积分单独报绝对差，不能用很小的百分比掩饰抵消。留出不具全域收敛保证。
- 如果已有可信的连续平移光场求值器可直接算所有轨迹点，可按其真正调用次数扣除锚点预算；**任何调用BEM solve即停止并计成本**，不能称之为零BEM。
- 根据处方轨迹在线构成`2001`帧的**强度时序**，尽量流式累计FFT或块级输出，而不是重复2001次完整`render_system`。每轨迹至少保存`C400`复系数41×41、时均、掩码、时间起点、`D/zf/a/f`、阶段使用的角谱/插值误差证据和一小段可复核帧。
- 以原`extract_fft_v073`的**N=2001、Fs=5000、400目标频点**实际跑时序。选择2–4个样本像元，用独立显式DFT核对输出，沿用本轮已知数值容差`relative<1e-5`或`absolute<1e-7`、相位只对足够非零分量检查`<1e-4 rad`；这些只是FFT算术检查，不是磁实验验证。
- 对`M200`不得预设400分量一定非零或一定与D单调；应保留产生二次谐波的光学非线性项并测到什么报告什么。对于`M400`也不能把处方位移幅度当已知实验运动幅度，**不把三尺寸结果强制拟合成校准曲线**。

**曝光诊断**：仅选择`D60,zf450`的`M200/M400 × a=5/20`四种情况，另分别比较假设`tau=0.1ms`与`0.2ms`（共最多8个额外时序评价）；其余24条首先采用`tau=0`理想采样。无实际曝光元数据时，任何tau曲线仅为假设范围，不计做实验误差界。另允许最多2个“无颗粒、全场光强调制”解析负对照，用以说明400 Hz背景也能产生FFT峰。**总计≤34条时序评价**。倘若受限不执行完毕，逐项状态、资源和原因必须列出，不从成功几例推断全体。

### C3. 定量结果与不可识别性，而非仅报漂亮的C400图片

每种轨迹至少报告下列参数-结果：

`D_nm,zf_nm,material_source,lambda_nm=520,trajectory_type,amplitude_nm_assumed,frequency_Hz,exposure_s_assumed,render_source_hash,source_system_hash,validation_status,absC400_center,complexC400_center,ROI_normC400,ROI_valid_fraction,kinematic_interpolation_error,FFT_DFT_error,flags`。

建立**仅限这24个探索点**的变动与混叠表：不同D而不同a、焦面或驱动模式能否产生近似幅值；计算固定其他参数时D差异、改变a或zf造成的变化。近零与多解明确标`NOT_IDENTIFIABLE_UNDER_CURRENT_NUISANCE`。任何结果不得推出实验真实位移值、真实磁化动力学、正式粒径Bias/RMSE或绝对D；三尺寸和两个焦面不构成连续域单调与独立留出。

**失败处置**：物理平移接口或样例验证未通过，则**不开启24轨迹全批**，也不因此新授权BEM；先完成B和下面D的独立工作并返回`BLOCKED_BY_FIELD_TRANSLATION_VALIDATION`。

---

## 4. D：物理输入差距与后续正式标定的前置判定（不扩大采集）

逐项真实登记`value,unit,source,source_sha256,status,uncertainty`：

| 参数 | v073可接受状态 | v074必须遵守 |
|---|---|---|
| 激光真空波长 | **520 nm，USER_CONFIRMED** | 进入实验合同，不能再标演示-only；但不自动证明其他光路与演示一致 |
| 相机采样频率 | **5000fps，原脚本与所报200μs时间戳一致** | 本7.29批次使用；未来数据逐批核对 |
| FFT主目标 | **400Hz（实际399.8001Hz）** | 正式主观测：复归一化C400及其模，420仅对照 |
| 真实曝光时间/快门时序 | **MISSING** | 不能把200μs帧间隔当曝光，也不能继承金球1ms |
| 物镜NA/总放大倍率/物方像元 | **UNCONFIRMED** | 历史250×及56nm/px由轨迹/推断得出，未独立确认；演示65nm/px不得当实验值 |
| 磁驱动频率、方向、相位参照 | **MISSING** | 历史200Hz/2f400作为线索，不是该帧批次同步驱动已证实 |
| 颗粒批次几何、核壳、光学n+ik及高度 | **MISSING/文献探索** | Fe₃O₄ Querry `n=2.349+0.083i`只作520nm体材料演示，非该批次实测 |

此阶段可只读查本机以前保存的相机元信息、实验记录、光路报告、用户已有文件，不联网猜参数；没有即标缺失，无需用户此刻再解释整个工程。形成`physical_input_readiness.json`，按物理上真正缺乏的条件列下一轮所需最少信息，**不让“用户未给齐参数”自动造成无限金球扩算**。

---

## 5. E：P0独立安全支线（继承已有预算，不挪动磁颗粒主线）

只在确认没有生产高内存BEM竞争、无活跃未完成任务、进程PID/命令行和用户权限清楚时，按历史剩余额度最多执行**一轮只记录的被动Hook**；目标为`galerkin.pot1.duffy1/eval2`实际是否命中、数组shape/dtype、pair计数、栈和预分配内存。**禁止按历史PID乱杀**。若不满足安全前置，则本轮直接`NOT_RUN_RESOURCE_GATED`并且不消耗Hook额度。

冻结P0门槛仍为同一离散问题`blocked/unblocked`的**direct/reflected/total分别Frobenius<1e-10**；目前历史差`2.58848e-7`，不能用`0.5%`参考增量或shape正确替代。大型rule7 BEM在本轮明确**0笔授权**；真实目标磁颗粒rule3的有效场与P0应按共享实现的真实影响范围隔离。

---

## 6. 总预算与阶段放行顺序（不因版本号增加清零）

| 项目 | v074上限 | 预算解释 |
|---|---:|---|
| **任何新BEM求解**（金或磁） | **0笔** | 已有30/60/100nm均匀/分层结果不因交接重新求解；rule7不放行 |
| 新真实采集/新噪声批次/新D节点 | **0** | 仅对现有7.29一批数据和既有场开展诊断 |
| 原实验BMP再次只读扫描 | **最多1次完整的2001帧扫描** | 只为最多8个固定ROI补时域/邻频缓存；已有缓存即扣除，不算新独立样本 |
| 实验ROI | **最多8个41×41 ROI** | 开发性选取，含中心及背景对照，不作独立盲测 |
| ROI频率 | `k=158:164,169`最多8个 | 固定频点，同一全幅掩码和归一化 |
| 新Fe₃O₄光学位置**侧render** | **最多54次**，先1例验证后扩展 | 30个锚点+24个留出（已有匹配缓存扣除）；必须不调用BEM |
| 受约束处方运动时域评价 | **最多34条** | 24主轨迹+8假设曝光敏感性+2无颗粒光调制负对照；必须可流式计算 |
| P0被动Hook | **继承原最多1轮** | 只安全诊断、目标路径需确认；不批准大型参考 |
| 全部原金球R2–R6及历史噪声 | **0新增** | 复用，历史失误不以补跑成绩改写 |

**自动推进规则**：A通过后优先B；C的合法复场平移前置和B可以并行进行纯读分析，但工作站高内存/同MATLAB会话互斥时串行。C0/C1不通过只停止C2/C3，A、B、D、E可继续；下一步不再等ChatGPT发起每一个计算。对任何NOT_EXECUTABLE给出可最小复现的真实失败和依赖关系；不得用没有验证的插值、物理参数自由缩放或修改标签凑成功数。不得追加预算或降低2%/1e-10原门槛。

### 6.1 本轮禁止的“漂亮但不严谨”的输出

- 从`|C400|=0.9019`或400 Hz邻频增强26%推导直径、检出率或磁响应强度；
- 将静态`C(D,zf)`或者中心/面积积分直接乘未知比例因子拟合实验`|C400|`；
- 把焦面变化当轴向轨迹，把Fe₃O₄文献体材料当样品批次实测；
- 用目标频率固定为400 Hz便宣称该7.29批次受到了200 Hz磁场；
- 在没有验证Fe₃O₄有效复场平移时用图像整体移动冒充物理模拟；
- 把不同孔径、D、a、曝光的相对误差直接相加或按样本挑好结果；
- 按`|C|>0.001`将大批像元称为粒子，更不把它们当作R5金球检测验证样本；
- 为了P0或新动态前向清空其他会话、重新生成已有BEM，或把不可运行模块写成PASS。

---

## 7. 一个ZIP + 可读分支：最终交付与审查链

输出**唯一**`iscat_v074_return.zip`，从运行真实产物打包，完成后在`v074`可读分支发布非敏感必要文本和小数值样例，默认不公开私有实验原BMP、批次私人路径、完整敏感帧。建议目录结构：

```text
iscat_v074_return.zip
  00_README.md
  00_全部文本汇总_v074.md         # 本轮真实摘要，不能复制陈旧v059全文充当新证据
  00_Codex_v074_执行指令.md
  status.json / review.md / active_observable_contract.json
  tables/
    v073_replay_arithmetic_audit.csv
    v073_array_and_source_inventory.csv
    roi_selection_frozen.csv
    roi_neighborhood_400_420.csv
    roi_time_stability.csv
    roi_background_artifact_diagnostics.csv
    translation_preflight_and_holdout.csv
    synthetic_motion_plan.csv
    dynamic_C400_observables.csv
    dynamic_nuisance_identifiability.csv
    physical_input_readiness.csv
    p0_hook_status.csv
    task_execution_cost_ledger.csv
  source/
    ... actually executed revised/proposed extractor code, ROI scorer,
    translation/physical time-forward implementation, hashing and unit tests ...
  numeric/
    ... verified small ROI traces, 400/neighbor complex arrays,
    translation sentinel, selected time frames and dynamic C400 examples ...
  logs/
    ... original MATLAB stdout/stderr, errors, source versions, stop reasons ...
  history/
    ... previous v072 wrong FFT-axis artifact status, v070 unpersisted comparison history ...
  manifest_sha256.csv
```

至少包括：源文件与输入hash，使用的精确系统`sha256`、每项实际`D/zf/x`、`ntheta/nphi/ntab/q`、每时序的`N/Fs/k`、全部有效/无效掩码、原数组shape/dtype/hash、外部真实实验输入状态、关键ROI完整少量复时域/频域数据。大文件只在工作站时登记实际路径、变量、shape、dtype、sha与`workstation_only`，不要声称它在ZIP里。**发布后固定提交SHA并回读审查核心文件**，从未验证原数组时不说“独立复核了全部物理像素”。

统一三类状态：`execution_status`（NOT_STARTED/RUNNING/COMPLETED/FAILED/INTERRUPTED/UNKNOWN）、`validation_status`（PASS/FAIL/INDETERMINATE/NOT_EVALUATED）、`evidence_status`（COMPLETE/PARTIAL/MISSING/CONFLICTING）。正式磁测径相关冻结字段必须保留`calibration_valid=false`,`experimental_validation=false`,`detection_validated=false`,`single_particle_diameter=NOT_ESTIMATED`直到有对应真实校准和独立验收；解析运动fixture/P0成功绝对不能覆盖这些字段。

**连续执行结束条件**：所有前置允许、预算内的任务完成后统一交ZIP。依赖分支阻塞时保存最小复现并继续独立分支。无需每步向GPT等待审批；若要新增实际材料BEM、正式样品粒径库/校准、噪声统计或改变物理/统计门槛，必须作为**下一轮明确新授权**，不静默扩算。

---

## 8. 证据索引：固定提交内的真实原始来源

审查目标：`https://github.com/yyyyzoey/iscat-handoff/tree/7cee6972be5c0e361820f737093148ca6c9f4e17`

| ID | 固定源码/表格/日志 | 直接支持的范围 |
|---|---|---|
| S01 | `status.json`, `review.md` | v073执行者报各阶段PASS/OPEN及明确未称实验验证 |
| S02 | `source/extract_fft_v073.m` Git blob `d0d165d2a739f27c226184fe054f1a7932d402a1` | FFT时维检查、N固定、bin、复NaN掩码与归一化公式 |
| S03 | `source/run_v073_replay_corrected.m` Git blob `7088af0d96522a595be04ba491172a68f2f1bf39` | 7.29组两路同样帧源、两次FFT调用、DFT样点选择、源帧处理与小ROI保存 |
| S04 | `tables/fft_replay_direct_dft_checks.csv` Git blob `d76475929e1168e7646b2e85808c44b7a28b1334` | 12点复系数误差（含两个零值角像元） |
| S05 | `tables/fft_replay_direct_dft_checks_recheck.csv` Git blob `d6c63555b81f2b56a6812b7266aa51e94d4683c7` | 独立会话41×41局部DFT和归一化读回，局部与全幅floor差异 |
| S06 | `tables/fft_mask_and_quality.csv` Git blob `9d1488e7b29197dbd4dbcb97754091c78356300a` | 93179/104192、有效/无效数量、幅值统计、82749个超过0.001的像元 |
| S07 | `tables/fft_spectral_neighborhood.csv` Git blob `1cf07c9f2942b2d2e2d63d383ca093a2c7ca625c` | 400频点与6个邻频点的有限ROI统计，不含磁因果识别 |
| S08 | `tables/input_provenance_replay.csv` Git blob `3300d487d0c6c052e5483281d3db10aadf5b713a` | 2001帧序号、文件名、单帧字节哈希与来源 |
| S09 | `tables/fft_axis_negative_tests.csv` / `fft_fixture_corrections.csv` | v072错误FFT维与v073补齐的数值测试 |
| S10 | `experimental/observable_contract_v073.json`, `experimental/experimental_inputs_v073.json`, `tables/physical_input_gap.csv` | 400Hz主观测及520nm用户确认；其他实测输入缺失 |
| S11 | `numeric/numeric_inventory.json` +树中小MAT与工作站缓存清单 | 小数值可下载存在，大FFT全场只在工作站；不能据清单自称逐像元独立验证 |
| S12 | `tables/v068_27condition_clean.csv`, `v067_27condition_k2_fixed.csv`, `controlled_comparisons_v071.csv` | 有限静态场与后处理数字；不构成400Hz磁尺寸响应 |
| S13 | `tables/p0_hook_actual_state.csv`, `logs/v073_return_process_cleanup_record.txt` | P0未做、旧等价性开放、严禁未经确认杀旧进程 |

在本轮用这些真实来源完成工作；不得从摘要猜测缺少的原数组、运动幅度、曝光或颗粒批次光学常数。

**把这一段给Codex即可**：请完整执行本v074唯一指令，先对v073正确FFT和归档做最小核验，再利用既有7.29一组数据开展最多8个固定ROI的400Hz频谱/背景资格检查；若Fe₃O₄复场平移被真正验证，从既有520nm场完成最多34条有界处方运动时域前向，绝不新增BEM。不要把解析轨迹当真实磁响应或静态C当FFT标定。P0只在安全前置满足时使用剩余被动Hook。所有前置满足的独立任务连续执行，失败按依赖停分支，最后统一返回一个ZIP和GitHub可读v074分支。
