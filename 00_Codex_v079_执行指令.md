# iSCAT / Fe₃O₄ v079 唯一连续执行指令

## v078 源码审查、满秩谐波分解修复、合成曝光收敛与有限干扰参数辨识评估

> **文件性质**：交给 Codex 在用户 Windows/MATLAB 工作站执行的**下一轮方案**；不是 v079 已完成的数值结果。工作站根据实际可用缓存执行、保留失败证据、一次性交回 ZIP 与 GitHub `v079` 可读分支。无需每一步等待 GPT；仅依赖失败的分支停止，允许的独立任务继续。
>
> **固定审查提交**：`yyyyzoey/iscat-handoff` 的 `v078` = **`2e81e3ba5b882fde79763b65ffbfa1d2dfb11d9b`**（父版本 `v077`=`bfc87300d00d245e985e37dbfd3768600a89c427`），不从活动 HEAD 猜测源码。
>
> **物理与实验事实**：用户已确认实验激光**真空波长520 nm**；7.29现有数据`Fs=5000 fps`、帧1000–3000、`N=2001`，正式候选观测为400 Hz目标（MATLAB正频bin161，实际399.800099950025 Hz）的单边**归一化复调制对比度** `C_k=2X_k/(N Imean)`，反演候选主特征为`|C_k|`，复数图仅在相位参考约束下讨论；420 Hz为旧控制。演示光学参数（NA1.3、物方65nm/px、玻璃/水、5nm间隙、Querry1985体Fe₃O₄折射率）不是实验仪器/样品批次标定事实。曝光、实际NA/倍率/物方像元、磁驱动波形/相位、样品核壳与运动约束仍缺。
>
> **最高预算硬约束**：新增BEM solve **0笔**，新增任何位置的Fe₃O₄复场render **0侧**；不新增粒径/焦面/磁性参数/实验噪声批次。任何修改既有2%前向、`1e-3`复场留出或P0三个矩阵`<1e-10`门槛均禁止。所有数值身份由真实MAT文件、实际执行路径与字节SHA-256证明。

---

## 0. 审查裁决：保留成果与必须撤回的表述

本轮实际锁定并读取 v078：`status.json`、`review.md`、`source/run_v078_A_identity.m`、`source/run_v078_B_closure.m`、`source/run_v078_CDE.m`、原生日志及新增CSV，逐行复核记录数量、配对与若干标量关系。**GPT未在用户电脑执行MATLAB、未重新算BEM、未独立重读工作站全部大MAT**；只接受有源码及实际记录支持的窄结论。

### 0.1 已成立、不得因本轮错误再次重跑的内容

| 结果 | v078实际发布 | 准确裁决 |
|---|---|---|
| 负频率复数项 | 将旧`A_h/2·G(-f)`改为`conj(A_h)/2·G(-f)` | **公式正确**，有非零相位fixture支持；不要撤回修复本身 |
| 数值CSV | 奇偶270行、相机ROI24行、24条谐波表、对应长表96行、实验假设配对276行、曝光8行 | 这些表**确实存在且行数匹配**；不代表它们各自已经通过物理推断 |
| 正确中心、正负键、复场留出 | 历史v075–v077：物理41×41ROI在精细61:265，30签名锚点，24个正负留出`relEs<0.001` | 保留正确缓存与工程验收，无需重复BEM/位置render |
| 8个旧ROI的真实400Hz FFT | 来自v073/v075正确时间轴、六邻频下的开发性诊断 | 保留；不将热点、幅值阈值或邻频增强宣称磁颗粒因果 |
| v078的闭合误差 | 24条`closure_rel`最大约`2.7348e−14`，全部小于源码中`tolClosure=1e−10` | **只接受代数投影重构层面的窄PASS**，不接受“拟合模型满秩/谐波参数已独立认证” |
| P0 | 仍`NOT_RUN_RESOURCE_GATED`；旧`2.58848e−7`高于`1e−10` | 原门槛OPEN，rule7大参考0授权 |

