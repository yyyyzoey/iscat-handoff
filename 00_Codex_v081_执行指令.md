# iSCAT / Fe₃O₄ v081 唯一连续执行指令
## 对 v080 的固定提交审查、中心 C400 数值一致性、复数谐波归档与合成曝光真正收敛

> **文档性质**：这是交给 Codex 在用户 Windows/MATLAB 工作站执行的下一轮方案，不是已经完成的 v081 仿真结果。必须在真实前置和预算内连续完成可执行任务；依赖分支失败则暂停该分支，其他独立工作继续，最后统一输出一个 ZIP 与可读 GitHub `v081` 分支。严禁以计划代替已运行结果。
>
> **固定审查对象**：`yyyyzoey/iscat-handoff` 分支 `v080`，commit **`f309176f2f33e70bb75afff938e9c5946704ac62`**。其前驱 `v079@8e9bfbafe3046213b75c251009fc25b050e7f651`。所有证据、源码和缓存都要以真实文件内容与SHA-256固定，不能读取移动HEAD后仍写上述身份。
>
> **已确认的实验输入**：真实激光真空波长 **520 nm**（用户明确确认）；7月29日这组实测帧的分析处理合同为 `Fs=5000 fps, frames=1000:3000, N=2001, MATLAB FFT索引161, k0=160, fbin=399.80009995002496 Hz`。候选正式实验观测量为 `C400=2 X_160/(N*Imean)`的**复数归一化调制对比度**，其模为当前主要分析量，复值/相位留作诊断；旧420Hz未归一化幅度仅为对照。真实曝光时间、NA/倍率/物方像元、磁场激励波形与同步相位、真实批次材料光学常数、真实运动与高度**尚缺独立证据**。Fe₃O₄ Querry `2.349+0.083i`、65nm演示物方像元、NA1.3、5nm间隙及a=5/20nm均不得自动升格为真实实验参数。
>
> **成本与门槛**：新BEM求解**0笔**；新Fe₃O₄位置复场render**0侧**；不增加D/zf/波长/磁场/轨迹/噪声或真实采集。历史2%前向误差、0.001复场留出及P0三矩阵各Frobenius `<1e-10`不放松；已验证的时序DFT算术、满秩QR及复闭合使用下述原数值合同。所有已消耗计算永久留账，不因版本号清零。

---

## 0. 本轮实际审查结论——纠正 v079 的错误，但不要把 v080 全部宣布完成

本轮确实核读了固定提交的 `status.json`、`review.md`、`source/run_v080_harmonics24.m`、`source/run_v080_CDE.m`、原生日志及新表，通过外部逻辑复核行数/列数、所有24条列名键、逐条rank/cond/闭合、原DFT计数到归一化C的换算、已有中心时序与纠偏C400图的交叉差；**没有**在审查端运行工作站MATLAB或取得工作站全部复场数组。

### 0.1 已有可继承成果

| ID | 固定源码/表/日志证据 | 当前裁决 | 限定 |
|---|---|---|---|
| A0 | `v080_harmonics24_validated.csv`真实24行、22列，24行皆`PASS`；键均`D{30/60/100}_zf{450/550}_M{200/400}_a{5/20}` | **接受已报告的满秩24条件重新执行** | 不再把v079历史24 ERROR套用到v080，也不是自动接受动态图中心身份 |
| A1 | 24行rank=9，cond=1.4146，`closure_rel` M200最大约`2.7361e-14`、M400最大约`1.1351e-15`，均严格小于代码原`1e-10` | **接受有限模型的代数复数闭合** | 复闭合含拟合残差，不单独证明谐波物理归因、精度或实验磁响应 |
| A2 | `v080_harmonic_parts_long.csv` 96行、4列，每条对应4种频率，Re/Im均可解析 | **接受长表结构修复** | 仍缺完整残差、截距和原始bin的同单位复数归档 |
| A3 | `v080_time_series_identity24.csv` 24行，但只有series长度、均值、标准差 | **接受时序存在性记录** | 不是逐样本新算/旧存核对，且没有识别与复C400图的来源一致性 |
| A4 | 原v078 270奇偶、24相机ROI、276对离散比较仍可继承；v080新的276对基于v076纠偏复图 | **保留只读原结果** | 不是新物理盲测，更不能宣布实验唯一性 |
| A5 | v080高阶曝光积分报告`NOT_EXECUTED_RESOURCE_LIMIT`，`v080_cost_ledger.csv`新增曝光求积=0 | **高阶曝光尚未做** | `sinc(400*tau)`只是纯正弦解析参照，不能代替时域求积 |
| A6 | v080日志先列24个`Iser`未定义的失败尝试，随后另列24条PASS | **区分旧失败与后续成功试次** | 必须恢复实际运行ID/时间、入口源SHA；不能谎称一气呵成，也不能因失败尝试抹去最终合格表 |

