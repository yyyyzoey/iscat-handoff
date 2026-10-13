# iSCAT v076 唯一连续执行指令：v075审查、物理中心ROI纠偏及400 Hz动态谐波真实性验证

> **性质**：这是ChatGPT对v075固定提交的源码、表格、日志进行审查后发出的**下一轮Codex执行授权**；它**不是新仿真已经完成的证明**。
>
> **固定审查对象**：`yyyyzoey/iscat-handoff`，`v075` commit **`edb36dddf1b855063f0aa2491f589d5aef13e006`**。新工作产物请提交新的`v076`分支，不静默拉取移动HEAD。
>
> **执行方式**：一次接收本指令；Codex对全部前置已过、输入齐全、资源允许、预算内的独立任务自动连续执行，无须每步等待GPT。失败只冻结受影响分支；不能将未运行/无法读取/统计标签PASS转成物理验收PASS。最后仅交一个ZIP和可读GitHub分支。
>
> **研究定位**：用户确认真实激光真空波长520 nm；正式分析定义为400 Hz目标、实际399.800099950025 Hz的**归一化复调制对比度**`C400=2X160/(N Imean)`，主幅值为`abs(C400)`，并保存复相位。实验`N=2001, Fs=5000 fps`。现有Fe3O4 `n=2.349+0.083i`（Querry 1985）、演示65 nm/物方像元、NA1.3、玻璃/水、5 nm间隙、假设横向运动**尚不是被独立确认的真实实验光学/磁动力学**，绝不可出具单颗粒绝对粒径或有效标定。

---

## 0. v075固定提交审查事实、判定与遗留预算

| ID | 证据位置 | 本次真实核查结论 | 保留/限制 |
|---|---|---|---|
| A0 | `source/position_key.m`, `source/run_v075_A_fixes.m` | 原`makeValidName`将±10 nm映射为相同字段；显式`XM/XP`键在30个配置唯一 | **接受确定性键冲突修复**；仍需与实际文件内容、D/zf/x确认 |
| A1 | `v075_holdout24_corrected.csv`, `run_v075_B_holdout24.m` | 24/24行`Esca_relL2_full`介于`0.0008748895`—`0.0008833604`，全部`<0.001` | **接受六组D/zf、±5/±15 nm的有限离散场插值门槛通过**，不推导连续区间全域误差界 |
| A2 | `v075_roi_spectral_corrected.csv` | 8个ROI、六邻频确实重导出，HOTSPOT1 `Rlocal_median=1.51054178`，有效像元`>1.5`占`0.502736` | 接受开发性频谱比较；不声称颗粒身份/磁响应因果/独立检测率 |
| A3 | `v075_dynamic_C400_corrected.csv`, `run_v075_C_dynamic_redo.m` | 24条处方轨迹与8条曝光CSV已经生成；但是其`roiBlocks`精细场裁剪起点=64，而正确中心映射应为61 | **撤回v075动态中心量的数值验收资格，待重新居中**；不撤销原始复场缓存 |
| A4 | `v075_independent_recheck.csv` | 发布的该CSV实际为**8条**核验记录而非status称“9/9” | 订正文字和实际样例覆盖；原独立会话重聚合不能证明没有ROI坐标错误 |
| A5 | `v075_exposure8_corrected.csv` | 八行标量比值复算一致；实际范围`−0.0580%`至`−1.0328%`，并非status所称`−0.06%`至`−0.86%` | 接受算术，重做中心纠偏后再评价物理/数值意义 |
| A6 | `v075_negative_controls.csv`, `run_v075_neg_controls.m` | `expected_absC400_with_leakage`写的是未考虑泄漏的调制深度`m`；通过判据却允许`computed/m=0.985..1` | 这不是与准确解析泄漏参考的严格验收；需修合同、原表保留为历史 |
| A7 | `v075_motion_plan_and_gate.csv` | 六行的`trajectories_recomputed=2`只是运动**类型**数；每D/zf实际为2种类型×2振幅=4条主轨迹 | 订正任务含义，不再混记唯一轨迹数、时域评价数、边界解数 |
| A8 | 历史P0/实验物理输入 | P0 blocked/unblocked `2.58848e-7`，未过`1e-10`；激光520 nm已确认，曝光/NA/实际物方像元/驱动/颗粒批次等仍不完整 | P0与主线按真实依赖隔离；无rule7授权、无磁实验粒径标定 |