### 0.2 五处具体、可复核的问题

**X1（P0最高优先，QR拟合矩阵被覆盖，确定性错误）**：v078 `source/run_v078_B_closure.m`两处同型实现为：

```matlab
Bm=zeros(N,1+2*nH);
Bm(:,1)=1;
for hI=1:nH
    Bm(:,2+2*(hI-1)-1)=cos(2*pi*allFreqs(hI)*tj);
    Bm(:,2+2*(hI-1))=sin(2*pi*allFreqs(hI)*tj);
end
```

第一条`cos`落在**第1列**，覆盖截距；末列未赋值。`nH=4`时是**2001×9列、秩8、最后一列全零**。原日志对六个fixture、24条轨迹反复报告`秩亏`，相符。审查端独立构造同一矩阵确认：错误9列矩阵`rank=8,cond=Inf`；正确设计矩阵`rank=9,cond≈1.41456849`（这一数值为审查端N=2001/Fs5000/[200,400,600,800]的数学复算，非MATLAB工作站实测）。**因此v078虽然重构成功，也不能证明谐波系数唯一、稳定或其各项所占物理比例。**

**X2（“闭合”与“模型可信”混淆）**：`residV=Ic-Bm*coefAll`后，`Xbin≈Xmodel+Xres+Xintercept`主要检验线性DFT恒等式；任何含残差的线性分解即使基函数错误或秩亏，仍可代数闭合。必须另验设计矩阵秩、条件数、已知幅相回收、残差贡献、源时序一致性及模型稳健性。原`v078_harmonic_parts_long.csv`只有`bin161_dft/model_correct/residual/intercept`四种复项，**缺每个200/400/600/800（或400/800/1200/1600）分量的复数投影列**，现有表不足以单独复核逐频因果贡献。

**X3（摘要把别的字段写成bin/fit）**：`status.json`声称“M200 bin161/C400_fit≈1.000003”。这个`1.000003`对应`v078_harmonics24_complex_closed.csv`最后一列`old_formula_ratio`（旧模型幅值与bin幅值之比），**不是bin161与真正拟合C400幅值之比**。从该表12条M200算`leak400_C/harm400_fit_C≈0.9897636625`（均相同，有限矩形窗的已知离箱衰减）；v077表直接bin/fit约0.9895–0.9897。不得再把三类比值换名。v078 review中“v076 QR本来正确、1000倍差异是v075空间偏移造成”也是不真实的历史重述：v076实际源码确有对LS幅值多乘`2/N`的错误；修正v077及新共轭v078均有必要，二者互不否定。

**X4（状态写的精度严于原结果）**：v078摘要称“六fixture/24条闭合均`<1e−14`”，实际`closure_rel`有数项约`1.9–2.7e−14`，不满足这一更严的叙述；但都远低于代码预先设定`1e−10`，所以不是原门槛下的FAIL。下轮原值保持精度，不以舍入改写门槛。

**X5（曝光并未真正完成高阶积分试验）**：`source/run_v078_CDE.m`在D段直接`load(v076_dynamic_center_corrected.mat)`并把8行旧五节点左端等权结果重新导出，同时更新纯400 Hz `sinc(400τ)`列。**它没有执行新的高阶曝光积分、没有独立检查五节点误差。**当前只能记`PASS_SCHEMA_AND_REFERENCE_FORMULA`，不是`QUADRATURE_CONVERGENCE_PASS`。近零M400的相对变化仍列0.21至0.75等大百分数，仅因源端阈值`absCenter<1e−10`没有触发；这不是经过噪声/精度验证的“可靠百分比”。

**其余限制**：v078的270行正确三态奇偶重构误差`<1.8e−18`是按定义的代数恒等式，不是独立的平移物理验证；3个振幅步长5/10/20nm的有限差分是步长敏感量，不能自称连续位移的精确局部导数。v078的276对距是v076正确中心的离散处方状态，与v077同范围，**不是新增独立盲测**。跨粒径最小幅值图对称距离约0.26465455，不能无噪声/光路/运动先验便得出“必定可区分”或“严重混叠已认证”。