### 0.2 必须修复的新缺口（从固定原值独立复算）

**X1：中心时序与整幅C400图的同一像元没有统一验收。**

源代码 `run_v080_harmonics24.m`：

```matlab
Xbin = sum((I-mean(I)).*exp(-2i*pi*160*(0:2000)'/2001));
Cbin = 2*abs(Xbin)/(2001*mean(I));   % 合法：无量纲幅值
% 与 f76.binAbs 的校核在数值上相当接近
mapC21 = abs(RMap.(caseId).C400(21,21));
% 但 mapC21 仅被输出，未进入正式PASS判断
```

逐行复算表中**真正无量纲**的`2*abs(Xbin)/(2001*mean_I)`与`v076_binAbs`接近，相对比约在0.9999955—1.0000037之间；这是两套单像元时序/DFT值的**有限一致性证据**。但是对于`v076_dynamic_center_corrected.mat`的**整幅复C400图**中心，尤其弱M400出现较大差异。预先记录以下标量审查结果：

| 条件 | 用原DFT和Imean重算`abs(Cbin)` | 发布整幅图中心`abs(Cmap21)` | `abs(Cbin)/abs(Cmap21)` |
|---|---:|---:|---:|
| D30/zf450/M400/a5 | `1.519269221869361e-8` | `1.0327166899415374e-9` | **14.7114** |
| D30/zf550/M400/a5 | `6.767259175945558e-9` | `1.0329366251227157e-9` | **6.5515** |
| D60/zf450/M400/a5 | `4.730568631428596e-8` | `1.0678607509362337e-7` | **0.4430** |
| D100/zf450/M400/a20 | `5.814027419242142e-6` | `5.852805315953447e-6` | **0.9934** |

上述数值**来自已发布标量表算术**，不是重新计算了真实复光场。不能据最大幅值比14.7宣布错误的物理振幅、粒径误差或光学模型失效；也不能只说“肯定是single精度”而不验证。尤其强M200仍存在小差异（例如D30/zf450/a5幅值约1.13%），需要同时核对复杂值、平均分母、四维`Ipix`的中心 `(21,21)`、直接5x5像元积分和`extract_fft_v073`的类型/掩码/舍入路径。**源一致性必须独立于谐波fit闭合判断。**

**X2：`bin161_absC`列实际保存的是`abs(Xbin)`，并非归一化`abs(C400)`。**例如D30/zf450/M200/a5在v080表中`bin161_absC=1.395626809751306e-5`，而同条`mean_I≈0.0052447`，换算出的无量纲对比度是`2.659692467796406e-6`。原表保留历史；新表应分别设置`Xbin_abs_DFT_count`和`Cbin_abs_dimensionless`，并保存复数Re/Im两侧，不以重命名伪造重算。

**X3：`v080_harmonic_residual24.csv`只有表头，无24行。**虽然`closureRel`报告通过，`v080_harmonic_parts_long.csv`已有四谐波，仍缺逐条件`Xbin_complex / Xmodel_complex / Xres_complex / Xintercept_complex`及同一量纲完整证据。下一轮必须用原保存的24条时序和满秩公式补齐，不是再求BEM或重复整幅渲染。

**X4：回归负向测试CSV仍有结构破损。**`v080_regression_negative_tests.csv`表头5字段，`N3`行将`N4_old_matrix_rank`挤在了同一行，含未转义逗号、实际字段错位。status声称“7 negative tests all PASS”与实际独立行数不符。必须重建统一长度的表和真正会阻断批处理的负向断言，而不是复制新的PASS摘要。

**X5：高阶曝光0/16；所谓“v080_exposure16_incremental.csv”实际只有8条而且均`NOT_EXECUTED_RESOURCE_LIMIT`。**保留这8项标记，本轮只在前置通过后执行原已批准、尚未使用的16次**非BEM时域求积**。不可称原5点左求和已经收敛，更不许自动将纯400Hz`sinc`公式当作混合谐波的积分结果。

**X6：来源与执行账本有多轮尝试。**日志先记录`Iser`未定义后记录PASS；代码当前版本没有使用`Iser`变量，说明日志涵盖不同脚本尝试或旧修订。要求给出每次的执行入口内容SHA/时间、成功/失败消耗、最终产物SHA，不能用最终源码替所有旧失败声称执行时相同，也不能凭Git blob SHA-1假装文件SHA-256。

