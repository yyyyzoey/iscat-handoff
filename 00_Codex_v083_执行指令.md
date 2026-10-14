# iSCAT / Fe₃O₄ v083 唯一连续执行指令

## 对 v082 的固定提交审查、同一物理中心时序身份纠正、曝光剩余敏感性与无新增 BEM 的空间观测量筛查

> **文件性质**：这是依据 v082 实际源码、日志与结果表制定的**下一阶段执行方案**，不是 v083 已经完成的实验或仿真结论。Codex 应在 Windows 工作站自主连续执行所有满足前置的任务，只有依赖失败的分支暂停；全部可执行任务结束后统一给出一个 ZIP 和一个可读 GitHub v083 分支，不必每一步等待 GPT。
>
> **唯一审查对象**：`yyyyzoey/iscat-handoff` 的 `v082` 固定提交 **`0fbebbb1db863a7ad79081ea470e907b442781d4`**（父提交 `v081@812171a5fbea43c68d1ca93995f876e2fd051e19`）。禁止静默从移动中的 HEAD 获取不同源码；确有修复只能产生新的 v083 源并保留旧代码身份。
>
> **物理事实与范围**：用户确认的真实激光真空波长为 **520 nm**。7.29 实验批次的脚本记录 `Fs=5000 fps`、取帧 `1000:3000` 共 `N=2001`、400 Hz 目标的最近离散频点 `k0=160`（MATLAB第161点），频率 `399.800099950025 Hz`；候选主观测量为复数归一化单边对比度 `Cbin=2 X_160/(N Imean)`，其模为无同步相位参照时优先考虑的量。200 Hz交变磁场频率、14 µm传感器像元、50×标称物镜均属于**有历史记录但最终配置尚未核实**。实验曝光、NA/浸液、额外倍率与真实物方 nm/px、场幅值/梯度/波形/同步、颗粒位置/轨迹和批次光学常数尚未闭合。**65 nm/物方像元、5/20 nm运动、450/550 nm焦面及Querry Fe₃O₄光学常数仍是演示模型假设**。无实验磁场因果证据、校准或真实绝对粒径。
>
> **本轮预算底线**：**新增 BEM = 0；新增光学位置复场 render = 0；原7.29 BMP再次全量读盘 = 0**。必须保留已有正确材料、30个有符号位置锚点、24个复场留出、静态前向和正确中心数组。不得因 v082 报告身份问题重求先前BEM。原静态 `<2%`、位移复场留出 `<0.001`、P0同一问题direct/reflected/total三矩阵Frobenius各 `<1e-10`及现有动态复数代数闭合 `<1e-10` 门槛均不放宽。所有新诊断标准单独标注，不能事后冒充原冻结验收门槛。

---

## 0. v082审查裁决——先保留真进展，再限定结论

### 0.1 可接受的实绩，禁止下一轮退回重算

