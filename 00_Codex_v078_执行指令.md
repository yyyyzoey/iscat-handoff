# iSCAT / Fe₃O₄ v078 唯一连续执行指令
## 对 v077 的固定提交审查：复数谐波投影闭合、曝露参考、三态奇偶差分与有限可识别性

> **性质**：交给 Codex 在原 Windows/MATLAB 工作站执行的下一轮唯一指令，**不是已运行的 v078 仿真结果**。先保留已经有根据的结果，再纠正源码与发表数据之间的冲突；不允许由总结文字替代实际计算。前置合格、预算允许的分支一口气连续执行，不必每一步等 GPT。失败仅暂停依赖该失败的分支，其他独立任务继续，最终统一返回一个 ZIP 和可读 GitHub `v078` 分支。
>
> **固定审查对象**：`yyyyzoey/iscat-handoff@bfc87300d00d245e985e37dbfd3768600a89c427`（`v077`，不可改读移动分支）。前驱 `v076@1e6287d4ba31af5f132aa5fc125f5a44e89a22d0`。固定本轮输入、实际 MATLAB `which`、函数源码的字节 SHA-256、旧结果 MAT 的变量 shape/class/hash。Git blob SHA-1 不是文件 SHA-256。
>
> **实验与物理身份**：用户确认激光真空波长 **520 nm**；7月29日数据 5000 fps、帧1000—3000共2001帧；主观测定义 `C400=2 X_{k=160}/(N Imean)`，MATLAB索引161，实际频点399.800099950025 Hz，主拟研究模值`|C400|`，保留复数值。420 Hz旧未归一化链仅作对照。已用体Fe₃O₄ Querry(1985) `n=2.349+0.083i` 的BEM场、65 nm物方像元、q5、演示NA等**仍是文献材料/演示光路**；不把它们当该批次真实标定。曝光、实际NA/倍率/物方像元、磁驱动波形/相位、材料批次、轨迹和高度仍未确认。冻结：`calibration_valid=false`、`experimental_validation=false`、`detection_validated=false`、`single_particle_diameter=NOT_ESTIMATED`。

---

## 0. v077已审事实、裁决及本轮不可重算事项

| ID | 实际审查事实（固定v077来源） | 严谨裁决 |
|---|---|---|
| R01 | `source/run_v077_B_qr.m`用 `C400c=(coef4-1i*coef5)/Im`，不再给正弦LS系数多乘`2/N`。12条M200表报 `bin161/fit=0.989509..0.989727`。 | **接受QR单一谐波的归一化纠正**，不能据比例单独宣称完整泄漏因果分解。 |
| R02 | 六行解析夹具在已报告检查条件下均PASS，尤其单频点DFT对闭式双项Dirichlet参照。 | 保留有限解析验证；多谐波复数闭合仍需新增**真正测试**。 |
| R03 | `v077_identifiability_276pairs.csv`有276个不同状态无序对，含192个跨D、84个同D，来源代码读取的是`v076_dynamic_center_corrected.mat`而不是被撤回的v075偏移图。 | 接受离散pair覆盖及已发表数值，须原数组重聚合与分组解释；**不是实验准确率、FPR或连续唯一性证明**。 |
| R04 | `v077_even_odd_derivatives.csv`实际**45条**，源码只有`for zf=450`，而非状态文字的450条。 | 修订覆盖表述；三态读取成立，但下述 `recon_err` 公式不成立。 |
| R05 | `v077_exposure8_schema_and_quadrature.csv`结构可读；**M200四行sinc仍按200Hz**，M400四行按400Hz。 | 撤回“八行全部使用400Hz强度观测参照”的PASS。 |
| R06 | `v077_harmonic_complex_projection24.csv`有96行，正好24条件×4类：`model_total,leak200,harm400,residual`；**不是包含800Hz分量、同单位、实测闭合误差的全贡献表**。 | 撤回“全24条复数窗口泄漏闭合”的宣称。 |
| R07 | `v077_center_series_crosscheck.csv`只有6行，全部为`DIFFERS`，保存与重建原始强度最大差约`1.99e-10..4.64e-10`。 | 不宣称 bit-identical；检查 single/double 路径及其对中心复C的影响。 |
| R08 | `source/run_v077_A_identity.m`试图寻找`v075_return/numeric/render_cache/D60_zf450_x-5.mat`并记为`MISSING`；实际v075保持的是`position_key()`格式的`D60_ZF450_XM0005000.mat`。 | 是**路径约定错误/需要真实核查**，不能据错误路径宣称原留出丢失或重算BEM。 |
| R09 | `v077_holdout_camera_roi_semantics_fixed.csv`有24个物理条件 + 1行`D=0,zf=0` T10伪条件；`Itot_roi_relL2`源码对205×205精细网格直接取Frobenius。 | 把T10另表，物理条件表只留24行；精细网格诊断与真正41×41相机像元误差分开。 |
| R10 | 正确中心位置仍为物理65×65相机图第33像元；41×41相机ROI精细`61:265`，中心像元精细`161:165`，q=5。v075 24条复场留出小于原`0.001`门槛。 | **继续保留**。不得为v077的数据/公式瑕疵而重跑旧BEM或54个位置态。 |