---

## 1. 冻结研究边界、任务依赖与预算

### 1.1 不变的物理与软件参数

- 演示材料：原已验收Fe₃O₄ Querry体材料520nm光学数据，符号和读回仍按既定材料合同；样品实际批次材料状态为未测。演示光路NA、65nm物方像元、介质分层、5nm间隙均保留**演示假设**标记。
- 演示球径`D={30,60,100}nm`，焦面`zf={450,550}nm`，固定横向位移锚点`[-20,-10,0,+10,+20]nm`、历史留出`[-15,-5,+5,+15]nm`。处方运动`M200/M400`、幅度`a={5,20}nm`，位移形式`x(t)=a cos(2πf t)`，不是实测运动。
- 相机演示ROI为原65x65物理像元图中央41x41，即`13:53`；在q5精细场中为`61:265`，中心物理像元的精细块`161:165`；中心MAT索引`(21,21)`。精细场旧错误64:268及键冲突历史不得复活。
- 数据处理`N=2001,Fs=5000,k0=160,kMATLAB=161`，强度先复场叠加、平方、子像元强度平均、逐帧曝光积分，最后FFT归一化。不得使用先平均复场再平方，不能重新估计历史实测掩码产生同名观测量。
- `P0`原三矩阵blocked/unblocked direct、reflected、total Frobenius各`<1e-10`；历史`2.58848e-7`仍OPEN；rule7大参考本轮授权0。

### 1.2 明确预算与停止规则

| 项目 | v081允许上限 | 预算类型 |
|---|---:|---|
| 新BEM解 | **0** | 冻结，不允许 |
| 新位置复场render | **0** | 优先原30锚点及24留出 |
| 已存24中心时序的QR/DFT及缺漏残差归档 | **最多原24条** | 读取/数学后处理，不是新物理采样 |
| 中心数值一致性纯时域双精度纠错 | **先6个固定试点，必要时总计最多24条原条件** | **本轮显式一次性新增的条件性纯后处理额度**，绝不调用BEM或完整位置render |
| 新解析、错输入与CSV负向夹具 | 最多8类小测试 | 不耗新物理状态 |
| 合成曝光16/32节点 | **最多16次**（原8条件×2预设积分规则） | 继承v079/v080未消费额度，不追加tau或物理条件 |
| 既有270条奇偶、24相机ROI、276对 | 只读与选择性数值核对 | 不再重复跑全套 |
| 新D/zf/NA/真实磁激励/噪声/实测样本 | **0** | 不放行 |
| P0安全被动Hook | 原最多1轮，在资源安全时 | 本轮不增加rule7 |

自动推进：先A入口来源/导出单案例→B完整复数归档→C六条件同源精度对照→D高阶曝光（需至少对应4条时域源通过）→E有限观测量稳健性→F物理输入及资源安全支线。不因M400近零失败暂停已经合法的M200和独立数学夹具；依赖失败只暂停受影响分支，记录`BLOCKED/INDETERMINATE`。严禁因历史结果已有24 PASS而绕过本轮的**新增中心一致性**门槛。

---

## 2. A：数据来源、状态与I/O硬门槛（先一个case，不费新光学计算）

### A0. 验证真正的生产对象

需要原生读取（示例路径须在工作站依据当前实际路径检查；绝不从用户私人Windows路径拼造新缓存）：

- `v076_return/numeric/v076_center_roi_harmonic_small_examples.mat`：每个case `series`恰为2001强度样本，`binAbs`为标量，`C400`是拟合标量（**不可**在这个对象上索引`(21,21)`）。
- `v076_return/numeric/v076_dynamic_center_corrected.mat`：24张`41x41`复`C400`图（及8个曝光派生结构），`C400(21,21)`有复数值。
- `v074_return/numeric/render_cache/*.mat`：30个带真实正负文件名的复场锚点，不能用`makeValidName`直接编码正负x；v075留出缓存使用`position_key`，其复场验收继续沿用原0.001门槛。
- `src/extract_fft_v073.m`、`src/render_system.m`、`src/pixel_mean.m`、`src/position_key.m`及本轮将实际运行的新共享工具：记录`which`、内容SHA-256、MAT变量名、shape、dtype、复数/NaN比例、源系统材料/光路/单位、读取实际缓存hash。

### A1. 六种强制失败注入