---

## 1. 执行依赖、禁令与状态语义

- **固定源**：v078 SHA如首页。加载现有`v076_return/numeric/v076_center_roi_harmonic_small_examples.mat`（24中心时序）、`v076_dynamic_center_corrected.mat`（24正确ROI复C400图）、v075`v075_holdout_data.mat`（24个真实全复场留出），v074 `render_cache/*.mat`（30有符号锚点）。以真实工作站`which`、`whos -file`、shape/type/SHA、D/zf/x/q/fs/bin身份重新核对。
- 先读有效文件身份和任务账本，不为导出或更新文字重复计算。不得引用已撤回v074错误有符号内存键、v075偏移中心图、v072错误FFT时间维度图，不能把缓存目录中的历史坏数据当PASS。
- 采用四字段`execution_status`、`validation_status`、`evidence_status`、`scientific_scope`。数值`PASS`不覆盖`experimental_validation=false`。失败独立分支继续，报最小复现。
- 正式工程门槛不变：旧均匀场BEM/Mie四指标各`<2%`、v075复场留出`<1e−3`、原P0三矩阵各`<1e−10`；**v079新QR设计矩阵满秩与条件数检查是新增数学前置，不是放宽物理门槛**。
- 对任何有风险的操作（新增BEM solve、变相提高网格、真实数据新采集、新磁颗粒D节点、删除别人的MATLAB会话）本轮一律不批准。

## 2. A：零BEM入口门禁及满秩矩阵修复（最高优先级）

### A1. 校正一个共享的谐波基生成函数

建议建立`build_harmonic_design(t, freqs, includeIntercept)`和`fit_harmonics_fullrank(I,Fs,freqs)`，删除各驱动内的重复错误索引。正确MATLAB伪代码：

```matlab
freqs = [200 400 600 800];              % M200示例；M400=[400 800 1200 1600]
N = numel(I); t = (0:N-1)'/5000;          % 实际t0单独记录
H = numel(freqs);
B = zeros(N,1+2*H);
B(:,1) = 1;
for h=1:H
    B(:,2*h)   = cos(2*pi*freqs(h)*t);
    B(:,2*h+1) = sin(2*pi*freqs(h)*t);
end
assert(all(abs(B(:,1)-1) == 0));
assert(all(any(B~=0,1)));
assert(rank(B)==size(B,2),'QR_DESIGN_RANK_DEFICIENT');
conditionNumber = cond(B);
assert(isfinite(conditionNumber) && conditionNumber < 1e8,'QR_DESIGN_ILL_CONDITIONED');
coef = B\double(I(:));                    % 拟合原始I，截距独立求解
Imean = mean(double(I(:)));
A_h = complex(coef(2*h),-coef(2*h+1));   % 每个频率对应的复正弦幅值
C_h = A_h / Imean;                        % 不是 2*A/(N*Imean)
```

`cond<1e8`是v079新增数学稳健性预检的保守上限；任何不满足都停该谐波支线并给出奇异值、采样设计和精确条件数，**不得通过截断或任意正则化绕过**。源代码务必使用正确的实际变量名和取样索引，不得复制上面示例中的循环变量`h`出作用域。

### A2. 定义必失败的负向测试及同源时序测试

1. 将v078旧矩阵按原语句构造，断言`size=(2001,9)`、`rank=8`、第9列全零、第一列非恒1；该旧函数若用于生产必须报错。
2. 新矩阵`rank=9`、完整截距与全部正余弦列非零、`cond`有限；零调制、已知相位及混合信号拟合不得出现rank-deficient警告。
3. 对24条中心时序优先直接读取v076小MAT；按结构身份检查它们真是物理中心(21,21)而非历史`Ipix(21,1)`；对最多3条弱M400用既有复场比较float32/float64计算链。v077记录6条“`DIFFERS`”且最大强度绝对差约2–5×10⁻10，报告**数值误差而非位级一致**。
4. 一笔实际缓存元数据发现缺失，查正确签名键再查`render_cache`，不得因v077错误不带`.mat`/错误文件名重新render。