### 核心新增问题B0：41×41动态ROI存在**确定的3个精细子像元偏移**

已发布源码`source/run_v075_C_dynamic_redo.m`（沿用v074的`roiBlocks`）写：

```matlab
q=5; H=size(E,1); Np=H/q; c0=(Np+1)/2; % 65x65 / q5 / H325 => c0=33
 i0=round((c0-20-0.5)*q)+1;           % round(62.5)+1=64
bi=E(i0:(i0+204),i0:(i0+204),:,i);  % 64:268，大小205x205
```

冻结正式41×41**物理像元**ROI为完整65×65的第`13:53`像元，按逐像元连续5×5子像元映射到完整325×325精细格应为：

```matlab
physical_indices = 13:53;
i0 = (physical_indices(1)-1)*5+1; % 61
fine_indices = 61:265;                 % 精细中心(61+265)/2=163
```

原裁剪的精细中心为166，偏移3个子像元。若`render_system`实际网格确认为65 nm物理像元、q5，位置偏移`3×(65/5)=39 nm`。**必须在工作站通过`fine_x_nm/fine_y_nm`和真实`pixel_mean`实现核实该坐标映射**；如实际实现非上述直接连续分块，保存真实坐标并使用映射表，不允许从硬编码推断后立即替换。不同ROI会显著影响中心像元的奇偶对称响应及200/400 Hz谐波。此问题**不改变v075对全场`Esca`的24行holdout门槛**，但污染了原v075动态中心值、ROI范数和合成曝光值，必须重新后处理后才可用于任何动态规律讨论。

### 核心新增问题B1：M200的“介于a²与a⁴”解释在数学上错误

`v075_dynamic_C400_corrected.csv`中固定D/zf将振幅`5→20 nm`（倍率4）：
- M200在六组条件的`absC400_center`倍率约`8.8619—9.2956`，有限两点幂指数`alpha=log(ratio)/log(4)`约`1.574—1.608`；
- M400约`3.9589—4.0429`，alpha约`0.993—1.008`。

真正的`a²`和`a⁴`随振幅×4应分别放大16和256倍；8.86倍率**介于a¹与a²之间**，非a²和a⁴之间。独立复核`run_v075_verify.m`却将`q200>4&&q200<32`标为`M200_scaling_superlinear_between_a2_and_a4`，该名与门槛均错误。重算中心后必须重新计算这些倍率，并分离**真实运动200Hz基频泄漏到400Hz FFT-bin**与光学非线性产生的真实2f成分。不能仅凭一个频点的模值宣称已证明2f物理机制。

### 核心新增问题B2：旧留出强度ROI不是41×41物理像元

`run_v075_B_holdout24.m`中的`roiD=ItD(Cm-20:Cm+20,Cm-20:Cm+20)`取的是**41×41精细子像元**（在q5时仅覆盖约8.2个物理像元边长），`S_area_absdiff`只是此区域的原始强度求和差，没有统一为以前的65nm像元下的**41×41归一化对比度面积积分**。只可保留为历史小精细窗口诊断，不可给它换名字解释为正式相机ROI的`S_area_nm2`。新阶段需要同时算冻结41×41物理像元的`C`、强度、积分和零信号差，实际用`pixel_mean`与`Iref`归一化。

### 核心新增问题B3：状态/源码/缓存的有效性检查不得含空真值