1. 将数值频率200直接传`%s`生成非ASCII类型键——必须FAIL；正确只允许`M200`/`M400`。
2. 对标量`C400`访问`(21,21)`——必须在类型守卫中被拒绝。
3. 将原始`abs(Xbin)`写入`Cbin_abs_dimensionless`——必须由公式/单位断言拒绝。
4. 将5列表头的N3行挤成更多列、或造空缺乏完整24条结果的residual表——必须拒绝该文档被记为`COMPLETE`。
5. 人为将`RMap.C400(21,21)`换成`(21,1)`或旧fine64:268——必须由坐标及源身份否定测试拒绝。
6. 将旧高阶曝光0条/缺失写成`CONVERGED`，或在未保存和读回结果前计入PASS——必须FAIL。

可再用至多2个纯数学夹具检查`Gn`在接近0的频差极限及复频率镜像共轭；这些不额外产生时域物理条件。代码要实际`assert`或抛异常，不能只用打印字符串当作成功。

### A2. 原生账本

将v080执行记录区分`FAILED_ATTEMPT_Iser_UNDEFINED`（日志确有24次错误）与后续`SUCCESSFUL_RUN_24`（最终24合法表），记录每次的源sha、实际命令、开关、缓存版本、时间戳和异常；不可假定原代码来源完全相同。对于表格/残差修复，不重跑物理位置场，也不将旧失败尝试删除或把所有旧运行归入0成本。

**A放行**：一个固定单案例D60/zf450/M200/a5的源、满秩、复数DFT、CSV列宽、MAT数据读回完整通过；全文件读回规则及负向测试通过后才批量B。

---

## 3. B：保留24条合法QR，补全真正的复数投影归档和单位合同

### B0. 必须区分两种量

令`I_j`为一像元时间强度，`Ibar=mean(I_j)>0`，`y=I-Ibar`。k0=160，t=(0:N-1)/Fs，则

\[
X_k=\sum_{j=0}^{N-1}y_j e^{-2\pi i k_0 j/N},\qquad C_k=\frac{2X_k}{N\bar I}.
\]

`X_k`是原始**DFT count**，`C_k`为无量纲复对比度；`bin161_absC`在v080原表实为`abs(X_k)`，应发布新字段`Xbin_re_DFT_count, Xbin_im_DFT_count, Xbin_abs_DFT_count, Cbin_re_dimensionless, Cbin_im_dimensionless, Cbin_abs_dimensionless`并逐行断言上式。历史v080原文件只读保留。

采用经过v080证实的满秩构造，不再重写另一套相互不一致的B列索引：

```matlab
N=2001; Fs=5000; k0=160;
t=(0:N-1)'/Fs;
if strcmp(type,'M200'), freq=[200 400 600 800]; else, freq=[400 800 1200 1600]; end
B=ones(N,1+2*numel(freq));
for h=1:numel(freq)
    B(:,2*h)  =cos(2*pi*freq(h)*t);
    B(:,2*h+1)=sin(2*pi*freq(h)*t);
end
assert(rank(B)==size(B,2) && cond(B)<1e8);
I=double(series(:)); Ibar=mean(I); assert(isfinite(Ibar)&&Ibar>0);
y=I-Ibar; coef=B\y; residual=y-B*coef;
A_h=complex(coef(2:2:end),-coef(3:2:end));  % 强度正余弦幅值
C_h=A_h/Ibar;                                % 拟合振幅，不多乘2/N
Xbin=sum(y.*exp(-2i*pi*k0*(0:N-1)'/N));
Cbin=2*Xbin/(N*Ibar);
```

### B1. 原复数DFT闭合（维持已用`<1e-10`定义）

对每条频率f_h及其复振幅A_h，使用稳定数值的核函数`G_N(u)=sum_{j=0}^{N-1}exp(2πi u j)`或等价闭式（接近零时数值稳定），则

\[
X_{h\to k}=\frac{A_h}{2}G_N(f_h/F_s-k_0/N)
+\frac{A_h^*}{2}G_N(-f_h/F_s-k_0/N).
\]

截距项`X_int=coef(1)*G_N(-k0/N)`，残差项`X_res=sum_j residual_j exp(-2πi k0 j/N)`。完整**复数**闭合

\[
X_{bin}=\sum_h X_{h\to k}+X_{int}+X_{res}.
\]

输出`Xbin,Xh(f),Xint,Xres`的Re/Im和`units=DFT_count`，再在单独字段对应归一化`Cbin`/`Ch`；不得将单项模值相加。原合同`closure_rel=|delta X|/max(√N||y||_2,预声明绝对尺度)<1e-10`不改；但必须另报实际模型残差`rms`、`||residual||/||y||`、rank/cond，以免将代数恒等式当作物理拟合好坏。