**对用户的审查端独立数值复核**（来自这次固定提交的CSV，不冒充MATLAB/BEM重新运行）：

- 24条新QR拟合：12条M200的`bin161/correct_fit`落在`0.989509..0.989727`；其余12条M400的比值为`0.302600..1.292892`，接近零的中心量不能用一个统一“1%泄漏”解释。
- v077曝光：`sinc(400×0.0001)=0.9973701827725`；`sinc(400×0.0002)=0.9895056209813`。M200的四行仍写`0.999342`和`0.997370`（对应200Hz），与宣称不符；M400四行约对。
- 45条奇偶（仅zf450），中心D60 `odd_half≈6.8129e-11`、`even_increment≈−7.7666e-7`，有限样本支持近偶对称；不能由此宣称任意位移/任意焦面近偶对称。
- 276对中，跨D最近的一对：`D30_zf550_M200_a20`与`D60_zf450_M200_a5`，对称复距离`0.26552775`，模值图距离`0.26465455`；84个同D对的最小模值距离约`0.37829551`。**没有标定的仪器噪声与模型误差，不能把0.2647直接判定为不可分，也不能宣称可分。**

### 0.1 影响结论的四项确定性代码缺陷（P0）

**X1，复数投影的两频项缺共轭**。源代码对`a200=coef_cos-1i*coef_sin`写：

```matlab
Xleak200 = (a200/2)*(G1+G2);      % v077错误，负频率项须共轭
Xh400    = (a400/2)*(H1+H2);      % 同样有问题
```

正确应使用`(a_h/2)*G1+(conj(a_h)/2)*G2`，且模型中存在的800Hz必须进入投影。当前处方模型时间起点的纯cos系数可使错误被掩盖；要求使用**任意非零相位**混合fixture及真实残差验证。

**X2，原始DFT/归一化对比度的单位混用**：`Xleak200`,`Xh400`,`Xres`是未归一化DFT系数，`model_total=Cmodel=2*Xmodel/(N*Im)`已经归一化；v077发布的96行无法按其列名直接求和。保存的`closureAbs`不是正式CSV字段，源码也没有对24条逐项`assert`。绝不能把代码注释`closure checked`当成验收。

**X3，奇偶重构误差错误**：`recon=I0+odd_half+even_increment`的预期恰是`Iplus`；发布代码却计算`abs(recon-I0)/abs(I0)`命名为`recon_err`，该列实际更接近相对强度变化。应对Iplus和Iminus均闭合，以双精度绝对误差评估。

**X4，实验观测sinc按强度频率而不是运动基频**：对于M200的**400Hz强度谐波**，仍必须使用400Hz作为矩形曝光的纯频率参照，而非200Hz。合成强度若含200/400/800Hz多分量，则各谐波应分别乘自身频率的复曝光传递函数，不能把混合非线性时序硬套一个纯400Hz sinc作为其整体精确真值。