`run_v075_C_dynamic_redo.m`仅遍历`fieldnames(holdData)`判断全部`PASS`，**没有在该放行点断言恰好24个唯一、匹配D/zf/±dx的记录**。空结构会让`allPass`保持true。v075发布表恰好24条、有数值通过，这不意味着软件守卫逻辑没有缺陷。新放行必须按**精确24键集合**验证，不接受无记录/缺对称侧/过期哈希通过。

---

## 1. 阶段A：不增加BEM的身份/坐标/门槛预检（先于所有新动态评价）

**[目标]** 真实恢复30锚点、24 holdout和两个现有焦面的时域配置；核准中心ROI与物理坐标；建立失败即停止的自动断言；不得用重跑BEM解决缓存问题。

**[执行]**

1. 冻结v075上述commit；读取`v074_return/numeric/render_cache/`30个已带符号文件、`v075_return/numeric/render_cache/`24个holdout文件、`v075_return/numeric/v075_holdout_data.mat`、原30/60/100 nm精细分层`s`、`render_system`/`pixel_mean`函数源码与`fine_x_nm`。每个位置缓存必须检查D、zf、带符号x、材料、λ、ref/far、q、网格和真实SHA256。**不是有文件名就命中**。
2. `position_key()`必须显式拒绝碰撞、非有限、未经许可的D/zf/x；在30状态集合测试唯一性和正负反向回查，不只测试键字符串。用户不要求改源库物理公式时，不准修改作者NANOBEM基线。
3. 冻结64:268作为`LEGACY_SHIFTED_ROI`只做对比；从真实坐标确定`PHYSICAL_CENTER_ROI`（预期精细61:265）；保存`i0, i1, center_fine_index, origin_nm, q, pixel_nm`和正反向映射。比较中央像元在原65×65图`C(33,33)`与正确细格聚合后第21×21像元的对比度，在`x=0`分别抽取D60/zf450、D100/zf450；通过原同一路径归一化的数值差必须以事前写定工程门槛评估。**建议数值等价门槛**绝对`≤1e−6`且对非零阵列相对展平L2`≤1e−6`，若实现的浮点精度/精确物理模型不支持，报告真实误差和原因，不能自行降低门槛后显示PASS。
4. 用已保存的±10 nm状态核对图像质心坐标：旧`0.1525954`是**65nm物理像元**单位，换算应为9.918701 nm而非1.98 nm。必须从实际数组复算及核查轴正方向，硬编码旧值不是物理验证。`Eref`应按原物理假设不随平移变化。远场相移法已有质心方向哨兵，但先前周期DFT像面移位验证失败，因此**不可以仅凭单位修复把独立复场等价性标PASS**，使用状态`SENTINEL_CONSISTENT__INDEPENDENT_FIELD_VALIDATION_OPEN`。
5. 加入负向单测：3个子像元偏移必须导致正式ROI身份/中心校验FAIL；24 holdout缺任何一行或任一负位置、锚点hash改变、`+10`误读作`−10`、只有legacy64:268图像应被拒绝。保留日志与最小复现，不清空旧缓存凑PASS。

**[放行]** **真中心坐标映射、完整30/24输入身份、负向拦截通过**后，B/C可执行。若渲染/像素汇聚关系与当前假设冲突、不能证实坐标，则停止物理动态新结果，只开展其它独立的数学漏频/实验ROI审查。

## 2. 阶段B：正确居中的41×41相机ROI与原24行holdout后处理（零新增位置render）

**[目标]** 从缓存中的**全幅**直接复场/插值复场重新抽出对应的205×205精细子像元，再通过q5像元强度积分获得41×41物理像元；保留原全场场门槛不动。

**[要求]**