1. v082新正式数据表经源码和表格复核：`v082_harmonics24_validated.csv` **24行×34列**、`v082_harmonic_parts_long.csv` **96行×13列**、`v082_harmonic_residual24.csv` **24行×14列**、`v082_time_series_identity24.csv` **24行×15列**，四张表数据行宽与表头一致，所需记录真实存在。这与 v081 的 ERROR/空表不同，必须保留。
2. 24例满秩截距首列模型：`rank=9`、`cond≈1.4146`；从实际表重新复算 `Cbin=2Xbin/(2001 Imean)` 与表列值一致；24条`closure_rel`最大约 **`3.9223e−14`**，均满足原 `<1e−10` 数学闭合门槛。M200的12例 `|Cbin|/|C400fit|=0.989512…0.989731`，是现有处方时序的有限窗算子关系，**不是磁场驱动因果证据**。
3. `v082_preflight_and_schema.csv`含**18个数据测试记录**，包括10个负向守卫与6张正式表读回；发布前确认了表长、固定键、编码和字段结构。各有效计算输出保留，不重复原24条QR来凑新版本记录。
4. `v082_weak_center_precision6.csv`给出**6个旧M400/a=5条件×3条数值路径=18行**。插值复场先求强度路径与双精度二次型的Cbin绝对差在这些例子中约`1e−17`量级；单精度路径与双精度路径的**确定性数值差异**约`2.1e−8…5.7e−8`（按表的诊断尺度）。其中D30的双精度信号约`1.7e−9…2.7e−9`，远小于该路径差异。**这些不是统计噪声标准差，更不是实验仪器噪声底**；“10倍”仅是本轮标记相对误差是否适宜解释的诊断规则，不可升级成实验检出门槛。
5. `v082_exposure16_convergence.csv`含**28行=4条纯400Hz夹具+16条新16/32节点评价+8条旧5节点只读记录**。v082确实执行了16次指定的高阶**纯时域**处理，预算已被使用，下一轮不得称“未执行”或重新用这16次余额。纯正弦解析夹具的完整有限DFT预测与求积输出相合，所测试积分规则向sinc收敛；原8个混合处方仅有16→32的有限增量证据，**不构成任意曝光时长、真实仪器或绝对误差上界的认证**。
6. v082将520nm USER_CONFIRMED、5000fps/2001帧 SCRIPT_RECORDED、200Hz/14µm/50× HISTORICAL_UNVERIFIED、65nm和5/20nm SIMULATION_ASSUMPTION、NA/曝光/总倍率/磁场幅值等 MISSING 区分，是正确且必须保留的科学边界。
7. P0 本轮没有启动MATLAB Hook，资源账本`used=0`；历史误差`2.58848e−7`仍未达到每项`<1e−10`。rule7大参考授权仍为零；该独立未完成项不能自动推翻正常的磁材料/FFT后处理。

### 0.2 重大缺口 X1：所谓跨方法“中心时序”实际上混用了不同像元

直接检查本固定提交内的历史生产源码 **`source/run_v076_C_dynamic_center.m`**：正式图像中心采用`cc=o.C_k(ci,ci)`、`ci=21`，但同一例的保存字段却是：

```matlab
% v076 原历史源码（保留原文件作为历史，不覆盖）：
res.(key)=struct(...,
   'tseries_center',double(Ipix(ci,1,1,:)), ...);
```

它存储的是41×41ROI的**第21行、第1列**，而非中心第21行、第21列。另一个小MAT来自`run_v076_D_qr_center.m`中精细`161:165`的真正中心25子像元。v082 `source/v082_evidence.py`第231–234行将二者直接逐点比：

```python
cross = f2[key]['tseries_center'][:]  # v076遗留字段实际是第21行、第1列
cross_max = max(abs(series - cross))
```

实际`v082_time_series_identity24.csv`最大原强度绝对差约 **`0.0079891235`**，最大相对时序L2约 **`0.57875795`**。这不是两种**同像元**数值方法的误差，不能解释为单/双精度、全205×205与25子像元块运算的差异。`v082`主B的24条小MAT满秩谐波**数学结果可保留**，但`A_identity`/跨源一致性的`evidence_status=COMPLETE`必须单独降级为`PIXEL_IDENTITY_MISMATCH__TO_REPAIR`。保留原字段，并在v083派生表明确改名`legacy_row21_col1_series`，严禁旧表静默改值。

**v083必须从已有30个正确位置锚点复场、同一41×41映射重新提取正确`Ipix(21,21,1,:)`，并与小MAT的同一中心时序及`v076_dynamic_center_corrected.mat`中真正的`C400(21,21)`核对。**不新增位置render、BEM或物理轨迹；只是恢复相同旧处方的同像元时域算子。近零量同时用有单位的绝对复差和明确数值精度下限，不能用`realmin`制造巨大相对误差。

### 0.3 其他待修复的确定性/语义问题