**A放行**：正确设计矩阵满秩且条件数有限；旧秩亏断言能拦截；24时序身份明确或逐条列`MISSING`；源SHA和真实输入量纲保留。

## 3. B：24条谐波分解的真正参数验证与复数闭合

### B1. 保持原始测量量，与拟合诊断分开

对每条2001帧像元时序`I(t)`同时保存：

```text
Imean = mean_t I
k0=160; actual bin frequency=399.800099950025 Hz
Xbin = sum_j (I_j-Imean)*exp(-2pi i*k0*j/N)            # units = 原强度×帧
Cbin = 2*Xbin/(N*Imean)                              # dimensionless complex
A_h = a_h - i*b_h  (LS拟合原始I得到的实际强度振幅)
C_h,fit = A_h/Imean                                  # dimensionless complex
G_N(u) = sum_{j=0}^{N-1} exp(2pi i u j)
X_h->k = 0.5 A_h G_N(f_h/Fs-k0/N) + 0.5 conj(A_h) G_N(-f_h/Fs-k0/N)
Xbin = sum_h X_h->k + Xintercept + Xresidual
```

**两层不同的验收**：
- 数学/代数：复数误差`|Xbin - (ΣXh+Xint+Xres)|`。保留v078源码`closure_rel<1e-10`的门槛并发布未舍入值；附加`|error|/|Xbin|`只在稳健非零时报告，近零用绝对DFT单位差。
- 模型物理解释：`rank/cond/singular values`合格；已知频率、幅值、非零相位fixture能回收对应`C_h`；残差时域RMS与投影大小可见；改用满秩后的`C400_fit`、200/400/600/800或400/800/1200/1600贡献与v078表逐项比较。**闭合即使达到机器精度也不自动意味着残差小或模型足以分离磁因果。**

### B2. 解析夹具，不重复无意义测试

只允许**8个纯解析fixture上限**（包括必要重新执行的原6项、额外最多2项相位/近零应力测试），不增加BEM/位置render：纯200、纯400非零相位、纯800、200+400任意相位、200+400+800任意相位、零幅；此外可采用含截距、真实时间起点或极小C400的夹具两项。解析双精度输入期望的复系数/残差按`≤1e−10`相对或适当绝对`≤1e−12`检查（固定在fixture源码；近零不以`realmin`冒充精度）。必须出现一项**故意复制旧索引**的`MUST_FAIL`测试。

### B3. 24条既有时序后处理

M200频率基固定`[200,400,600,800] Hz`；M400固定`[400,800,1200,1600] Hz`。对每条输出至少：

```text
source_series_sha, D_nm, zf_nm, M200/M400, assumed_a_nm,
N, Fs, t0, k0, mean_I, min_I, fit_frequency_set,
rank_B, cond_B, rank_warning_count,
A200/A400/A600/A800/A1200/A1600 (按实际包含频率),
X_h_real/X_h_imag (每个谐波的独立长表),
Xbin_real/imag, Xres_real/imag, Xint_real/imag,
Cbin_real/imag, Ch_fit_real/imag,
closure_abs_DFT, closure_rel_DFT, residual_RMS,
old_invalid_design_status, validation_status
```

为避免再次缺独立核查入口，逐谐波`X_h`和`Xbin`,`Xres`必须保存**相同DFT_count单位的实/虚两列**；归一化`C_h`另表，不允许混入同一求和式。对至少3条M200和3条近零M400保存完整小中心时序与模型预测，独立MATLAB会话读回并复核，不以仅复制CSV字符串算独立验证。

**B放行**：旧坏矩阵被拒绝，8项内fixture中规定任务均PASS；24条的满秩与复投影门槛逐条评估。失败只冻结对应实验物理分解论断，其它C/D/E依赖只读工作可继续。