附加来源/字段问题：`v076_C_dynamic_center.m`曾把字段`tseries_center`存成`Ipix(ci,1,1,:)`（左列而非中心列`Ipix(ci,ci,1,:)`），虽然**原整幅复C400的提取位置是正确的**。v077采用另一个中心复场路径生成谐波时序，因此下轮必须在同一条件对两条路径的真正中心时序/复数DFT做对照。V077独立会话只报告6条新旧时序`DIFFERS`，不得偷偷改成字节相同。

---

## 1. 阶段A：源代码/缓存身份、中心时序与I/O守卫（零BEM/零位置render）

**A1. 固定输入并真正读回**：

1. 实际`which`、SHA-256、长度、MATLAB版本；冻结 `render_system.m`、`pixel_mean.m`、`extract_fft_v073.m`、`position_key.m`、本轮新的拆分程序。
2. 核对`v074_return/numeric/render_cache`30份真正带符号的锚点；`v075_return/numeric/render_cache`24个holdout实际文件名按`position_key`；`v075_return/numeric/v075_holdout_data.mat`；`v076_return/numeric/v076_dynamic_center_corrected.mat`（24张41×41复C图）；`v076_return/numeric/v076_center_roi_harmonic_small_examples.mat`（24条中心时序）。独立检查shape/class/物理D,zf,x与 SHA，不靠目录名代替。
3. 删除`run_v077_A_identity.m`中对二进制MAT的大块`fileread`测试和错误`D60_zf450_x-5.mat`路径；只需`dir.bytes`及真实字节hash、必要变量`whos('-file',...)`。原表的`MISSING`保留作错误路径历史，新表写`WRONG_LOOKUP_CONVENTION`或真实`MISSING`。
4. 固定物理中心：`fine 161:165`整合成65nm中心像元第33；物理41×41为`fine 61:265`。通过存盘正负状态和独立中心取样，不允许按结果选择ROI。
5. 对至少6个已有M200 a5条件，从真实缓存重建中心`I_j`，和v076真正中心时序比对；保存`maxAbs(Inew-Iold)`、强度单位、单/双精度、C400复数最大差、时间原点/系数。若有不一致，查实现与精度；不得凭约`1e-10`相差很小就写成bit-identical。
6. 所有CSV固定键、字段宽度、无意外控制字符、NaN/空值、重复键，独立读取器拒绝坏数据。历史错误记录只读，不能替换。

**A放行**：缓存身份真实可读，物理中心、时序轴、原观测定义一致；缺原时序则仅在本轮已说明的条件性纯后处理范围内恢复，严禁因此求BEM。

## 2. 阶段B：复数DFT/G_N/QR联合闭合（本轮最高优先级）

### 2.1 正确数学合同与量纲

设`N=2001, Fs=5000, k0=160, Ibar=mean(I_n), y_n=I_n-Ibar`。对真实**强度**时序做统一的联合最小二乘（截距＋各正/余弦）：

\[
y_n=\beta_0+\sum_{h\in\mathcal H}\bigl(a_h\cos(2\pi f_h t_n)+b_h\sin(2\pi f_h t_n)\bigr)+r_n.
\]

定义`A_h=a_h-i*b_h`，直接振幅`C_h,fit=A_h/Ibar`，**无需**`2/N`；原FFT bin的定义另为

\[
X_k=\sum_{n=0}^{N-1}y_n e^{-i2\pi k_0n/N},\qquad C_{\rm bin}=\frac{2X_k}{NIbar}.
\]

复Dirichlet核（差分指数求和）：

\[
G_N(u)=e^{i\pi (N-1)u}\frac{\sin(\pi Nu)}{\sin(\pi u)}
\]

在靠近整数极限以数值稳定表达求值，必要时直接有限和交叉核查。单一谐波的**原始DFT单位**贡献为：