- **X2，错误的相位字段**：`source/v082_phase_c_precision.py`用`Cfit, rmsR=qr_fit_C400(s)`求出拟合复数Cfit，却把`C400fit_phase_rad`写成`np.angle(C)`，其中C是**FFT Cbin**。对18行检查均有`C400fit_phase_rad == atan2(C400_Im,C400_Re)`的代数关系。因此该字段是误标的FFT相位，不是拟合400Hz相位。v083分别生成`Cbin_phase_rad`和`C400fit_phase_rad`，从各自**正确**复数对象计算；低于数值分辨尺度则标相位`UNRESOLVED`，不伪装绝对相位意义。
- **X3，截距项的残差闭合公式与文字不完全一致**：`source/v082_evidence.py`计算并输出`X0=coef[0]*G_N(-k0/N)`，文字定义`Xbin=ΣXh+X0+Xres`，但代码`closure_abs=abs(Xbin-Xmodel-Xres)`以及表中的`closure_Re/Im`省去了X0。现有24表中`|X0|`最大约`3.52e−21`（本轮已复算），远小于约`5.11e−15`的最大原始DFT闭合差，因此**不改变当前通过裁决**；下轮直接按已定义的完整复数式显式包含X0，避免再产生语义分叉。
- **X4，数值路径差≠仪器噪声**：v082把三条确定性计算路径的差定义为`path_noise_scale_absC`，这一名称最多只能表达“数值路径差异上界（对所比较的三条路径）”，不是相机shot/read噪声、材料不确定性或观测SNR。D100/a5的双精度信号约`3.09e−7…3.77e−7`大于该路径差异，但这**不能证明实验中可测**。
- **X5，曝光收敛解释需限定**：8条件中最大的16→32幅值差是D60/zf450/M200/a20、tau=200µs的`2.8666925e−8`（相对32节点约`2.4363e−5`）；**最大相对**16→32差则是D60/zf450/M400/a20、tau=200µs的**约`0.00356229=0.35623%`**。该M400/a20/200µs的32节点结果与旧5节点相比约**23.76%**，另M400/a5/200µs相对旧值达约**34.71%**；近零相对值不能被当成真实曝光误差。16/32为有限Cauchy增量，没有独立高阶收敛定理；纯余弦fixture的O(M^-2)不能无条件推广至由分段插值构造的非光滑处方运动时序。
- **X6，完成证据与科学结论分开**：数值模态拟合的满秩及`closure_rel<1e−10`证明规定离散算子的算术正确，**不等于**真实相位同步、200Hz磁场导致400Hz信号、实验噪声模型、光学参数匹配、单颗粒测径或连续域唯一反演已经通过。v082冻结`calibration_valid=false`、`experimental_validation=false`、`detection_validated=false`、`single_particle_diameter=NOT_ESTIMATED`必须保持。

---

## 1. 统一执行规定、独立审查方法与失败状态

- 只读冻结v082原文件，创建v083新输出；源哈希、变量shape、dtype、实际单位、case元数据和物理像元坐标必须一致。严禁把HDF5哈希、字节SHA-256、Git blob SHA-1和拟合序列SHA混用。
- 每个任务分别有`execution_status`、`validation_status`、`evidence_status`、`scientific_scope`；数学闭合PASS与跨源身份未闭合可以**同时**存在，不得用总`PASS`冲掉`PIXEL_MISMATCH`。
- 读取 `v074_return/numeric/render_cache` 原30锚点、`v076_return/numeric/v076_center_roi_harmonic_small_examples.mat`、`v076_return/numeric/v076_dynamic_center_corrected.mat`；可复用`v082`三条小MAT与各张平表。不存在的原始字段必须标`MISSING`，不得根据CSV补造时序。
- 明确`q=5`、演示物方像元65nm、65×65物理网格的物理中心33，41×41 ROI对应物理像元13:53、精细61:265，ROI内中心21/21、整幅精细索引161:165。严格记录HDF5轴顺序与MATLAB存储轴顺序，不能因转置/flatten顺序改变中心。
- 所有新增数学验收在首次运行前冻结绝对量与相对量尺度，**不得**替换原BEM、复场留出和P0旧门槛；“新诊断结果没有量化噪声校准”不得凭阈值自封实验VALID。
- 阶段A未核清正确像元身份，只阻塞依赖其同像元差异结论及空间稳定性阶段；不推翻既有B谐波算术、D曝光解析fixture、E参数来源合同。依赖失败时继续其他独立工作，最后交唯一ZIP。