## 4. C：奇偶270行、相机ROI24行与空间条件敏感性——只做必要复核

1. **继承v078原270行**：实际上是18个`D,zf,a`组合，每组15个固定物理像元(5行×3列)，三态`I(-a),I0,I(+a)`完整。不要为了新版本重导270行。只用小表做`a=5/10/20 nm`步长下`odd_half`与`even_increment`趋势，记有限差分意义，特别比较同一物理像元在不同`a`的`Iprime,Isecond`稳定性；不能宣布连续导数已证实。`Iplus_recon_err/Iminus_recon_err`天然近机器精度，属于代数校验不是新光学独立验证。
2. **继承v078相机ROI24行**：保持`Itot_camera_relL2`、`Itot_finegrid_relL2`、`contrast_roi_relL2`互不替代；41×41物理ROI按精细`61:265`，`pixel_mean(q5)`后评分；`S_area=65²sum(C)`单位nm²。近零相机中心和带符号积分同时报告绝对差、相对差是否适用。
3. v078 `T10_true_39nm`已从精细`64:268`与`61:265`比较，原结构正确，保留数值，不再重复物理render。
4. 对跨D的动态形状比较应使用真实对应`v076_corrected_C400`，而不是旧v075偏移中心。若共享缓存丢失，仅标缺证据，本轮新位置render=0。

## 5. D：真正完成旧8个合成曝光的积分收敛（有限时域后处理）

**重点**：v078只重导了原5节点左端等权的8行和正确`sinc(400τ)`，并没有真正执行高阶积分。

对**固定D60,zf450**、两种处方运动(M200/M400)、振幅a=5/20nm、合成曝光`τ=100/200 μs`共8个原物理条件，使用已有30个签名位置复场，绝无BEM或位置render：

- 先做1个**纯400 Hz强度正弦**解析夹具，以曝光平均`I_frame(t)=1/τ∫_{t}^{t+τ} I(s) ds`为参考，理论幅值`|sinc(400τ)|`，相位附带积分中心时间移`+τ/2`（具体符号按FFT约定推导）；禁止把磁运动基频200当成待测强度谐波400。
- 复用v076/v078已算好的5左节点结果，只新增**高阶复用位置插值的时域数值评价**：例如每曝光窗口16节点与32节点复场构强度的中点积分（对原8个条件最多各2次，**至多16次额外时序评价**），与5点左和同一无曝光基线比较，保存每条原始复C400（不仅模值）、时间积分误差、有限差分及频点/相位/无效掩码。需要防止用假设`τ=200μs`等同真实曝光；实际仍`MISSING`。
- 数值近零的M400中心，应给出绝对变动、单双精度误差和可解析正弦夹具精度，若接近数值下限则`NUMERICALLY_UNRESOLVED`，禁止仅以`75%`之类无稳定分母比值作因果解释。
- **不降低原工程门槛**；本轮曝光收敛是新增模型开发结果，若16/32节点的变化未稳定，仅标`QUADRATURE_NOT_CONVERGED`，不能增大到任意64/128节点无授权扩算。

## 6. E：研究上的真正下一步——有限参数干扰下的观测量区分度（零新物理状态）

v078已经有24张来自v076正确物理中心的`41×41`复C400图，276个无序对（192跨D/84同D）。**不重新运行276组物理仿真**，直接读取正确且可回溯的现有`v078_identifiability276_audit.csv`与v076图做以下有限分析：