上一轮`v080_harmonic_parts_long.csv`合法的96条逐谐波继续复用；仅缺损或源身份不匹配时才从原时序重算。**必须填满**`v081_harmonic_residual24.csv`：24行含`Xbin/Xmodel_sum/Xintercept/Xres/closure`各自实虚值，原残差RMS和来源SHA。原空`v080_harmonic_residual24.csv`标为`MISSING_DATA_0_ROWS`并留历史。

### B2. 数据与来源一致性分离

对同一case，不许将`f76.binAbs`（从保存中心强度序列计算）等同于`RMap.C400(21,21)`（整41x41动态算子输出），即使多数情况下数值近似。分别发布：

- `source_center_bin_complex`及其单/双精度；
- `stored_qr_series_bin_abs`和`stored_map_pixel_bin_complex`；
- `delta_complex`, `delta_abs`, `relative_if_resolved`, `mean_I_source`, `mean_I_map`, `source_map_shape`；
- 同一case源键、`N/Fs/FFT_dim/bin`、物理像元坐标、复场锚点SHA与渲染/提取器SHA。

对于未超过数值精度稳定尺度的M400弱量，标`NUMERICALLY_UNRESOLVED`，保留全部**绝对差**，不得因相对差大就宣布物理失败，也不能因原“24 PASS”把弱中心量标成可靠。所选稳定尺度必须由C阶段**实际**单/双精度/实现路径差异计算并先登记定义，不能事后挑一个使数据通过的数值。

**B放行**：24条实际合法状态和24行残差表均机器独立读回；谐波、残差和原始bin统一量纲复数闭合；数据身份明确。若少数弱M400仍不一致，保留合格M200结果，仅对该源一致性分支留`INDETERMINATE`。

---

## 4. C：对弱M400和典型M200做**同一强度算子、同一物理像元**精度诊断

### C0. 固定试点，避免按结果挑“漂亮案例”

先固定六个旧条件，不生成新的光学或运动状态：

1. `D30_zf450_M400_a5`（时间序列/图中心比约14.71）；
2. `D30_zf550_M400_a5`（约6.55）；
3. `D60_zf450_M400_a5`（约0.443）；
4. `D100_zf450_M400_a20`（较强M400参照，约0.993）；
5. `D30_zf450_M200_a5`（M200约1.13%幅值差）；
6. `D60_zf450_M200_a20`（强M200对照）。

这六项是根据历史异常预选的**开发诊断**，不是盲验证或误差统计样本。全部24项的进一步检查仅在六项仍有无法归因的差异时依赖扩展，且累计不超过24个既有case。

### C1. 绝对禁止重新求BEM或改变q/光路

从相同的原30个签名锚点，使用当前已确定的中心物理像元fine`161:165`矢量复场（复杂场的`real/imag`保留），在**原N=2001采样的同一处方轨迹**下分别计算以下严格相同的流程：

```
E_sca(x_j) = 原冻结带符号锚点的分段线性复场插值
I_sub = sum_components |E_ref + E_sca(x_j)|^2
I_pixel = 5x5 pixel_mean(I_sub)        # 强度再平均，不是复场平均再平方
I_j (double path) = double精度累计上述强度
I_j (single path) = 严格复现历史实际single落盘路径
Cbin = 2*sum_j(I_j-mean(I))*exp(-2πi*160*j/2001)/(2001*mean(I))
```

**对照路径**：`run_v076_D_qr_center`的1x1中心时序、`run_v076_C_dynamic_center`的41x41动态像元时序、`extract_fft_v073`的4维正确FFT入口；所有中心应为 `(21,21)`，不得使用历史错误列`(21,1)`、旧fine64:268或不同meanFloor。复数值相同物理强度和归一化分母才可比较；对每次输出`mean_I/min/max/range、FFT_Re/Im、源和数组数据类型、源数组SHA、像元区域、差值`。对超过精度地板的分支，检查是否实际把双精度I_j强制转`single`后再FFT，或有不一致的像元归一化/中心坐标/时间轴/缓存源。**不允许**对振幅做事后乘常数或自由相位对齐来凑PASS。

### C2. 近零可信度量

- 对每条件报告`absDelta_C`, `max(abs(single-double),abs(extractor-double),abs(map-double))`及与信号幅值的比；该最大差只是**所测实现之间的数值敏感性诊断**，不是数学上的绝对误差上界。
- 只有当信号显著大于上述数值敏感性尺度（预先冻结如`|C|>10*observed_numeric_spread`的开发诊断定义），才讨论相对幅值、标度或中心信噪；不足时明确`NUMERICALLY_UNRESOLVED_CENTER`，不得用近零数据判断线性/二次性、探测限或真实粒径。
- 若强M200源与动态图仍差约1%，必须追查分母、坐标、数据类型或进入两条入口的实际不同复场信息；不因满足静态2%门槛便自动签“同源FFT一致”。
- 记录完整41x41复图范数与空间能量，固定中心值与离中心量分开。中心偶对称导致M400接近零时，允许讨论**固定ROI的空间模态具有非零信号**这一模型事实，但不得对真实实验自由移动ROI来获得有利结果。