## 2. 阶段A（最高优先级）：纠正同像元时序来源，零BEM、零位置render

### A0. 单个试点 `D60/zf450/M200/a5` 先验证全链

1. 从**相同**五个有符号位置锚点，使用v076冻结的线性复散射场插值，固定参考场与完整强度`|Eref+Esca(x(t))|²`，按5×5子像元平均形成**物理中心(21,21)**帧强度。以共享函数分别计算：`field_first_double`、`quadratic_form_double`、`quadratic_form_float32`（模拟而非声称字节相同的MATLAB单精度）。同一区域还可以在不申请新位置场的条件下重放正确的41×41块，但本阶段仅需中心25子像元。
2. 对照`v076`小MAT保存的`series`（已知正确中心），并从 `v076`动态图中读取`C400(21,21)`（正式中心复系数）；把历史错误字段`tseries_center`明确标注为`legacy_row21_col1`并单独证明它来自该列。绝不拿错误列的57.9%差当作数值精度。
3. 保存全部2001帧的可读小型NPZ/MAT与CSV摘要、时序SHA、数值路径身份、平均值和复数`Xbin/Cbin`。采用独立FFT和显式DFT交叉验证。单/双精度路径差用复数绝对差先验收；近零时不强制用相对差。先独立新会话读回**一条试点所有数字**，成功后自动扩展至其他旧条件。
4. 必须故意注入`(21,1)`替代`(21,21)`的负向测试，强制触发**像元身份拒绝**；另针对HDF5维度转置、错误ROI精细`64:268`、源SHA不符、数组大小不符建立失败守卫。低成本单元夹具不需要新BEM。

### A1. 对原24条旧处方进行有限同像元数值重构

- 优先对24个已经存在的时序进行**共享中心算子**重构并与v082原小MAT、v076动态图的中心C400比较；每个旧条件最多一次新的正确中心时域**后处理**（不是24个新物理状态）。已存在可信同一数值路径数组则零算重用。逐例保存`cross_source_numeric_compatible`状态，而不是要求MATLAB单精度与Python双精度字节相等。
- 结果分开三种：`SAME_PIXEL_SAME_OPERATOR_VERIFIED`；`SAME_PIXEL_NUMERIC_PATH_SPREAD_REPORTED`；`MISSING/BLOCKED`。如果只验证了六个试点，不得把其余18个自动写成已通过。
- `v083_correct_center_series_identity24.csv`必须有24固定键、物理行列、数据源SHA、两份**正确中心**`Imean`、序列diff、同单位复数`Cbin`差、精度路径、数值解释和状态；旧错误`legacy_col1`另存只读对照。不能只写length/mean/std签收。

**阶段A完成**意味着真正的同像元来源闭合，不意味着任意复场位置插值或实验仪器测径精度已经证实。

## 3. 阶段B：只读保留v082满秩24/96/24数学闭合，做两个小修补