- 对每个D/zf与±5/±15 nm，从24个已有全幅`Es_direct / Es_interp / Eref`或相应原MAT提取正确ROI。保存复场阵列、强度/纯散射/干涉项、像元坐标和SHA；不能只从v075旧表重命名获得新验证。
- 在每个子像元先进行`I_ref=|Eref|²`,`Isca=|Es|²`,`Iint=2Re(conj(Eref)Es)`，再按原`pixel_mean(...,q=5)`汇聚；计算`C=(Isca+Iint)/Iref`，必须数值闭合实际`render_system`原contrast。不得先对复场求像元均值再平方；不能将`Iint`称为吸收。
- 冻结41×41物理像元的展平L2，中心对比度`C(21,21)`，有符号面积积分`S_area_nm2=65²*sum(C(:))`、正/负积分和绝对差；near-zero强制报告绝对差/符号，不以`realmin`制造相对精度。原`Esca_relL2_full<0.001`保持v075历史通过，不重设/重跑。**不事后新增所有标量都要<0.001的假门槛**；标量的数值资格另按预定意义分析。
- 不能以v075 `Itot_roi_relL2`和`S_area_absdiff`充当这套新物理ROI结果，它们的取域/单位不同。旧表历史保留，另出`v076_holdout_camera_roi.csv`。
- 产物须按每D/zf/Dx完整24行、注明`field_gate_original=true`与`camera_roi_aggregate_status`，缺任何一侧不产生完整PASS。

**[失败处置]** 任何违反原相机汇聚的结果都保留诊断，但依赖其进行的动态响应标记`BLOCKED_BY_PIXEL_GRID_IDENTITY`。只有前置合格条件自动继续。

## 3. 阶段C：从既有30个真实带符号复场锚点**重算原24条处方轨迹+8条曝光**（0新BEM）

**[前置]** 阶段A和B的坐标/完整输入/像元强度放行；所有六组D/zf中的真实复场锚点必须有已验证的正负键；旧v075动态输出仅为历史比较，不可混合新旧中心数值。

**[输入范围不改变]**
- `D∈{30,60,100} nm`、`zf∈{450,550} nm`、`x∈[-20,20]nm`；已有五锚点`[-20,-10,0,10,20]`，直接留出`±5,±15`也有缓存；
- `x(t)=a cos(2πf t)`，`a=5/20nm`，`f=200/400Hz`，相位起点0；`N=2001,Fs=5000`，400 Hz目标取MATLAB bin161；
- 原24条`3×2×2×2`时序评价、原`D60/zf450`的8个`τ=0.1/0.2ms`**合成曝光**评价；**不增新D、焦面、材料、磁学模型和实验独立组**；实测曝光仍未知。

**[处理]**
1. 对每D/zf从全幅锚点重建原复场，并以正确的205×205精细ROI（预期61:265）预计算矢量复场干涉多项式；原错误64:268和纠正版本分别封存标记。处理每帧必须先在子像元形成强度，q5汇聚像元；若`Imean`和有效掩码从仅41×41合成图估计，应标`ROI_LOCAL_SYNTHETIC_MASK`，**不可冒充实验“全幅Imean floor”**。若可从同一已有系统高效计算相应完整65×65时均和掩码，先作最多2条选择条件的全幅一致性对照；不能无记录地增加24次完整大场时序。
2. 预先冻结`source/position_key.m`、真实四维时间轴、完整干涉项、λ520、`q5/65nm`演示几何和原FFT函数身份。相同`D/zf/a/f/tau`只能存在唯一输出；保存`C400`复值、`absC400`、中心物理坐标、完整41×41、Imean/mask、必要的2001帧小像元时序和SHA。
3. 至少在中心像元、两个预先固定的离中心像元比较`τ=0`直接DFT和`extract_fft_v073`，要求与前一版本已声明FFT工程门槛一致：非零量相对误差`<1e−5`或绝对`<1e−7`，相位仅对有定义信号检查`<1e−4 rad`；不得将FFT算术一致宣称为磁学模型通过。
4. 将v075旧值与新值并列，特别是D60/zf450与D100/zf450在M400的中心响应及M200/M400大小排序；无需“让新结果接近旧结果”。**如果居中后与旧结果大幅变化，以正确坐标为准并保留原错误。**
5. 对8条合成曝光，分别记录`τ=0/0.1/0.2ms`、积分区间是`[t_j,t_j+τ]`还是居中、每曝光至少5节点的误差/终端采样假设，另附理论`|sinc(fτ)|`作为**纯正弦**参考；不得把0.2ms帧间隔当成已知曝光。重算范围，不复制status中的`−0.86%`。