\[
X_{h\to k}=
\frac{A_h}{2}G_N(f_h/F_s-k_0/N)
+\frac{A_h^*}{2}G_N(-f_h/F_s-k_0/N).
\]

拟合残差的原始系数为`Xres=DFT(r,k0)`，截距项在非直流整数DFT bin的和理论上为0（可单独记录数值余量）。按与真实拟合基**完全一致**的频率集合（例如M200先用200/400/600/800，M400先用400/800/1200/1600；若另采用对照基，另建实验ID），闭合：

\[
X_k=\sum_h X_{h\to k}+X_{\rm residual}+X_{\rm intercept},\qquad
C_{\rm bin}=\sum_h\frac{2X_{h\to k}}{NIbar}+\frac{2X_{\rm residual}}{NIbar}+\frac{2X_{\rm intercept}}{NIbar}.
\]

**注意**：每个分量必须**复数**相加，不得只加模值，也不得把原始`X`和归一化`C`相加。各列明确`units=DFT_count`或`dimensionless_C`。

### 2.2 六个固定数学夹具（零时序物理评价）

至多6个、包括真正使旧代码失败的样例：单400Hz非零相位；单200Hz纯泄漏；200+400且双方相位均非0/π；200+400+800非零相位；400+800+1600含残差；纯零调制/常数强度（相位未定义）。每个用**联合**QR/反演重建、直接DFT和闭式G_N独立核对。旧`(A/2)*(G1+G2)`必须在指定非零相位fixture上FAIL；将`X/C`混加、遗漏800和旧`2/N`也必须FAIL。

优先双精度：合成直接DFT与G_N的归一化复系数相对误差`<1e-10`（近零绝对`<1e-12`），模型分解复数闭合采用残差归一化

\[
\epsilon_{\rm close}=\frac{|X_k-\sum_hX_{h\to k}-X_{\rm residual}-X_{\rm intercept}|}{\max(\sqrt N\,\|y\|_2,10^{-14})}<10^{-10}.
\]

这些是本轮针对双精度算术新增的**工程断言**，不改变历史BEM误差2%、复场留出0.001或P0矩阵1e-10。对原先单精度样本，记录单精度→双精度强度转换误差及绝对/相对精度是否有定义；近零幅值默认`NUMERICALLY_UNRESOLVED`而非以`realmin`凑相对通过。

### 2.3 24条既有中心时序逐行复核，不重新生成物理场

1. 从已保存的24条正确中心原始强度时序读取；若没有完整时序或缓存身份冲突，最多允许24条**原条件**时域纯后处理恢复，算预算；不得新增D/zf/a/f或位置render。
2. 统一联合QR（固定频率/矩阵列/时间原点），保存rank、条件数、`Ibar`、拟合`A_h`（复数）、残差RMS及全部原始/归一化DFT贡献。
3. 每行明确`X_bin, X_model, X_res, X_intercept, C_bin, C_fit400, C_model, C_res, C_closure_abs, epsilon_close`。每行须独立触发断言，**不能只在日志打印PASS**。
4. 对24行M200/M400分开总结；先保留M200 `bin/fit≈0.9895`原观察，同时验证精确**复相位**贡献后才能说明窗口泄漏份额。M400中心极小信号优先用绝对误差和精度对照，不能用异常大的百分比归因。
5. 将`source/run_v077_B_qr.m`原`v077_harmonic_complex_projection24.csv`保留为`HISTORICAL_UNCLOSED_MIXED_UNITS`，新表必须使用新列、包含全部拟合频率及截距、可读回并有独立校核。

**B放行**：6/6合成夹具及24/24数学闭合条件逐项满足或明确列出失败，所有`C`由可追溯强度时序导出；只有通过者可进入后续谐波物理解读。数学闭合本身**不是**真实磁场产生谐波的因果证据。

## 3. 阶段C：用已有正负状态重做完整奇偶/相机像元诊断（零render）