- 不默认重跑24条QR（v082已实际完成且通过），从v082的正式`validated`、`parts`、`residual`表恢复实际物理量；检查固定24×9列基，门槛`rank=9`、`cond<1e8`、`closure_rel<1e−10`，不得事后修改。
- 表内`Xbin`、`X_h`、`Xres`、`X0`全是DFT_count；`Cbin`和拟合`C400fit`全是无量纲**不同算子**，不可将其复振幅或模无依据合并。新`closure`必须按`Xbin−ΣX_h−X0−Xres`输出复数Re/Im，保存原v082省略X0旧列作为历史（其实际最大量约3.52e−21，不足以反转旧代数PASS）。
- 精度表的误标列：正确导出`Cbin_phase_rad=angle(Cbin)`与`C400fit_phase_rad=angle(C400fit)`两个字段，不能像v082源码使用`angle(Cbin)`去填后者。若某路径中心信号相对数值差异不可分辨，两个相位只保存数值诊断、状态为`UNRESOLVED_NEAR_ZERO`，不能写真实同步相位。
- 对每条`v082_time_series_identity24.csv`的`cross_source_max_absdiff`保留历史值、将其语义改为`true_center_vs_legacy_col1`，新同像元身份只从阶段A生成，不得修改历史数据。

## 4. 阶段C：限定数量的空间ROI数值稳健性对照（条件满足才执行）

只利用v074正确30锚点与v076已存在的41×41复C400图，不发起新的位置场render，也不增加D/zf/a/type。若阶段A试点未过，空间对照直接`BLOCKED_PIXEL_IDENTITY`。

固定**最多4个**旧处方条件，先验选择：

| 目的 | 冻结旧条件 |
|---|---|
| 极弱M400中心 | `D30/zf450/M400/a5` |
| 极弱M400另一焦面 | `D30/zf550/M400/a5` |
| 中等M400参照 | `D60/zf450/M400/a5` |
| 较强M200参照 | `D100/zf450/M200/a20` |

- 在相同41×41物理ROI、65nm演示像元/q5和同一参考归一化上，利用已有复场锚点以**有界流式时域后处理**（例如每批≤32帧）构建4张双精度复C400图，保存来源与内存峰值；已有高可信同数值路径复图则直接读取，不因新版本重造。
- 每条件比较单/双精度或历史v076单精度动态图的**完整复图Frobenius绝对差和相对差**、中心复C400、`||C400||_F`、`Σ|C400|`、固定中心附近/离中心空间结构；在尚无标定真实nm/像元时，不能以这4条件做相机尺度认证。
- 该阶段只是演示数值路径敏感性筛查，**不增添新的“所有空间描述量必须<2%”验收门槛**。D30的弱中心信号不作为可靠实测检测极限；数值差小只说明现有计算路径一致，不证明真实光学误差上界。

## 5. 阶段D：保留已执行16次曝光，只对最敏感旧条件做极窄64节点确认

v082已完成8旧条件×16/32节点=16次时域评价，本轮**不重新授权或重跑这些16次**。原8条件和100/200µs仅作为**合成数学参数**，并非用户实测曝光。

仅额外有条件授权最多**2次64节点中点时域评价**，固定为：

1. `D60/zf450/M400/a20/tau=200µs`：v082最大全幅值相对16→32增量约0.35623%，需要检查32→64是否减小；特别保存中心复数**绝对**差和相位，不因近零响应而推论仪器曝光误差。
2. `D60/zf450/M200/a20/tau=200µs`：v082最大的16→32**绝对**幅值增量约`2.86669e−8`，用于较强400Hz响应的对照。

前置：原两份高阶数组与v074锚点身份完整；若资源/许可不满足则该两条`NOT_EXECUTED`，不可伪造。不允许为了追求比率变好继续增加128/256节点或改原τ。即使发现16→32→64变小，也只是有限数值趋近证据；分段线性位移插值的非光滑点不允许无条件套用纯正弦的O(M−2)定理。

纯正弦解析fixture之前已经通过，不能再把`|sinc(400τ)|`当作一般非线性处方整个FFT量的精确衰减。记录复数`Cbin`、幅值、时间窗相位约定、与32/16/旧5节点对比、算力时间和历史额度；不新增运动状态。

## 6. 阶段E：利用既有24张C400图做有物理含义的空间观测候选筛查