**[放行结论]** 原六组都能按相同物理中心得出有来源的时域C400时，才可标`PRESCRIBED_DYNAMIC_FORWARD_NUMERIC_PASS_WITH_ASSUMPTIONS`。如果空间算子只有质心哨兵而无独立物理平移验证，该状态中的物理证据仍应`TRANSLATION_VALIDATION_PARTIAL`。禁止`EXPERIMENTAL_CALIBRATION_PASS`。

## 4. 阶段D：独立分析200→400谐波、频谱泄漏与中心奇偶对称性（零BEM）

**要解决的科学问题**：M200的400Hz观测究竟多少来自**真正的2f强度谐波**，多少来自有限N=2001、f=200/400均不严格落在FFT箱中心而发生的**200Hz基频泄漏**，多少来自中心错位及场插值。本轮不能把“FFT bin161有能量”直接解释为2f主导。

1. 对每个固定D/zf/振幅从**正确中心的同一条时序**生成`X_200`、`X_400`、`X_800`和近邻复系数，保存真正`k0=round(fN/Fs)`与`f_actual`。例：200Hz最近零基bin`k0=80`，实际`199.900049975Hz`；400Hz`k0=160`，实际`399.800099950Hz`；800Hz`k0=320`，实际`799.600199900Hz`。报告“bin80/161”时必须声明零/一基，不虚构同箱精确频率。
2. **固定合成真值**的时间域正交/QR小基拟合，仅作为理论诊断：`1, cos(2π200t), sin(2π200t), cos(2π400t), sin(2π400t)`；对M400另可加800项。分析相应谐波复振幅，**不改变主400Hz归一化FFT观测定义**。当有分段插值尖点/运动高次谐波时须记录拟合残差；有限两点振幅`a5/a20`不能认证连续渐近阶数。
3. 准备至少3项预声明小型解析负/阳性对照（无BEM）：(a)只有200Hz正弦强度，即使真实400Hz谐波严格为零，有限窗的bin161可以有泄漏；(b)只有400Hz正弦；(c)200Hz和400Hz已知相位/振幅混合。所有对照的bin161参考由**独立闭式有限几何级数**计算，而不是再次调用同一个DFT算法后自称独立参考。
4. 数学参考建议：对`j=0..N−1`, `cos(2πf j/Fs+φ)`，独立复系数`X_k=(a/2)[e^{iφ}G_N(f/Fs−k/N)+e^{−iφ}G_N(−f/Fs−k/N)]`，其中`G_N(u)=e^{iπ(N−1)u} sin(πNu)/sin(πu)`（接近零用稳定极限）。如有时均分母，依原N帧`Imean`单独计算，最后`C=2X_k/(N Imean)`。此**完整复表达式**含镜像频率项，优于将单边Dirichlet幅值粗近似当成“精确参考”。
5. 修复v075负对照输出：`expected_absC400_with_leakage`必须输出上述公式的**真正期望值**。源表本身的`0.05`/`0.10`是忽略泄漏的幅值，不可继续叫带泄漏预期。v075的`computed`约`0.04948694657`/`0.09897142015`；独立数学公式应给与其一致的值，除非脚本/时序定义更改。按绝对`<1e−7`或相对`<1e−5`、明确零分母处理判定，而不是宽容的`computed/m∈[0.985,1]`。
6. 按已存`I(x=−5),I(x=0),I(x=+5)`在**物理中心**计算一次/二次有限差分和奇/偶分量，并审视实际镜头/偏振是否足以保证镜像对称；未经验证不能强行设`I'(0)=0`。处方200Hz位移的理论小a展开含`a I'(0) cos(ωt)`和`(a²/4) I''(0) cos(2ωt)`；是否数值主导要结合线性插值、泄漏、有限窗口检验。任何“M200一定二次”“M400一定一阶”“4倍振幅得到8.86倍证明a²主导”的声明必须撤回或通过新数组重新证明。