**C1. 数量与定义**：v077仅做了zf450的`3D×5行×3列=45`条，修正其总结。利用已保存的`x=-5,+5`留出和`x=0`锚点、正负10/20nm锚点，在D=30/60/100、zf=450/550、`a=5,10,20nm`、每组固定5行×3列上计算**最多270条**奇偶差分；即`3×2×3×5×3=270`。仅已有物理状态组合，不增加新光学配置，不产生新BEM。

同一固定像元`I(-a),I0,I(+a)`定义：

- `odd_half=(Iplus-Iminus)/2`；`even_increment=(Iplus+Iminus)/2-I0`；
- `Iprime=(Iplus-Iminus)/(2a)`；`Isecond=(Iplus-2I0+Iminus)/a²`，均注明nm量纲与只为有限差分估计；
- `Iplus_reconstructed=I0+even_increment+odd_half`；`Iminus_reconstructed=I0+even_increment-odd_half`；分别输出和**原Iplus/Iminus**的误差，而不是和I0比较；
- 记录直接总强度/参考背景、对比度、固定像元物理坐标、状态key和SHA。

判别中心奇偶、离中心变化时不允许随正负位移改变取样像元位置；仅从3组a中的局部有限差分趋势得方法研究结果，不把`Isecond`当连续物理微分的严格极限。若zf550原状态丢失则记录缺项，不为凑270条调用新位置render。

**C2. 相机ROI语义**：`v077_holdout_camera_roi_semantics_fixed.csv`现为24条件＋1伪`D=0,zf=0`T10行。输出真正24条件长表，另单独保存T10。`fine 61:265`经q5像元积分生成41×41**物理像元**，在同一I0分母计算：

- `relIt_camera = norm(ItI_pix(:)-ItD_pix(:))/norm(ItD_pix(:))`；
- `relIt_finegrid`另列作为205×205精细强度诊断，不可重名；
- `relC_camera = norm(CI(:)-CD(:))/norm(CD(:))`；
- `Ccenter_direct/interp`，`Sarea_direct/interp=(65nm)^2 sum(C(:))`及有符号差/绝对差、所有NaN/近零定义。

现发布源码`relIt=norm(ItI(fineROI)-ItD(fineROI),'fro')/...`是精细网格指标，尽管覆盖同一物理区域，不是物理41×41已聚合后相机误差；必须保持两个字段而不是改名冒充。

**C放行**：机器可读的实际记录数、状态覆盖、同一像元的三态重构、中心与参考分母一致；原复场`<0.001`门槛不变。

## 4. 阶段D：复曝光合同真正闭合（非实测曝光）

1. 用同一观测**强度频率400Hz**核对v077全8行的纯正弦解析参照：`sinc(400*0.0001)=0.9973701827725034`，`sinc(400*0.0002)=0.9895056209813083`，与运动类型无关。只有该强度本身是纯正弦时才可将此值视为整条时序的精确曝光响应。
2. 对强度中200/400/800等混合谐波，分别施加真实谐波频率的**复曝光传递函数**，保留`[t_j,t_j+tau]`的时相位因子，不能只按单个幅值比例乘整条信号。
3. 保留已计算的原8个D60/zf450、M200/M400×a5/20、τ=0.1/0.2ms，`tau=0`做基线；旧5左端节点是离散近似。对纯正弦建立精确参考、在本轮最多8条条件按现有锚点进行9节点中点等价积分复核，只有5点与9点尚不一致的分支才进一步用17节点对同一条件复核（额外最多8条）；**新增时域积分评价最多16条**，0 BEM、0 render。报告时间、节点数、复C、幅值差、相位差、输出数值收敛量、单精度地板；不为近零M400值写漂亮的百分比结论。
4. 若工作站资源或原中间缓存缺失导致开销超界，优先完成纯解析闭合与旧8条sinc字段纠错，并将高阶积分标`NOT_EXECUTED_RESOURCE_LIMIT`；不得暗中扩大仿真预算。