这一步只做**有限参数集合的纯代数派生统计**，不产生新BEM、光学位置、运动轨迹、焦面或试验样本。必须先确认v076的24张正确41×41复图形状、字段、掩码与源哈希；不使用v075偏移中心历史图。复图相位在真实实验中没有磁场同步参照时仅`DIAGNOSTIC_ONLY`。

候选观测量固定：
- 中心幅值 `A_center = |Cbin(21,21)|`，并标记已发现的弱M400不稳健条件；
- ROI幅值Frobenius `A_ROI = ||Cbin_ROI||_F`，无量纲；
- 固定ROI幅值和 `L1_ROI = Σ_(ROI)|Cbin|`，无量纲；若报告面积加权版本才乘**演示像元面积**`65² nm²`并注明演示单位；
- 仅作为幅度消除后**形状诊断**的 `shape = |Cbin| / || |Cbin| ||_F`（零范数必须拒绝），不要用自由幅度匹配把它当成已证明的实验特征；
- 有同步磁场参考之前，复图无自由相位对齐的距离仍只作数值开发信息，不视作实测可用物理相位。

读取此前24态/276对中每一态的`D,zf,a,type`，计算每种固定特征的**192对跨D**最近邻与**84对同D**干扰距离/范围；不重新模拟24个物理态或申请新的盲测。数据驱动形状差异和响应幅值由运动未知量混杂的影响要分开呈现。禁止无实验噪声模型便宣布“检出率”“粒径误差”“可辨识阈值”或连续粒径唯一性；示例中跨D幅值图最小对称距离`~0.26465`只能引用为原离散集合统计，不是误差率。

## 7. 阶段F：真实实验参数就绪门与P0独立支线

- 固定真实520nm用户确认，7.29 Fs=5000/N=2001/bin161来自脚本；200Hz交变磁场、14µm传感器像元、50×物镜来自历史记录，仍标`HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP`。新的`experimental_parameter_contract_v083.csv/json`区分`USER_CONFIRMED / EXPERIMENTAL_SCRIPT_RECORDED / HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP / SIMULATION_ASSUMPTION / MISSING`，每项列来源和最后核验状态。
- 真正进行磁场→动力学→成像→FFT→绝对D前仍最缺：**总倍率或标定nm/px、物镜型号NA浸液、真实曝光及触发、磁场幅值/梯度/几何/波形与时序同步、颗粒材料批次与涂层、实际位置/运动机制**。这些目前不能由GPT或Codex凭演示参数补全；用户未提供也不阻挡本轮A–E纯数值工作。
- P0只有原安全门全部通过时才允许使用**继承、未用的最多1次被动Hook**。本轮没有新增被动额度；不能因检测0个MATLAB进程就单独断言许可证安全或必需运行。P0历史三矩阵门槛`<1e−10`仍未过，rule7新大型参考**0授权**，不会为了本轮谐波问题启动高成本BEM或杀死未知历史进程。

---

## 8. v083严格新预算与自动继续规则

| 工作 | 新增/继承上限 | 计账及禁止项 |
|---|---:|---|
| 新BEM solve | **0** | 绝不重做已保存的30/60/100nm均匀/分层系统 |
| 新光学位置场render | **0** | 只用v074已缓存30锚点、v075旧留出 |
| 已有24处方正确中心时序同像元重新提取 | **至多24条** | 条件性重算**旧**2001帧纯时域处理；已保存可信则直接复用 |
| 四张完整41×41 ROI双精度时域复图诊断 | **至多4个旧条件** | 可流式；有相同来源合格缓存则0；不增加物理态 |
| 64节点曝光对照 | **最多2次** | 针对上述事先冻结两条件，属于**v083明示的窄新增额度**；v082已用16次不得清零 |
| 新解析/错误注入小测试 | 最多6项专项新夹具 | 不增加物理条件；基础CSV读回不作为新仿真 |
| 24态观测特征与276对距离 | **仅派生统计** | 不另授权MC/真实样本/校准精度 |
| 新D/zf/a/f/材料/磁场扫描、噪声批次、7.29BMP重读 | **0** | 未取得仪器输入前不扩建标定库 |
| P0被动Hook | 继承最多1轮、安全前置成立才执行 | rule7大型BEM参考0笔 |