1. 按固定扰动维度`+D`、`+a`、`+zf`、`+type`及其组合分别汇总；只对同一定义下的有意义对比较。对称距离`||Ci−Cj||/((||Ci||+||Cj||)/2)`分别用于复C400与模值图；实验没有磁驱动参考相位，**复图仅供方法学诊断，模值图才是当前可候选实际量**。
2. 找出跨粒径最相近的固定状态组合、同粒径不同干扰组合、全ROI vs中心单标量排序；报告分子、两侧范数、同一掩码及相同物方采样。发布记录中跨D最小`abs`图对称距离约`0.26465455`，这是当前离散点的无噪声相似度，不是噪声下不可区分阈值。**不得通过逐对独立的自由振幅/相位配准人为把不同D拉近后又称它们真实等价**。
3. 在**不引入新的噪声批次**的前提下，做固定、确定性的开发性`leave-one-template-out`几何最近邻清单（24个模板，只有这24个已发布状态，严禁称统计盲测）。分别比较完整ROI幅值、中心幅值。留一时若测试状态不在训练网格而相同D其他点存在，输出距离和猜测/失败，仅作为模型内插难度诊断；不输出实验粒径误差、置信区间、Bias/RMSE或FPR。
4. 由于真实样本NA、物方像元、曝光、实际磁驱动和批次材料未证实，**将参数不可辨识、信号背景伪影与检测未验证单列OPEN**。最终v079不批准新的磁颗粒物理粒径扫描或密库。

## 7. F：实验输入与P0安全诊断（独立支线）

- 在工作站现有项目目录、相机附带元数据、实验日志、MAT变量里**一次只读有限检索**实际曝光/快门、物镜NA、总倍率或物方像元、驱动频率/波形/同步参考、粒子制备批次及核壳、观测面和高度信息。记录`value/unit/source/SHA/status/uncertainty`；未找到即`MISSING`。禁止将演示65nm/px和NA1.3偷换成真实参数；520nm激光由用户已确认。
- 真实一组7.29像素FFT输出仅证明从时序计算正确的400Hz量；没有磁驱动同步记录不能证明“200Hz磁驱动导致的2f”，没有真实光路和已知颗粒标准不能建立绝对粒径标定，不能将均匀强度调制产生的400Hz峰当单颗粒检出。
- P0支线只在PID/命令行/内存许可与用户权限均可证明安全时，继承旧最多一轮`galerkin.pot1.duffy1/eval2`目标路径被动Hook；不安全则记`NOT_RUN_RESOURCE_GATED`并保留额度。冻结blocked/unblocked direct/reflected/total三矩阵Frobenius均`<1e−10`，原`2.58848e−7`OPEN，不运行新rule7大参考。

---

## 8. v079预算账本（全部显式、互不转移）

| 计算/分析项目 | 本轮最大额度 | 说明 |
|---|---:|---|
| **新BEM solve** | **0笔** | 旧30/60/100nm/金球解全保留，不因文本和QR重求 |
| **新Fe₃O₄位置复场render** | **0侧** | 已有30位置锚点、24留出直接读 |
| 原24条中心时序满秩QR复拟合 | **24条** | 从小MAT直接读取，**不是24次新渲染** |
| 合成数学fixture | **最多8项** | 包括旧6项新矩阵复验及最多2项新应力测试 |
| 原M400弱信号单双精度对照 | **最多3个既有条件** | 只读已有复场、可选恢复小规模时域采样 |
| 奇偶及相机ROI来源核对 | 原270/24条 | 优先只复用、抽点回读，不重复整批渲染 |
| 曝光积分高阶比较 | **8条件×最多2种高阶方案=16个时域评价** | 这是显式新增有限后处理预算；旧5左节点结果不重算 |
| 276对距离及最邻近筛查 | 纯已有数据，**0新物理态** | 可读回旧表与24图；不重复成本 |
| 实验原BMP完整组重扫、新噪声批次、独立采集 | **0** | v073正确回放复用 |
| 新D/zf/a/f、材料、磁运动拟合或实验标定 | **0** | 本轮不放行 |
| P0被动Hook | 继承旧**至多1轮** | 必须过资源安全门；rule7新求解0 |

成本账必须分别记录`planned_task_slots`、`actual_function_calls`、`physically_unique_states`、`cache_hits`、`failed_invocations`。先使用已验证缓存，不因为v079启动重算旧闭合/重读全部BMP。Matlab进程高内存或许可证竞争时串行执行，且不得杀其它任务持有的历史会话。