**D放行**：全8条已发行解析参照**独立公式**正确；高阶积分执行情况和真正数值增量逐条公开，不能仅将旧CSV换标签称“re-quadrature PASS”。实验真正曝光参数未确认，全部标`SYNTHETIC_TAU_ONLY`。

## 5. 阶段E：在已修复的24张复C400图上做真实的“有限可识别性”筛查

**E1. 保留既有276对，不盲目重算场**：按v076正确中心图的原数组SHA重聚合；校验每张41×41复图的状态key、N/Fs、材料、演示像元和掩码及数值精度；严禁读v075错误中心地图。全24状态无序对276，跨D192，同D84。

**E2. 解释与条件化**：给出对称复图与模值图距离；按是否固定/改变`a,zf,type`分层，列出**跨D最近10对**与每个假设状态的跨D最近邻、同D最近邻。现有数值的关键检验：跨D最小模值距离`0.26465455`，并不等于已知道可分或不可分。缺实验噪声、驱动先验、NA及幅度标定时，不能设置未经授权的“低于X即同粒径”的检测门槛。不得为使不同D接近或远离引入任意复相位/独立归一化因子再说结果物理真实。

**E3. 方法开发建议（纯现有样本）**：从同一24张C图对比三个观测：`|C400_center|`、`||C400_ROI||_2`、整张`|C400|`（复C另作相位条件化诊断）；留出固定焦面/运动类型/幅度与允许这些扰动的最近邻差异。只做现有结果上的条件歧义矩阵和明确命名的可识别性限制，**不模拟真实误检率、不给直径Bias/RMSE、不拟合连续标定曲线**。

**E放行**：结果来自真正v076物理中心C图且pair键/行数完整，数值能从同数组重复计算；异常记录保留，不能由距离大小宣称真实装置已能测径。

## 6. 阶段F：P0及实验参数独立继续

- 冻结真实输入：520nm激光用户确认；原7.29组5000fps/2001帧、400Hz归一化复调制量的数学实现已有验证。未确认：实际曝光与快门时序、NA、总倍率、物方像元、玻璃/水材料和照明几何、磁驱动频率/场幅/相位与实际颗粒运动、样品复折射率/包覆和真实高度。只读检索已有实验记录；空缺不编造，尤其不把演示65nm/px当实验已标定。
- P0矩阵`blocked/unblocked`的 direct/reflected/total 三个完整 Frobenius 门槛各`<1e−10`仍OPEN（历史差`2.58848e−7`）。只继承原**最多一次**安全被动Hook；如果许可证/历史MATLAB会话资源不安全，标`NOT_RUN_RESOURCE_GATED`，不挪动主线。rule7大参考**0授权**，新金球/磁颗粒BEM**0授权**。
- `calibration_valid=false`, `experimental_validation=false`, `detection_validated=false`, `single_particle_diameter=NOT_ESTIMATED`不变；不能因M200有谐波或ROI差异较大便赋真实颗粒身份或绝对尺寸。

## 7. v078冻结成本账本与停止逻辑

| 工作 | v078新增上限 | 依赖与费用说明 |
|---|---:|---|
| 新BEM（磁/金，任意网格） | **0笔** | 旧解决定/物理结果与不完整证据分开，不重算已有物理问题 |
| 额外Fe₃O₄位置复场render | **0侧** | 原30锚点+24留出已存在，键身份真实核对后使用 |
| 新物理粒径、焦面、材料、驱动类型/振幅节点 | **0** | 不扩新物理网格 |
| 真正复数投影解析夹具 | **最多6项** | 纯算术，包含相位/800泄漏/零信号与坏实现注入 |
| 24条旧中心时序的QR复拟合和归档 | **最多24条** | 已有时序优先直接读取，读回不可用条件性重建但不新增物理态 |
| 正确奇偶/有限差分 | **最多270标量记录** | 仅现有±5/10/20及零状态，3D×2zf×3a×5×3 |
| 24条相机ROI语义分离 | **24行＋独立T10** | 从已有holdout复场纯后处理 |
| 合成曝光纯解析核对 | **原8条** | 全部用400Hz观测频率，不凭表头当PASS |
| 合成曝光高阶时序评价 | **最多16条、条件性新增** | 原8条先9节点，必要时最多另8条17节点；0render |
| 可识别性pair比较 | **原276对复聚合** | 不新增观测样本；仅诊断分层和跨D最近邻 |
| 真实BMP新一轮完整回放/新噪声批次 | **0** | 直接复用v073正确FFT与v075/v076模拟图 |
| P0被动Hook | **继承最多1轮，非本轮新授权** | 只有资源安全才执行；rule7禁止 |