**自动执行顺序**：固定源码及SHA→A单case真实同像元证据→A余23条件（能执行的连续做）→B字段与X0修补→C4条件空间试验（依赖A及资源可用）→D2条件64节点（独立安全前置）→E只读特征/参数混杂分析→F资料与P0安全核查。依赖项FAIL只停受影响分支；历史PASS不会因报告错误自动改为物理FAIL；所有前置通过且预算充足的工作连续完成，不必每一步等待ChatGPT。

## 9. 每个新输出必须提供的可复算证据

至少打包一个**真实存在**的ZIP `iscat_v083_return.zip`和一个可读`yyyyzoey/iscat-handoff`的`v083`分支；推荐文件结构：

```text
iscat_v083_return.zip
  00_README.md
  00_全部文本汇总_v083.md
  00_Codex_v083_执行指令.md
  status.json / review.md
  source/
    v083_pixel_identity_repair.py / .m
    v083_harmonic_metadata_fix.py / .m
    v083_roi_precision_controls.py / .m
    v083_exposure64_two_conditions.py / .m
    v083_observable_screen.py
    ...实际执行脚本、错误注入/CSV守卫和依赖身份...
  tables/
    v083_correct_center_series_identity24.csv
    v083_pixel_identity_negative_tests.csv
    v083_harmonic_complex_closure_X0_corrected.csv
    v083_phase_columns_corrected.csv
    v083_fullROI_precision4.csv
    v083_exposure64_target2.csv
    v083_nuisance_observables24.csv
    v083_nuisance_feature_pairwise276.csv
    v083_experimental_parameter_contract.csv
    v083_cost_ledger.csv / v083_p0_status.csv
  numeric/
    ...至少D60/zf450/M200/a5正确中心两条方法的2001点原序列、复DFT和SHA的读回小样例...
    ...最多4个条件的流式双精度41×41复C400样例...
  logs/
    v083_native_or_python_execution.log
    source_identity_sha256.csv
    independent_readback.log
    failures_and_skipped_dependencies.log
  history/
    v082_time_series_identity24.csv                 (不改数值，只读历史)
    v076_tseries_center_col1_bug_source.txt         (明确旧第21行第1列)
  manifest_sha256.csv
```

1. `v083_correct_center_series_identity24.csv`必须**实际读取或重构正确像元**并独立验证，有`case_id,physical_pixel,source_hash,series_SHA,N,mean,complex_Cbin,delta_abs/rel,status,method`。以前`v076_C`错列的原系列单列为`LEGACY_NOT_CENTRE`，不可复用旧证据假装已验证。
2. 谐波X0与相位字段修补必须重新CSV读回确认24个固定键，原B数值门槛不变；不得误将模型拟合复数幅值当FFT离箱测量算子。
3. 曝光对照只交真实执行的64节点输出，未执行明确写`NOT_EXECUTED`；不重新发送16/32原值冒充新结果。实验曝光未知必须一律标`SYNTHETIC_TAU`。
4. 跨D的空间特征只作为有限开发性筛查，没有已冻结的真实相机PSF/噪声模型/幅相参考，**不能输出实验单颗粒直径、校准曲线、误差率或磁响应因果证明**。
5. `status.json`严格分别记录`execution_status`、`validation_status`、`evidence_status`、`scientific_scope`；完整MAT只在工作站时写`WORKSTATION_ONLY`真实路径、shape、dtype和**文件字节SHA-256**。CSV全部按表头/行宽/键/控制字符/单位独立读回。错误与跳过必须保留，不能把计划写成PASS。

## 10. 本轮审查原始证据索引（全为v082固定提交）