**允许使用的标签**：`FFT_400_BIN_PASS`, `FINITE_WINDOW_LEAKAGE_QUANTIFIED`, `OPTICAL_2F_COMPONENT_PRESENT`, `ODD_EVEN_MODEL_SENSITIVITY`, `INDETERMINATE`。不要把开发性小型“光学2f存在”冒充真实200Hz磁场驱动2f验证。

## 5. 阶段E：有限尺寸/焦面/振幅的可识别性与实验匹配资格（仅存量结果）

- 在C/D数值通过后，从正确41×41**复数**C400图和主幅值图，分别计算24条条件的成对像元距离（无任意幅相拟合）：`||C_i-C_j||₂/||C_j||₂`、`|||C_i|-|C_j|||₂/|||C_j|||₂`，近零分母单报绝对差；为避免混淆，要注明是否改变D、zf、a或M200/M400，不能称独立统计置信区间。
- 除中心量外保留固定离中心像元以及空间复场形状，探索是否至少在**有限离散参数集**能减少不同D、不同a/焦面给出的近似幅值混叠。不要用3个离散D拟合所谓绝对标定曲线或推断连续唯一性。若无真实运动/相机/材料标定，全部仍仅`LITERATURE_MATERIAL_EXPLORATION`。
- 当前真实实验**已确认**波长520nm、采样5000fps和400Hz观测定义。曝光时间、物镜NA、放大倍率或物方像元、玻璃/水几何、颗粒批次光学n/κ、磁场波形与同步相位、真实运动/高度**未独立确认**。模拟65nm像元/NA1.3和文献Fe3O4不能因波长匹配就变为实验已知。真正将模拟`C400`与实测图比较之前，核查正确的物方像元及曝光和相同掩码定义。
- 8个ROI的v075六邻频表已修复。可复用既有`Ak`进行轻量交叉验证（无BMP重读），并解释HOTSPOT1中位1.5105仍仅开发性频谱候选，背景Rlocal中位约1并不证明颗粒因果。**不为提高显著性重新选择ROI**；不报告FPR/检出率/单颗粒粒径。

## 6. 阶段F：P0独立安全诊断与旧线账本

- 本轮**零新增BEM**，尤其不重跑现有D30/60/100均匀和分层场。历史Mie/BEM四项`<0.02`、分层41×41 Frobenius`<0.02`、P0 blocked/unblocked direct/reflected/total各`<1e−10`继续保持原门槛，不以新插值0.001取代。历史P0仍`2.58848e−7`，未过门槛。
- 仅在空闲、无他人活跃进程和许可证资源安全时，沿用此前尚未消耗的**最多1轮被动`duffy1/eval2`目标路径Hook**（若真实仍可执行）；不重复触发历史OOM，不杀历史PID，不启动rule7大参考；`TARGET_PATH_NOT_REACHED`不能写为`OOM_CONFIRMED`。
- 原A3/R6边界及金球R2–R6均按真实预算和独立前置，**本轮不追加**。

---

## 7. 新一轮预算（明确与历史累计相区分）