**C放行**：正确对齐同一物理像元和复数FFT分母后，能用保存的实现差异说明上述六项信号数值稳定性。无法解决的保留`INDETERMINATE_NUMERIC_OR_CACHE_IDENTITY`及最小复现，不扩散成全部24条物理失效。

---

## 5. D：真正执行原8种合成曝光的两级高阶求积（剩余16次）

### D0. 不允许新曝光条件

原固定条件是D60/zf450、`M200`/`M400`、a=5/20nm、`tau=0.0001/0.0002 s`，共8个。原`tau=0`与5左节点近似值为历史，只读复用；实际相机曝光时间未确认。采样时刻固定为`j/Fs`，曝光时间区间仍为**合成约定** `[t_j,t_j+tau]`；不得改成中心曝光而只修改标签。

### D1. 解析前置：先用纯正弦而非磁模型

对纯400Hz**强度**余弦，严格解析相机矩形曝光复频响应为：

\[
H_{400}(\tau)=\frac{\sin(\pi400\tau)}{\pi400\tau},
\]

原数值校验：τ100us时幅值`0.9973701827725034`，τ200us时`0.9895056209813083`。这是**纯400Hz强度项**，与处方运动是M200或M400无关。对含基频、二次谐波、插值非光滑处及非线性强度的总时序，需要逐频率完整求积，不能拿该单一sinc给总C400“签证”。测试纯正弦不同初相、τ=0、接近零系数及非整数周期；对解析fixture提前固定绝对/相对误差，做到真正FAIL阻断。

### D2. 原额度下的16次非BEM评价

原8个条件固定两种节点密度：`n=16`和`n=32`的**合成曝光区间等距中点求积**，共8×2=16个新的时域评价（无新位置render）。同一`t_j`、τ、材料、q、像元、轨迹、参考场，用当前正确且可复用的5个复场锚点构造子时刻强度。每帧先对5x5子像元强度求平均，再对曝光子时间做平均。不能将移动复场先做时间平均后平方。可以计算完整固定41x41 ROI，也可先中心；若只中心，必须明示`CENTER_ONLY`，不得称整幅图已验。

导出每个条件`old5_left_Ccomplex`, `mid16_Ccomplex`, `mid32_Ccomplex`, `delta5to16_complex`, `delta16to32_complex`, `phase_if_resolved`, `norm_of_Imean`, `num_floor`, `sinc_ref_only_for_pure_sine`, `source_keys`, `error_if_any`, `status`。**只比较不同真实数值求积结果**才可讨论收敛趋势；16与32接近是局部收敛证据，不是严格误差上界。如果单精度中心幅度处于精度地板以下，报告绝对差并标`NUMERICALLY_UNRESOLVED`，不能由75%之类相对变化推断曝光物理效应。若资源不足，按顺序4个M200→4个M400；保留尚未执行的正确状态，不挪额度到BEM。

### D3. 成果等级

- `EXPOSURE_FIXTURE_PASS`：独立纯正弦解析算子验收；
- `FINITE_QUADRATURE_INCREMENT_OBSERVED`：16/32有真实数值、在当前样例稳定；
- `INDETERMINATE_PRECISION`：中心太弱或16/32尚不收敛；
- `NOT_EXECUTED_RESOURCE_LIMIT`：没有真实求积结果。

无论结果多好，未知真实相机τ时均不能把此表叫实验曝光误差已标定。

---

## 6. E：原24张C400复图的观测量稳健性与粒径歧义（只读）