| 编号 | 源路径 | Git blob SHA-1 | 审查能支持的范围 |
|---|---|---|---|
| V01 | `status.json` | `634a25ab68bab5c0e1c1e01de63eadc07ff034cb` | v082执行者总结，不替代源码和数据 |
| V02 | `review.md` | `14f25ad7d074dc2b145922d6deea5e016e7d40e0` | 本轮执行者科学解释及未闭合物理合同 |
| V03 | `source/v082_evidence.py` | `e7b27f2069e283898c90fe10bbc799fad57c0a49` | 24/96/24/24计算；对旧`tseries_center`错误同像元比较；X0闭合小缺项 |
| V04 | `source/v082_qf_common.py` | `bd32c5e94b6bb917f03ef9e38f2843b88cd8fea4` | 25子像元中心二次型/复场先求强度辅助算子 |
| V05 | `source/v082_phase_c_precision.py` | `fe51ed7b90c1fe507e2e2df8f8bbd49fca2d60a2` | 6条件×3精度路径；`C400fit_phase_rad`误写FFT相位 |
| V06 | `source/v082_phase_d_exposure.py` | `8fbdc4e669ad0341676f586ecff5b59d93f9f965` | 正弦夹具与8条件×16/32中点曝光评价 |
| V07 | `source/run_v076_C_dynamic_center.m` | `9eb52259f1af0f1ef79675d372c2020379576725` | 真正中心`o.C_k(ci,ci)`；错存`tseries_center=Ipix(ci,1,1,:)` |
| V08 | `tables/v082_harmonics24_validated.csv` | `88fd4a35a12d8feef692473ab14c899184aa8172` | 24条真实主记录、满秩复闭合、单位、旧跨源差 |
| V09 | `tables/v082_harmonic_parts_long.csv` | `7d5ebbe27c4fd781711597d82b49314726398eaa` | 96个有限DFT谐波贡献 |
| V10 | `tables/v082_harmonic_residual24.csv` | `16df52023a61e8dc84388144d773346b0646b69d` | 24条复残差+X0与省略X0的历史闭合 |
| V11 | `tables/v082_time_series_identity24.csv` | `70b71388671f395d8aca914bc0456a3f8f8cf768` | 24条历史错误col1跨源比较，不能当中心数值误差 |
| V12 | `tables/v082_weak_center_precision6.csv` | `e13c58c3f44acecf3e59421c71eaf52338dfda49` | 6条件×3路径数值差与相位标签错误 |
| V13 | `tables/v082_exposure16_convergence.csv` | `0500c71e177ec0efb950a56f158ce2bc18952224` | 4夹具+16高阶+8只读，16/32有限增量 |
| V14 | `tables/v082_preflight_and_schema.csv` | `212d0814a0fee8c0526a7cfe8d0e06a124adc999` | 18条结构/负向/读回测试 |
| V15 | `tables/v082_experimental_parameter_status.csv` | `9e5930809531a4299e49d0e2b3eb585b5696df01` | 已知/历史/演示假设/缺失参数分层 |
| V16 | `tables/v082_cost_ledger.csv` | `f17fd05b7c2138cc8ce121f27f9230522d1f75ce` | 16次曝光已消费，0 BEM/0位置render |

**Codex一条执行口令**：请完整执行本v083唯一指令，从v082固定提交和工作站真实缓存接续。**不要重复v082已通过的24/96/24谐波表或16次曝光**；先纠正v076历史`tseries_center`取了第21行第1列的错误跨源比较，在同一个真实中心像元上重建与核对24条旧时序，修复X0闭合与相位字段；前置过关后在固定4个旧条件上限内做双精度完整ROI诊断，并仅对预定2个旧合成曝光条件做64节点验证。利用已有24张复C400图筛查中心与空间幅值特征的干扰参数稳健性。不新增BEM、新位置render、新物理节点，不放宽任何历史门槛，不输出未经实验校准的绝对粒径；可执行任务连续完成，失败只暂停依赖支线，最后一次性返回真实ZIP及v083可读分支。