| 项目 | v076新增允许 | 预算口径 |
|---|---:|---|
| 新磁/金BEM | **0笔** | 无例外；已保存sol缺失也不能偷偷新求解 |
| 恢复30个原位移锚点 | **0个新render优先** | 读取v074带符号缓存与实际物理字段，缓存错则标阻塞 |
| 重新做原24个±5/±15 holdout直接求场 | **0个新render优先** | v075已耗24次，重算相机ROI从已有24个全幅场读取 |
| 中心ROI纠正后的处方时序 | **最多24次时域评价** | 重做原六组×四轨迹；v075的24次成本不清零 |
| 中心ROI纠正后的合成曝光 | **最多8次时域评价** | 原D60/zf450，τ=0.1/0.2ms；不再增新真实曝光假设 |
| 实验2001 BMP重新扫描 | **0次** | v073/v074有效时序/ROI Ak优先复用；若缺失，单独报告，不静默读全批 |
| 相机全65×65时均/掩码一致性 | **最多2条已有条件的受控时域评价** | 条件已存在；可行性、内存和全幅物理一致性前置通过才执行 |
| 补充分段插值留出（可选） | **最多8个新非BEM直接render** | 只有原已有24点不足以回答明确的数值缺口时，先冻结D/zf/x，再扣账；不是必跑、不是扩展D或焦面 |
| 谐波/漏频解析夹具 | **最多6个小型无BEM夹具** | 包含200-only、400-only和200+400等；沿用主FFT不改观测定义 |
| 新颗粒尺寸、焦面、材料或新相机噪声批次 | **0** | 不开发正式密库/检测/标定 |
| P0被动Hook | **继承历史最多1次，前置安全时才用** | 不重置额度、不放行rule7 |

**历史成本独立保留**：v074原30锚点+24留出（共54唯一位置状态，且另有重试）、v075新的24次holdout，v075的24+8时域评价；不得因为v076数值错误纠偏而将其从账本删除。相同位置不同符号不是同一状态；“缓存命中”必须先做输入、源码和哈希验证。

## 8. 状态机、依赖关系与失败处置

阶段依赖：`A→B→C→D→E`；独立`实验ROI轻量核查`及`F/P0`只按各自真实资源状态推进。若A的映射或B的相机像素闭合FAIL，C/D/E的物理数值分支停止、标`BLOCKED_BY_PIXEL_GRID_IDENTITY`，不以无BEM的解析正弦代替Fe3O4动态模型。若C成功但D真实二倍频贡献仍不可区分，可保留C为**处方前向数值输出**，D为`INDETERMINATE`，不得把模值排序推成磁物理机制。若P0资源不足，记录`NOT_RUN_RESOURCE_GATED`，不挪用主线。

统一三个独立字段：

- `execution_status`: `NOT_STARTED / COMPLETED / FAILED / BLOCKED / NOT_EXECUTABLE / INTERRUPTED`；
- `validation_status`: `PASS / FAIL / INDETERMINATE / NOT_EVALUATED`；
- `evidence_status`: `COMPLETE / PARTIAL / MISSING / CONFLICTING`。

**任何情况下不得声称**`calibration_valid=true`、`experimental_validation=true`、`detection_validated=true`或估算实验单颗粒绝对直径。用户指定的实际520nm只解决波长这一个实验输入维度。

## 9. 唯一返回包及不可省略的检查

请提供一个`iscat_v076_return.zip`，并在GitHub发布可读`v076`分支。必须包含源代码、日志、可独立复核的小数值MAT、状态、成本与真实SHA（大私有BMP/全场MAT仅在工作站清单列身份，不默认公开）。建议：

```text
iscat_v076_return.zip
  00_README.md
  00_全部文本汇总_v076.md
  00_Codex_v076_执行指令.md
  status.json / review.md
  tables/
    v076_coordinate_mapping_and_negative_tests.csv
    v076_holdout_camera_roi.csv
    v076_dynamic_center_corrected.csv
    v076_exposure8_center_corrected.csv
    v076_harmonic_leakage_exact_reference.csv
    v076_odd_even_symmetry_and_derivatives.csv
    v076_dynamic_nuisance_identifiability.csv
    v076_roi_spectrum_recheck.csv
    v076_physical_input_readiness.json
    v076_cost_ledger.csv
    v076_task_status.csv
  numeric/
    v076_center_roi_static_sentinels.mat
    v076_center_roi_harmonic_small_examples.mat
    v076_array_manifest.csv
  source/
    ... every actually invoked revised/verified MATLAB function ...
  logs/
    ... native MATLAB, retries, error calls, hashes, independent session comparisons ...
  history/
    ... v074/075 old wrong center and wrong scaling interpretations, never overwritten ...
  manifest_sha256.csv
```