- 复用v076**正确物理中心**的24张41x41复C400图，并从每张计算中心复数幅值、固定ROI的`||C||_2`、`||abs(C)||_2`、固定空间分布的正则归一化范数；**报告所有归一化分母**，不把原始DFT计数写为C、也不把平均强度/演示物方像元当实测标定。
- 继承原276对，其中跨D=192、同D=84；不可再用已撤回v075偏移中心图。固定对称距离`||Ci-Cj||/((||Ci||+||Cj||)/2)`分别计算复图和模图，仅在同一固定坐标和掩码上比较。
- 如果复图与中心时序在C阶段存在未解释不一致，则配对结果维持`HISTORICAL_DEVELOPMENT_SCREEN`，不升级为可靠尺寸标定。对相位参照未知的实验，复图只作方法开发；正式候选观测为`|C400|`。
- 关注原最相近跨D模图组：D30/zf550/M200/a20 与 D60/zf450/M200/a5，历史对称距离约`0.26465`。这只是**有限已测模型参数假设的近邻**，不是已知噪声条件下的统计不可分辨，也不能作为新训练样本；原D、a、zf、运动模型的耦合和实验缺失不允许被隐含优化掉。
- 需要形成的不是新分类准确率，而是 **`observable_qualification.csv`**：每种候选量的数学定义、动态强度来源、数值稳定性等级、未知物理参数依赖、允许进一步反演的条件和禁止的外推结论。**本轮不创建拟合D的正式标定曲线、检测FPR或绝对单颗粒测径误差。**

---

## 7. F：真实输入、P0和执行安全

- 已确认：520nm实验激光，7.29脚本对应5000fps和400Hz目标，2001帧bin161是已接受的解析提取定义；`Imean`有效掩码与全幅阈值沿v073正确结果，不在局部ROI重新估计。实际曝光、物镜NA、物方像元、总放大倍率、磁驱动波形/触发时间/相位参照、真实磁颗粒光学常数/核壳结构、真实位移/高度仍是缺失或未证实；可只读检索工作站旧实验记录及相机元数据，不能联网猜参数。
- `P0`历史同一离散blocked/unblocked direct/reflected/total三矩阵各`<1e-10`未达到，历史差约`2.58848e-7`；未知MATLAB历史会话和许可证瓶颈时不能擅自清理/杀进程，只有资源安全和进程归属都明确才继承至多1次只记录被动Hook；**rule7大型参考=0授权**。
- 任何本轮数学或合成曝光通过，不得把`calibration_valid=false`、`experimental_validation=false`、`detection_validated=false`、`single_particle_diameter=NOT_ESTIMATED`改成真。没有同步磁驱动条件与物理参数，不能把400Hz实验峰叫“磁颗粒2f已证明”。

---

## 8. 唯一ZIP / GitHub发布与验收

### 8.1 必需文件及最低字段

```
iscat_v081_return.zip
  00_README.md
  00_全部文本汇总_v081.md
  00_Codex_v081_执行指令.md
  status.json / review.md / manifest_sha256.csv
  source/
    ... 实际执行的input&negative tests、中心对照、复数DFT/QR、曝光16/32、观测量资格脚本 ...
  tables/
    v081_execution_attempt_ledger.csv
    v081_cache_identity_and_source_hashes.csv
    v081_regression_negative_tests.csv
    v081_harmonic24_units_fixed.csv
    v081_harmonic_parts96_verified.csv
    v081_harmonic_residual24.csv
    v081_center_series_map_precision24.csv
    v081_center_precision_pilot6.csv
    v081_exposure_pure_sine_fixtures.csv
    v081_exposure8_quadrature16_32.csv
    v081_observable_qualification.csv
    v081_physical_input_readiness.csv
    v081_p0_status.csv
    v081_budget_ledger.csv
  numeric/
    ... 小型真实中心时序、双精度计算、复数C_bin/Cmap与曝光夹具MAT；
        大锚点及完整复图若留工作站，写真实变量shape/hash/WORKSTATION_ONLY ...
  logs/
    ... MATLAB原生日志、不同源码版本和执行时间、每条实际失败堆栈、读回记录 ...
  history/
    ... v079原ERROR和v080首次Iser失败、旧空residual表、旧单位错列 ...
```

所有CSV使用UTF-8、固定schema、**每行列数=表头数**、正确引用带逗号文本、唯一case键、有限数字与明示NaN状态；先保存原数组后导出，导出失败只补导出；所有声称PASS的数值必须从已保存源读回且校核成功。大MAT不上GitHub时填实在的Windows路径、字节数、SHA-256、变量名/shape/dtype及读取命令，不可用Git blob SHA-1冒充文件SHA-256。

### 8.2 执行和科学状态**分离**

每阶段/每条件分别保存：

```
execution_status: NOT_STARTED | RUNNING | COMPLETED | FAILED | INTERRUPTED | NOT_EXECUTABLE
validation_status: PASS | FAIL | INDETERMINATE | NOT_EVALUATED | NOT_EXECUTED_RESOURCE_LIMIT
source_evidence: COMPLETE | PARTIAL | MISSING | CONFLICTING
scientific_scope: ANALYTIC_FIXTURE | PRESCRIBED_DYNAMIC_OPTICAL_DEVELOPMENT |
                  EXPERIMENTAL_FFT_ARITHMETIC | EXPERIMENTAL_PHYSICAL_VALIDATION_NOT_ESTABLISHED
```