*特别说明*：所谓“旧24条时序修复”的运算已经在v074—v077计过成本，不能因版本号改成0历史成本；表中24是本轮最多计算条数，不意味着24次新的BEM。独立解析6＋后处理组的价值在**严谨复算与正确科研解释**而非扩张采样。

**自动执行依赖**：

- A身份/中心不通过：暂停依赖时域的B实际数据与D，仍可运行纯解析fixture、C缓存能读的项目与E已归档pair审计。
- B任意完整复数闭合失败：修复相位/归一化/拟合来源，不能把旧数据贴“TRUE_HARMONIC_PASS”；独立E和物理缺口审查可继续。
- C有限差分/相机误差失败：暂停对应的奇偶/数值稳定性声明，不触发新render。
- D高阶曝光不能运行：保留纯正弦解析检查，标执行状态而非写“收敛通过”。
- E来源与24图不能读：标`SOURCE_MISSING`并停该分支；不转而使用v075偏移中心图。
- F P0资源不安全：停P0，允许主线零BEM/零render的可执行项独立完成。

禁止：为凑24/24、270/270、276/276而跳过错误或新增预算；调整冻结2%、0.001、P0 `1e−10`门槛；无证据宣称校准有效、正式磁颗粒检出、运动实际幅度或真实粒径。

## 8. 单ZIP与GitHub分支交接要求

最终发布**一个**`iscat_v078_return.zip`并在`yyyyzoey/iscat-handoff`新可读`v078`分支交接必要文本和小MAT，返回固定commit。旧错误源/表完整只读保留；本轮必须发布：

```text
iscat_v078_return.zip
  00_README.md
  00_Codex_v078_执行指令.md
  00_全部文本汇总_v078.md
  status.json / review.md
  source/
    run_v078_preflight_identity.m
    run_v078_complex_closure.m
    run_v078_evenodd_camera.m
    run_v078_exposure.m
    run_v078_identifiability.m
    ...测试脚本与实际辅助函数
  tables/
    v078_source_cache_identity.csv
    v078_center_series_consistency.csv
    v078_complex_projection_fixtures.csv
    v078_harmonics24_complex_closed.csv
    v078_harmonic_parts_long.csv
    v078_evenodd_270.csv          # 缺源可少于270，明确状态
    v078_camera_roi24.csv
    v078_T10_true_39nm_negative_test.csv
    v078_exposure_analytic8.csv
    v078_exposure_quadrature.csv
    v078_identifiability276_audit.csv
    v078_identifiability_profile.csv
    v078_cost_ledger.csv
    v078_p0_status.csv
  numeric/
    ...至少1个多相位fixture的完整时序+分解
    ...6条中心时序单/双精度复C对照
    ...部分准确的奇偶/相机ROI样例及真实来源
  logs/
    ...原生MATLAB stdout/stderr、命令行、版本、状态与中断原因
  manifest_sha256.csv
```

**发布检查**：任何CSV行数、列宽、固定键、NaN、复数real/imag必须独立读回；每条`Xbin`与`ΣXh+Xres`以复数公式真正闭合；历史失败保留，不准覆盖；工作站专有大MAT标 `WORKSTATION_ONLY`并给实际路径、字节大小、shape/class/SHA和重读方式。GitHub只发非敏感小MAT与充分的汇总，不公开用户原BMP/私人绝对路径；不以文件名虚构hash。发布后锁提交SHA，读取分支关键文件确认可见。每阶段分开`execution_status / validation_status / evidence_status / scientific_scope`，明确PASS、FAIL、INDETERMINATE、NOT_EXECUTED。