**发布前硬检查**：24个holdout键与36/30身份关系一致；每个表的字段数、类型、NaN、bool及UTF-8无控制字符；动态24条与曝光8条及条件组合不重复不漏项；小MAT由**独立第二MATLAB会话**可读并重新得出关键中心C400/对比/FFT；正/负键及`61:265`中心映射（或真实验证过的等价索引）必须互查；真正的代码SHA和运行配置实际记录、与主表一致；缺数或不完整的阶段不能PASS。真实本地数据隐私路径仅存用户工作站；GitHub发布对外可读最少源与无敏感小样例。每个完成环节落盘后自动继续下一个满足前置条件环节，无须GPT逐步批准。

## 10. 审查索引（本文件审查依据，可核对的固定提交）

GitHub fixed root: `https://github.com/yyyyzoey/iscat-handoff/tree/edb36dddf1b855063f0aa2491f589d5aef13e006`

- `status.json`，blob SHA1 `b119888a531fbc59b48c5e8ab024a5e63c067a25`：v075执行者报告、历史状态。
- `review.md`，blob `1759b5bb4bcac40ea56a45986e3049319428d143`：本轮工作结论。
- `source/position_key.m`，blob `42d467f4f9c0ef4646dd77635da38e3100ae7d85`：正负位移新键。
- `source/run_v075_A_fixes.m`，blob `257ea190eefd5bfa9fef4e88b1cf88818e9a4f64`：键/位移单位和8 ROI重导。
- `source/run_v075_B_holdout24.m`，blob `841fd0a5ea8521872a1384cfbca1ca076caed75b`：有限24 holdout、取域与单位。
- `source/run_v075_C_dynamic_redo.m`，blob `d8cdb926b52026ef84882ec9a3c625d45d63d2fb`：24+8处方前向，`roiBlocks`索引新问题。
- `source/run_v075_verify.m`，blob `9c733832104031ac298e69c6d54d694d1d8d24ab`：独立会话有限复算与错误M200标签。
- `source/run_v075_neg_controls.m`，blob `472157633cbf81975f094493684d460fc6489d11`：泄漏期待值/接受条件的语义偏差。
- `tables/v075_holdout24_corrected.csv`，blob `dcd8a1a55913931a829a88025a52cac03eac53da`。
- `tables/v075_dynamic_C400_corrected.csv`，blob `0b608cc257d05289e0ad231e809e9be64b00d3ae`。
- `tables/v075_exposure8_corrected.csv`，blob `58259eb004cd2c22ca9a23a4515e7f549ccb72d9`。
- `tables/v075_roi_spectral_corrected.csv`，blob `45f51b0061bcbc629a3a476557aa0d789582785e`。
- `tables/v075_independent_recheck.csv`，blob `105ef6326dbe64bed1df9ceb42306c13eded66a4`。
- `tables/p0_status.csv`，blob `9ecea86f906c44a06069d71c1039a4de9bf5b7d4`。
- 实验观测基础：`experimental/observable_contract_v073.json`、`source/extract_fft_v073.m`、用户已确认的真空激光波长520 nm。原BEM粒径/材料/装置的其余假设沿用历史身份，不因本审查新增实测证据。

**交给Codex时的一句话**：完整执行本v076唯一指令，从v075固定提交、v074/v075缓存接续；先修正41物理像元ROI在q5精细场中64:268→坐标验证后的61:265，重核零位与保存的真场，零BEM重算受影响24条动态C400和8条合成曝光，再分开评价200Hz真正2f谐波与有限窗泄漏；不增加粒径库、不替实验确认未知参数、不降低原门槛，独立支线资源安全时推进，最后统一一个ZIP及可读分支。