A正式导出不通过→暂停依赖的B/C；B复数闭合有局部失败→只暂停相关观测量解释和D，独立输入/P0状态可以继续；C数值精度不足→仍允许做数学曝光fixture，但相关弱M400物理归因留待验证；D资源不足→保存未运行状态，不消耗新render也不许写PASS。全部预算内、前置通过的任务应**连续执行**，不需要每一个case返回GPT。结束统一**单ZIP+固定v081分支SHA**，并从发布提交回读核心状态/表格，严格审核实际行数，不再出现只有表头的“完整”表。

**最终成功门槛**：成功修复v080三个发布缺口（原始DFT列的单位、24行复数残差表、负向回归表），真实给出至少6个预先固定的中心与动态图同源双精度对照；如前置和资源允许，完成原8条件×16/32节点高阶曝光数据。对弱M400如无法由原数组说明精度，明确给`NUMERICALLY_UNRESOLVED`，不为凑数宣布所有观测量可靠。保留继承结果、不在本轮输出任何实验绝对粒径。

---

## 9. 固定提交证据索引（必须回读原源，不能仅从review复制结论）

所有链接以 `https://github.com/yyyyzoey/iscat-handoff/blob/f309176f2f33e70bb75afff938e9c5946704ac62/` 为前缀：

| 源文件 | Git blob SHA-1 | 本次能直接支持的范围 |
|---|---|---|
| `status.json` | `51bb3e3e7d2249f8f15adc938b93ac926b8887c0` | 执行者报告24/24；不代替源数组身份 |
| `review.md` | `7feb536758c0ca00ddb237a73eb4306d28ec0f4a` | 承认高阶曝光未做 |
| `source/run_v080_harmonics24.m` | `4adb616edb1d12932fd0bcb58b82819c7169d316` | 真正满秩、复数GN、成功计数与未比较的地图中心 |
| `source/run_v080_CDE.m` | `3f8a39a17d1fb29d96846ee0c8c006eae31dd61c` | 276旧状态重筛和未执行高阶曝光表 |
| `logs/matlab_native_run.log` | `258bc678abf61ee7870c3e560f4bfc27a9696d81` | 历史Iser异常24次+后续24条成功记录，需拆分运行来源 |
| `tables/v080_harmonics24_validated.csv` | `a14de8d11848bf87977f69b77ecfd21e0e74ab7a` | **24行结构PASS、rank/cond/closure及原Xbin错名字段** |
| `tables/v080_harmonic_parts_long.csv` | `34823911cd9a54060288ff211e10ba3effc67fca` | 96行4列合法复谐波表 |
| `tables/v080_time_series_identity24.csv` | `c7825ec2276296e01130ddc5e25a8ab6fa58e581` | 24行len/mean/std，非逐样本强身份校核 |
| `tables/v080_harmonic_residual24.csv` | `9075dceea76c56aa7936fd34d5b87d0d67970f98` | **只有表头，0行** |
| `tables/v080_regression_negative_tests.csv` | `f46ff3c587696fa5ef007d8776d479090650bd6c` | **N3/N4混在一行；结构损坏** |
| `tables/v080_exposure16_incremental.csv` | `ea58d7776973d64d44afaf91b327fd7e2507a6b3` | **8条件全`NOT_EXECUTED_RESOURCE_LIMIT`、0次新高阶求积** |
| `tables/v080_identifiability276_audit.csv` | `3b39fc5b63bac23596f7bafc81e95c89b0c38bcd` | 276对有限处方模型距离筛查 |
| `tables/v080_cost_ledger.csv` | `422354b0c6b0b5f976d0e5f63e2c2215665faeb4` | 新BEM0、新位置render0、高阶曝光0 |

**交给Codex的唯一执行口令**：

> 请完整执行这份v081唯一指令，从v080固定提交及真实工作站缓存接续。保留正式通过的24条满秩QR与96条谐波贡献，不重复已有BEM/位置render；先纠正原DFT误命名为C400的单位、填满24条复数残差证据并修复N3/N4坏CSV，再用六个固定条件核对同一中心时序与41×41动态复图的数值一致性，追查弱M400的单/双精度误差，必要时只扩展到原24个时域条件。前置和资源允许时按原未用16次额度完成8个合成曝光条件的16/32节点高阶积分；不添加真实物理参数或粒径节点，不降低旧门槛，不输出未经标定的实验绝对粒径。所有依赖允许的任务自动连续执行，失败保留证据，最后统一交一个ZIP和可读v081分支。