**Codex一句执行口令**：请连续执行本v078唯一指令，从固定v077 SHA和已有缓存接续，先修正复数Dirichlet负频率共轭、缺少的谐波项和`X/C`单位混用，要求24条中心时序在复数DFT层面逐项闭合。然后零render重做真实三态奇偶/41×41相机像元指标，修正8条曝光400Hz sinc，并审核已有276对跨尺寸距离。禁止新BEM、新位置render与未经验证的实验测径。所有可执行任务无须每步等待GPT，完成后统一返回一个ZIP及GitHub v078可读分支。

## 9. 固定来源索引（v077@bfc87300）

- `status.json` Git blob `c6a001e285bbb2b742621164aa83ef343d40042c`：执行者总体声明（不能替代代码/数组）。
- `review.md` Git blob `8e9f3f53c3c1318036726f32279c532a03d9c0e9`：QR及可识别性解释。
- `source/run_v077_B_qr.m` Git blob `bc9e85ccab4d87d2b9c41345128620e552afb511`：LS归一化已修，复数G_N负频率共轭/800/混合单位/无assert问题。
- `source/run_v077_CCD.m` Git blob `69c7a39edc29f8f62abdb00cceecb81e047eb8e9`：真正三态来源、zf450只有45行、错误`recon_err`、205×205精细网格误称相机误差、T10附加伪物理行、276pair来源。
- `source/run_v077_A_identity.m` Git blob `1ac3331cc9f4d5407cb0fba491d207b7a0a62129`：错误的holdout缓存文件名约定与大文件`fileread`。
- `tables/v077_harmonic_fit24_correct.csv` Git blob `059e65c1a961104c5dbb48893b5b812f1e94393d`：24条QR标量；M200 0.989509..0.989727；M400不统一。
- `tables/v077_harmonic_complex_projection24.csv` Git blob `81a5e51fcaf682d7611734e04819b41ce01770b8`：96条四类不全同单位的贡献表。
- `tables/v077_qr_analytic_fixtures.csv` Git blob `95858d1b6694812d3b00bbe7f40eb018ba740b33`：6组解析夹具，仅有限覆盖。
- `tables/v077_even_odd_derivatives.csv` Git blob `bab80e082b8ffd304d12323f8124fb05a8fe76fd`：实际45行，而非450；`recon_err`误定义。
- `tables/v077_holdout_camera_roi_semantics_fixed.csv` Git blob `abbac7c25d091b01b790b03567f260db343390da`：24物理＋1T10假状态；`Itot_roi_relL2`实际上精细网格计算。
- `tables/v077_exposure8_schema_and_quadrature.csv` Git blob `ab8bca702a7278c9c86d18bff4737b272eb0fd62`：M200四行仍按200Hz sinc，M400四行按400Hz。
- `tables/v077_identifiability_276pairs.csv` Git blob `fa9ea447d835d7eb54efbb8b572056c14843f22b`：276对、跨D最近案例及对称归一化。
- `tables/v077_center_series_crosscheck.csv` Git blob `e6e9a6b7862f0fc7c410d25737c1c570ba5dade2`：6行DIFFERS、差约1.99e-10..4.64e-10。
- `tables/v077_source_and_cache_identity.csv` Git blob `4830c10fb298872d0e412853bcf49852c189893f`：来源字节信息与错误的MISSING路径。
- `tables/v077_cost_ledger.csv` Git blob `5bb601c5b695a97ff59f13edbf1aba1f27b8d4fd`：BEM0、render0、QR24、pair276。
- `tables/v077_p0_status.csv` Git blob `adc7d296c1ab05453c03d9012c626039fb4e6a37`：P0未安全执行、矩阵门槛不变。

**链接根**：`https://github.com/yyyyzoey/iscat-handoff/tree/bfc87300d00d245e985e37dbfd3768600a89c427`