## 9. 失败依赖和自动推进

- A满秩断言失败：阻塞B的科学谐波结论；可继续C/E/F只读核对。绝不能回退到旧秩亏模型后仍报PASS。
- A中部分中心时序缺失：只对相应条件报告`MISSING`；仅在原工作站有效完整复场缓存允许且本轮3弱信号预算内才恢复小样本，不能偷偷再执行24组时序全批。
- B单fixture复相位不通过：不放行24条谐波解释；保留现有DFT观测而不推断物理比例。
- D高阶曝光未稳：记录`QUADRATURE_NOT_CONVERGED`，保留旧5节点为开发结果，不能转换成正式误差条。
- E参数干扰没有独立证据：只能输出离散假设集合结构和最近对，不能宣称实验测径已成功。
- 独立任务不因别的支线失败停工；所有符合前置、预算的任务**连续一次完成**，最后一次性交回ZIP，不等待逐步GPT指示。

## 10. 唯一ZIP与v079可读分支交接

请生成**一个**`iscat_v079_return.zip`，并在GitHub `yyyyzoey/iscat-handoff`发布新`v079`可读分支（公开仓库不提交私人原BMP、个人绝对路径中的隐私信息、整组实验机密图）；至少包含：

```text
iscat_v079_return.zip
  00_README.md
  00_全部文本汇总_v079.md
  00_Codex_v079_执行指令.md
  status.json / review.md
  source/
    build_harmonic_design.m
    fit_harmonics_fullrank.m
    project_complex_harmonics_to_bin.m
    run_v079_*_actually_executed.m
    ... numeric safety tests and CSV schema validators ...
  tables/
    v079_source_identity_and_cache.csv
    v079_design_matrix_negative_and_positive.csv
    v079_harmonic_fixtures.csv
    v079_24_series_fullrank_complex_decomposition.csv
    v079_harmonic_terms_complex_long.csv
    v079_harmonic_closure_and_residuals.csv
    v079_weak_center_precision.csv
    v079_exposure_quadrature8.csv
    v079_evenodd_step_sensitivity.csv
    v079_camera_roi_semantics_check.csv
    v079_nuisance_aware_pairwise_summary.csv
    v079_24_state_developmental_leave_one_out.csv
    v079_physical_input_readiness.csv
    v079_p0_status.csv
    v079_cost_ledger.csv
  numeric/
    ... at least six trace/projection/residual small examples; full big MAT only if truly packaged ...
  logs/
    ... native MATLAB stdout/stderr, warnings, function paths and lineages ...
  manifest_sha256.csv
```

- 每张新CSV必须标准UTF-8，无NUL，字段数严格一致，数值型列不能掺入文本型状态；失败报告也要单独保存。包成后独立进程重新读取关键表、对SHA与原输入变量逐个核验。不允许仅通过打印`PASS`就取代实际断言。
- `source_hash`应为工作站源码**文件真实SHA-256**；Git SHA-1 blob另列，不能混写。Windows换行格式可能与Git文本不同，应注明计算对象，不武断判坏。大工作站only的MAT需报告真实path、bytes、sha、shape、class、复数/掩码及变量名；不能谎称它们存在于ZIP/GitHub。
- 不覆写历史v077/v078文件，保留全部错误的原状态和相应替代版本。`status.json`严格区分`mathematical_identity_verified`、`harmonic_parameter_fit_valid`、`finite_scope_forward_valid`、`experimental_detection_validated`、`calibration_valid`。
- 必须保持：`calibration_valid=false`、`experimental_validation=false`、`detection_validated=false`、`single_particle_diameter=NOT_ESTIMATED`，除非未来另有真实独立材料/光路/运动/检测/已知标准证据，本轮不允许变更。

## 11. 固定来源索引（全部可定位）

固定提交首页：https://github.com/yyyyzoey/iscat-handoff/tree/2e81e3ba5b882fde79763b65ffbfa1d2dfb11d9b

| 编号 | 文件 | 审查证据 |
|---|---|---|
| S01 | [`status.json`](https://github.com/yyyyzoey/iscat-handoff/blob/2e81e3ba5b882fde79763b65ffbfa1d2dfb11d9b/status.json) | 执行者宣称六fixture、24闭合和物理冻结状态；需与原表分开看 |
| S02 | [`review.md`](https://github.com/yyyyzoey/iscat-handoff/blob/2e81e3ba5b882fde79763b65ffbfa1d2dfb11d9b/review.md) | 复数共轭修复、数学/科学解释及历史叙述偏差 |
| S03 | [`source/run_v078_B_closure.m`](https://github.com/yyyyzoey/iscat-handoff/blob/2e81e3ba5b882fde79763b65ffbfa1d2dfb11d9b/source/run_v078_B_closure.m) | 两处满秩矩阵覆写错误、`tolClosure=1e−10`、GN和复数投影、元数据输出 |
| S04 | [`logs/matlab_native_run.log`](https://github.com/yyyyzoey/iscat-handoff/blob/2e81e3ba5b882fde79763b65ffbfa1d2dfb11d9b/logs/matlab_native_run.log) | 6fixture和24轨迹实际秩亏警告；旧程序完成不等于模型有效 |
| S05 | [`tables/v078_harmonics24_complex_closed.csv`](https://github.com/yyyyzoey/iscat-handoff/blob/2e81e3ba5b882fde79763b65ffbfa1d2dfb11d9b/tables/v078_harmonics24_complex_closed.csv) | 24数值闭合，最大约2.7348e−14；`old_formula_ratio`被status误称bin/fit |
| S06 | [`tables/v078_complex_projection_fixtures.csv`](https://github.com/yyyyzoey/iscat-handoff/blob/2e81e3ba5b882fde79763b65ffbfa1d2dfb11d9b/tables/v078_complex_projection_fixtures.csv) | 六fixture有复相位负频项数学信息；归因需满秩再检 |
| S07 | [`source/run_v078_CDE.m`](https://github.com/yyyyzoey/iscat-handoff/blob/2e81e3ba5b882fde79763b65ffbfa1d2dfb11d9b/source/run_v078_CDE.m) | 270三态差分、24相机ROI、39nm负向测试、8曝光复用旧值、276对复图距 |
| S08 | `tables/v078_evenodd_270.csv` | 270条，18组合×15像元；重构接近0由定义决定 |
| S09 | `tables/v078_camera_roi24.csv`、`tables/v078_T10_true_39nm_negative_test.csv` | 相机与子网格L2分列、41像元中心、负向测试 |
| S10 | `tables/v078_exposure_analytic8.csv` | 更新了正确的`400Hz sinc`文字，仍为原5左节点数据，未证明高阶积分收敛 |
| S11 | `tables/v078_identifiability276_audit.csv` | 24状态中276对；192跨D/84同D；属于假设离散模型诊断 |
| S12 | `tables/v078_source_cache_identity.csv`、`numeric/numeric_inventory.json` | 已验证的工作站源/原缓存位置，依旧不表示审查端读过全部大MAT |
| S13 | `tables/v078_p0_status.csv`、`threshold_freeze.json` | P0未过门槛，rule7不可启动 |

### 交给Codex的唯一口令

> **请完整执行本v079唯一指令，从GitHub固定v078提交和真实工作站缓存接续。第一优先修复两处谐波设计矩阵列索引覆盖造成的rank deficiency，让满秩、非零相位解析回收、24条原中心时序的复数分解与独立读回逐项成立；不要把含残差的代数闭合当作谐波归因。保留270奇偶、24相机ROI和276对结果，只做必要来源/步长核对；原8条合成曝光仅在最多16个新增高阶时域评价额度内完成收敛检查。新BEM 0、新位置render 0、不加新物理D/zf/运动、原门槛不变。符合依赖的工作连续完成，不必每小步等GPT，最后交一个ZIP和可读v079分支。**
