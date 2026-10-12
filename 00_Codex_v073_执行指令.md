# iSCAT v073 唯一连续执行指令：v072真实FFT回放纠错、400 Hz归一化复调制对比度验收与520 nm实验接口

> **文件性质：下一轮给Codex的执行授权，不是已完成报告。** ChatGPT负责固定提交审查、科学和统计门槛，Codex负责工作站MATLAB原生执行、原始数值归档与一份返回ZIP。满足前置条件后**连续执行全部可行任务，不必每小步请示GPT**；失败只暂停有依赖的分支，其余可继续。
>
> **锁定审查源**：`yyyyzoey/iscat-handoff`分支`v072`提交 `e1abfed0dca0acf9e656f39775d8274ceb561a0c`，不能在执行中悄然读取移动的HEAD。
>
> **用户最新确认的实验事实**：激光波长 **520 nm**。此字段在新的实验合同中记为`USER_CONFIRMED_2026-10-12`。其余物镜NA、实际总倍率、物方像元、曝光、磁颗粒批次光学常数、单颗粒高度/运动轨迹及驱动同步相位等**尚非已确认实验量**。现有520 nm Fe₃O₄（Querry体材料`2.349+0.083i`）是文献/演示模型，不能擅自提升为该批磁颗粒实测标定。

---

## 0. 本轮科研决策（用户已授权ChatGPT代选）

### 0.1 正式主观测量，**选择400 Hz归一化复调制对比度**

- **主观测定义**：从同一像元时间序列的复FFT系数得到无量纲`normalizedComplexContrast400`，反演前主要使用`normalizedAmplitudeContrast400 = abs(normalizedComplexContrast400)`；始终保留复系数、相位、时间均值、有效像元掩码及所用时间起点。
- **频率选择**：`Fs=5000 fps`、排序后`startFrame=1000, endFrame=3000`（两端包含；`N=2001`）、目标`400 Hz`、0-based频点`k0=160`、MATLAB频点`k=161`、实际箱中心`399.80009995002496 Hz`。历史7.29结果中的399.8001 Hz与此一致；早期实验记录的200 Hz磁驱动及其2f分量是选择400的**动机/待实验核对记录**，不能把“一定物理来自磁颗粒”作为先验结论。
- **复数约定**：

  \[
  \bar I(x,y)=\frac1N\sum_{j=0}^{N-1}I_j(x,y),\quad
  X_k(x,y)=\sum_{j=0}^{N-1}[I_j(x,y)-\bar I(x,y)]e^{-i2\pi k_0j/N},\quad
  \widetilde C_{400}(x,y)=\frac{2X_k(x,y)}{N\bar I(x,y)}.
  \]

  非DC、非Nyquist时使用系数2；有效像元按当前实际脚本`test_with_contrast.m`：`meanFloor=0.01*median(timeMean(timeMean>0 & isfinite(timeMean)))`，`validMask=isfinite(timeMean)&timeMean>meanFloor`；**无效像元用NaN+mask保存，不能填0计入候选/统计。**原1%规则是当前源码版本的一部分，而非已独立优化的实验阈值，冻结为本轮回放协议，不得按结果调到更好看的值。
- **保留420 Hz作为单独对照通道**：旧`test.m`的`420 Hz`（MATLAB箱169，419.79010494752623 Hz）只作来源对照和频谱诊断，不是主标定观测，也不能通过比例变换冒称已与400 Hz等价。
- **相位地位**：无磁驱动同步触发/参考时，FFT相位依赖时间零点；相位只能作为内部诊断及未来同步分析，不作为绝对磁响应相位。无论选哪个处理量，**静态C(D,zf)不能直接标定400 Hz幅值**；磁驱动运动/磁光机制、时间采样、曝光和实际同一提取器仍是必需的前向链。
- **光学波长**：实验合同固定`lambda_experiment_nm=520`（用户确认），而演示模型也曾使用520；只能说明这一个输入吻合，不能据此认定演示NA、65 nm物方像元、5 nm间隙、1 ms金球相机曝光、Fe₃O₄体材料代表实验。

### 0.2 科学上的禁止误读

不能把`|C400|`亮斑直接当单颗粒；不能把未验证的400 Hz来源直接归为磁运动；不能从一次幅值同时无约束反演直径、轴向高度、运动幅度及材料；不能把归一化振幅当作已有几何粒径真值；不允许用商用标称100 nm自动校准得到“绝对粒径”。

---

## 1. v072固定提交审查裁决（必须在下一轮status保留）

| 条目 | v072公开源可支持的事实 | 审查结论及处置 |
|---|---|---|
| 版本与源 | 新增`run_v072_fft_fixtures.m`,`run_v072_replay.m`,`run_v072_reconcile.m`及两提取器来源合同；提交有真实文件 | 接受来源固定与脚本定位 |
| 双脚本 | `test.m` SHA-256 `fdc918e691b13b33cbae8b32ecaacd1e63ec27be3e23b61b0701d0e595aea684`；`test_with_contrast.m` SHA-256 `d08575b1e860e09f29c74652442a77b721039c6e32368fe76d2c5c63143ea3aa`；400/420单位和归一化不同 | 接受两种源定义，主线按0.1选400归一化；不篡改旧脚本 |
| 箱索引 | N=2001,Fs=5000；400→161/399.80009995 Hz，420→169/419.79010495 Hz | 算术正确；它**不证明**回放FFT实际沿时间计算 |
| 解析测试 | CSV报告12/12 `PASS`，其中部分采用独立直接DFT参考 | 作为已报告的小例保留；**不接受“整个提取器已全流程验收”**，F07/F09/F10/F12有具体缺项 |
| 一组真实BMP | 报告本机5000张352×296、8-bit BMP，帧1000:3000已读；`run_v072_replay.m`有输入读取与写出日志 | `REPLAY_EXECUTED_BUT_FFT_AXIS_INVALID`；撤销回放数字的频域测量资格，保留输入盘点 |
| v071侧数组 | 工作站24份原C缓存复核、K03/K06与v068标量一致；P_common/F_angle缺原`sol`不可执行 | 有效历史静态数值保留，不因FFT回放缺陷重算BEM |
| v072受控清单 | `controlled_ledger_reconciled.csv`有24侧事件，但D_nm/zf_nm在24条中为空；`render_source_sha256`、`wrapper_source_sha256`表头与实际值互换 | `LEDGER_SCHEMA_SEMANTIC_FAIL`，必须从已保存侧cfg更正，仅重导出，不重render |
| 静态可识别性 | 仅用三尺寸×九焦面的演示静态Ccenter/Sarea对照，排序有变号/变化 | `STATIC_DEMO_SCREENING_ONLY`，不是连续D单调证明或动态标定 |
| P0 | 历史blocked/unblocked相对Frobenius`2.58848e-7`，原门槛`<1e-10`，Hook未跑 | 保留OPEN；大rule7参考不得启动 |

### 1.1 **致命问题：v072真实回放根本没有对时间轴作FFT**

`source/run_v072_replay.m`实际创建的是三维数组：

```matlab
stack = zeros(H,W,N,'single');     % H x W x TIME
...
timeMean = mean(stack,3);
signal = stack - timeMean;
fftR = fft(signal,[],4);           % BUG: 第四维长度为1
X420 = fftR(:,:,k420);
X400 = fftR(:,:,k400);
```

官方MathWorks `fft(X,[],dim)`文档明确规定：**若dim大于ndims(X)，则原样返回X。**因此这里`fftR`仍为三维时域去均值帧，`fftR(:,:,161)`/`(:,:,169)`拿到的是第161/169个**时间样本的空间灰度切片**，不是399.8001/419.7901 Hz复系数。所报告的`chainA_amp420_max=3.47769e-05`、`chainB_|Cf|_max=0.0615005`、mean/有效掩码等中，mean和mask可由原输入单独重验，但两项“频率幅值、相位及其统计”**不能用于正式研究**。不能只改列名或在原FFT结果中乘系数补救，必须沿真正时间轴重新读回同一2001帧计算。

参考：`https://www.mathworks.com/help/matlab/ref/fft.html`；v072固定源码及回放表。

源版`test_with_contrast.m`读写四维`imageStack(y,x,channel,time)`并使用`fft(signalStack,[],4)`，这一源版维度语义与适配器的三维不同；**不能因适配器错误就宣布原版源脚本错误**。

### 1.2 **解析夹具的“12/12 PASS”尚有明确漏洞**

- F07所谓“时间起点相移”中，`n0=1000`传入`runFixture`，但局部代码只读取n0，信号`t=(0:N-1)/Fs`没有按n0平移，甚至未用于实际数据；它事实上不能检验预期相位旋转。
- F09用`C=complex(zeros(...))`填无效像元，未复现源`test_with_contrast.m`的`NaN + validContrastMask`语义；所验证主要是掩码布尔值，不是源链完整一致。
- F10“RGB权重独立对照”的manual与chain用相同表达式，能够做小幅一致性检查，不足以证明独立实现或实图RGB→灰度路径全链相容。
- F12只测试假设`tau=0.0001 s`的解析矩形曝光sinc比值；不是当前装置真实曝光，也没有测试实验图像读取的时间戳和曝光积分。
- `tables/fft_analytic_fixtures.csv`的F12行`phase_wrapdiff`含实际`U+0000`控制字符（源于`printFix`把数值`pdiff=0`交给`%s`），违反干净CSV输出要求；应重导出，不须重做12个物理测试。
- 上述不意味着其余直接DFT/FFT数值全错；应逐fixture保留通过的证据，把F07/F09/F10等缺项订正为**测试覆盖不足**而非按历史全部FAIL，更新后再验。

### 1.3 `controlled_ledger_reconciled.csv`来源字段错误

`run_v072_reconcile.m`使用

```matlab
ci=find(strcmp(cid,sprintf('K%02d',1:6)));
```

而`sprintf`返回拼接字符串，不产生`{'K01',...,'K06'}`列表；`ci=[]`造成已发布24行的`D_nm,zf_nm`为空。此外`fprintf`顺序把`S.evi.code_sha256`写入`render_source_sha256`，又把`which('render_system')`的SHA写进`wrapper_source_sha256`，两列定义反了。应从当前`S.r.cfg.particle.diameter_nm`及`S.r.cfg.focus_nm(3)`、side文件哈希/实际签名重新导出并用单位测试审计24键，**不能凭空插入旧行或重render**。

---

## 2. 阶段A：先修正确时域FFT实现、最小失败夹具（最高优先级；BEM=0）

**[放行条件]** 在一个干净MATLAB进程中，锁定上述提交及真实`test.m`、`test_with_contrast.m`两脚本源SHA；确认7.29原BMP只读可达，盘点数据与运行中进程，不清理不属于任务的历史MATLAB进程。正式建`extract_fft_v073.m`（或等价纯函数），不修改用户两份原脚本；不使用动态`genpath`加载历史同名类。

**[必查项]**

1. 对三维`stack(H,W,N)`，显式使用`fft(signal,[],3)`；对四维`stack(H,W,channel,N)`，显式`fft(signal,[],4)`。编写**故意错误FFT轴的负向测试**，应当识别`dim > ndims(signal)`并中止，不能默默得到看似正常的幅度。`N=size(stack,timeDim)`必须等于2001，频点索引与频率范围须有断言。
2. 输出合约必须区别`X_k`（未归一复FFT），`A_k=2|X_k|/N`（单边灰度幅值），`C_k=2X_k/(N Imean)`（无量纲复调制对比度）、`abs(C_k)`、`phase(C_k)`、`timeMean`、`validMask`、`actualFreq`,`k`,`Fs`,`frameStart/End`、`source_sha`, `input_sha`。无效背景像元C应为complex NaN；不把无效像元当零噪声或未检出。DC/Nyquist另按源版判系数1。
3. 与**真正四维源版**在一个预先固定小ROI上交叉验算；再由独立逐点双精度直接DFT验证选定原像元复系数（含实部、虚部、模、相位和单位）。均值扣除、帧排序、灰度线性映射、mask一致。差异容差在运行前写入（建议单精度比较`|ΔC|≤1e-7+1e-5|C_ref|`；零信号只按绝对容差；相位仅对强信号、模不近零的点比较并≤`1e-4`rad），绝不按实际值临时放宽。
4. 内存资源受限时允许**两遍流式算法**：第一遍求与源版一致的时间均值（精度来源明示），第二遍按已冻结`exp(-i2πk0 j/N)`累加复DFT，避免为352×296×2001复制超大FFT张量；至少在一个41×41小ROI对照MATLAB正确第三维FFT。**禁止“流式算法跑出来了”但没有数值对照就升级正式合格**。
5. 保留`N=2001,Fs=5000`和用户激光`lambda=520 nm`；这些是不同量纲的合同。实际**曝光时长仍MISSING**；不要因为帧间隔0.2 ms就默认曝光等于0.2 ms，更不能套金球合成1 ms。

**[A失败处置]** 若时间轴、索引或源语义任一失败，停止真实回放和后续对比；先在允许的两次轻量修复内纠正、保存最小复现。K缓存归档、材料合同、P0安全盘点可继续。**新BEM=0**。

### MATLAB 关键断言模板（仅示意，Codex须按真实数据类型实现）

```matlab
% 3-D grayscale stack: [height,width,time]
assert(ndims(stack)==3 && size(stack,3)==2001);
N=size(stack,3); Fs=5000;
k0=round(400*N/Fs);  % 160, zero-based
k=k0+1;             % 161, MATLAB one-based
assert(k==161 && k>1 && k<=floor(N/2)+1);
Imean=mean(stack,3);
signal=stack-Imean;
assert(size(signal,3)==N && size(signal,4)==1);
F=fft(signal,[],3);                 % 必须是dim=3
X400=F(:,:,k);
valid=isfinite(Imean)&Imean>0.01*median(Imean(isfinite(Imean)&Imean>0));
C400=complex(nan(size(Imean),'single'),nan(size(Imean),'single'));
C400(valid)=2*X400(valid)./(N*Imean(valid));
actualFreq=(k-1)*Fs/N;
assert(abs(actualFreq-399.80009995002496)<1e-9);
```

要求对每个四维输入也进行时间维度测试，不可让三维代码沿第四维原样返回而仍报PASS。

---

## 3. 阶段B：修补解析测试覆盖及CSV序列化（零BEM）

**[放行条件]** A的FFT时间轴和小ROI正确复算通过；原12个v072夹具和数值保存继续保留原样供历史审计。

**[新授权的定向夹具上限≤8]**，只填源码已找到的缺口，不制造新的物理采样或噪声统计：

1. `AXIS_FAIL_NEGATIVE`：已知`[H,W,N]`的目标时间谱，错误`fft(...,4)`必须被守卫拒绝；正确`fft(...,3)`匹配解析系数。
2. `3D_VS_4D`：同一原灰度时序重排成`H×W×1×N`，正确dim3/dim4复数输出一致（源版对照）；保留长度N与单位。
3. `TIME_ORIGIN`：真正改变输入采样起始时间（2001帧窗口/指定n0），比较幅值不变和**由频率/时移算出的相位变化**；不能再只传未使用的n0字符串。
4. `MASK_VALUE`：低背景、零背景、NaN/Inf像元；验证无效mask和源版complex NaN，而不是只验掩码。
5. `RGB_INDEPENDENT`：真正用不等的RGB通道模拟读图到`im2single`/灰度转换，独立手算并校验权重。
6. `OFF_BIN`：真实400 Hz非箱中心信号同399.80009995 Hz箱的振幅与相位偏差；作为泄漏诊断，不事后“校正”正式观测。
7. `EXPOSURE_ANALYTIC_ONLY`：清楚写`tau`仅合成假设；验证中心时间和起始时间两种曝光相位惯例，不冒充实测曝光。
8. `IO_CSV`：正确序列化phase/NaN/未定义和UTF-8，强制拒绝NUL或其它控制字符；F12不再用`%s`写数值导致`U+0000`。

每个用结构化PASS/FAIL及来源和失败值记录；单精度阈值沿A预先声明的范围，不因以前表报12/12就跳过失败测试。`F07`旧PASS改登记`NOT_ACTUALLY_TESTED_ORIGIN_SHIFT`直至新夹具闭合。展示统计时将“测试数目”与“单元测试覆盖的实际源操作”分别说明，不以12/12证明实测数据频谱正确。

---

## 4. 阶段C：**纠正同一组真实7.29数据的400 Hz主回放**（最高优先级；只许1组旧数据）

**[放行条件]** A/B关键时间轴、版本、单位、mask前置通过；已盘点本机7.29原文件且与v072记录一致；一个新MATLAB会话中运行，不能依赖v072错误的`replay_729_frames1000_3000.mat`作为复FFT输入。

**[必查项]**

- 只读原**同一**5000帧BMP目录，排序后仍选第1000–3000帧、**N=2001**，检查首/末文件名与实际读到的矩阵尺寸/灰度和定标。对有用的源输入目录建立按序文件名+大小+至少样本SHA清单（能负担时对2001帧SHA一次性读取归档）；不把真实原始帧私自上传公共GitHub。
- 正式只用`test_with_contrast.m`定义的**400 Hz**通道作为主输出，保存完整`X400,C400,absC400,phase400,timeMean,validMask,bin/metadata`；同步计算**420 Hz副通道**`X420`供来源对照，用一遍正确时间FFT/流式DFT完成，不再当成新的实验样本或单独“重复验证”。
- 在至少12个预声明像元（含高均值、低均值、图像边缘和一处固定ROI）做**直接DFT**与正确FFT复数对照。可进一步在原版四维实现的41×41小块做逐像元一致性检查；两者都从真实输入帧独立重建，**不可用同一错误适配结果自证正确**。
- 有效掩码来自`meanFloor`和有限性；无效复C存NaN、mask=0；所有min/max/mean只在有效像元上计算，并提供无效计数、量纲、频点和近零统计。不得像v072那样将无效像元赋0，再把全图平均当测量背景。
- 同时保存错版v072结果的哈希并`INVALID_FFT_AXIS`隔离，不能覆盖到历史原路径。新、旧同名数组/表禁止混用；新输出带`CORRECTED_FFT_TIME_DIM3`和唯一配置/源码/原帧清单哈希。幅值或空间形态与v072不同是**预期需解释的纠错结果**，不以接近v072错误数值作为验收。
- 频谱背景诊断仅限已选时间段、预先固定的目标箱周围（如MATLAB k=158:164）及420箱169；记录复数、幅值、谱基线及是否出现一致空间结构。它是开发诊断，**不是新检测阈值或独立假阳性率验证**。单一亮点/较大模值不证明颗粒或磁场因果；如有原已识别轨迹和ROI来源，最多匹配有限既有候选并明确非独立。
- 不因数据可读而输出任何单颗粒绝对直径。没有真实磁激励相位/运动幅度、高度、有效NA/曝光和颗粒批次材料约束时，只写`REAL_400_HZ_OBSERVABLE_COMPUTED`，`calibration_valid=false`、`experimental_validation=false`。

**[失败处置]** 数据哈希/排序、时域处理、源脚本、直接DFT/FFT差异、低背景和数组保存任一失败，保留失败材料和错误截图/日志；仅允许本轮一组纠错回放，不因数值不美观而另选数据集、另选强信号帧或调整频点阈值。若资源无法存完整栈，可在同一帧集上改成**双遍流式DFT**并重新对照；同一采集只有一组实验样本，不把算法重算增加为新独立n。

---

## 5. 阶段D：正式观测量的资格诊断、静态模型与动态桥接边界（BEM=0）

**[放行条件]** 阶段C产生可复核的正确400 Hz复调制对比度；v068/v069现有三尺寸静态表与身份冻结。

1. **实测谱证据**：仅对已明确来自真实帧、来源合法的固定有限像元/ROI，报告复频率幅值和邻近箱背景分布、局部空间相关、帧顺序与相位起点；统计量和ROI预先写入，拒绝只挑最亮像元建立粒径曲线。没有独立磁场开关/参考时，统一标`ASSOCIATION_ONLY_NOT_CAUSAL_MAGNETIC_SIGNAL`。有已有前期13轨迹等历史候选时可做一份探索匹配，不能冒充新的盲测。
2. **静态光学库定位**：演示Fe₃O₄三尺寸30/60/100 nm、520 nm、三尺寸×九焦面的`Ccenter`/`Sarea`可作为光学前向缓存和可识别性预检；**焦面变化不是颗粒真实z(t)位移**，不能从已有zf采样直接构造“200 Hz驱动高度轨迹”，也不能将静态有符号S直接换算为`|C400|`。演示λ与实验λ同为520只是单因素对齐。
3. **极小的时域观测算子验证（可选，≤4组纯解析小序列，无BEM）**：在明确写作`ANALYTIC_OBSERVABLE_ONLY`的输入上给定人为的、已知的**强度**正弦调制（不冒称磁颗粒运动），依照固定时间平均、可选假设曝光积分、5000 fps、N2001及同一400 Hz提取函数计算输出，验证振幅/相位/单位。只验证`time series → FFT contrast`算子，**不能**作为`S(D)`曲线点或任何纳米颗粒物理验证。
4. **下一阶段磁颗粒物理仿真的必要输入表**：从工作站实验记录只读恢复实测/用户报告/文献/假设/缺失的波长(520, USER_CONFIRMED)、相机曝光与总倍率/NA、像元物方尺度、磁驱动频率与波形/场强、单颗粒轨迹与高度约束、材料批次、磁运动机制。只有可验证的运动/场模型和实验参数成立时，未来另行授权独立的`I(t;D,η)`模拟，再经过曝光与同一400Hz提取函数建立条件性的`|C400|(D,η)`，进一步检查可逆区间与留出样本。**本轮不给新BEM或密库预算。**

**[失败处置]** 发现不能区分磁响应与照明/机械/相机谱峰则明确记录`NOT_IDENTIFIED`，不能改用420或静态积分以获得“结果”。动态物理输入缺失则完成可执行的解析观测算子工作，留物理磁场分支`BLOCKED_BY_INPUT`。

---

## 6. 阶段E：归档与老数值支线安全诊断（不妨碍主线）

### E1 修复v072受控账本语义（零render/零BEM）

从`v071_return/numeric/side_*.mat`读取每条真实`cid`、`r.cfg.particle.diameter_nm`、`r.cfg.focus_nm(3)`，不要用`strcmp(cid,sprintf('K%02d',1:6))`。修正`render_source_sha256`为实际`render_system.m` SHA、`wrapper_source_sha256`为对应入口SHA；文件SHA与系统SHA语义分列。保留原坏表在history，不覆盖旧字节。

程序断言24个有效键完全对应K01–K06×4，D/z与预注册条件精确一致，元数据与C实际65×65、有限性一致，读回哈希稳定；再把12条`P_common/F_angle`正确标`NOT_EXECUTABLE`，历史v070失阵列的36个值仍标`HISTORY_UNVERIFIABLE`。修复产生的`controlled_ledger_v073_verified.csv`包含固定D、zf与真实hash、不声称没有sol就能改变角度网格。

### E2 P0只按原安全条件执行，不能清除历史进程绕过资源限制

工作站原历史hung `matlab -batch`进程未确认安全时，最多只做**被动进程、内存与对象路径清单**，不直接启动Hook；若已确认串行求解全部完成、隔离诊断克隆与安全资源可用，才在**原未使用额度**内最多执行一次不改求值语义的目标`duffy1/eval2`被动Hook，保存是否命中及形状、内存、调用栈。`TARGET_PATH_NOT_REACHED`不算定位成功。P0完整direct/reflected/total blocked-unblocked各`<1e-10`仍OPEN（历史Frobenius2.58848e-7），rule7大参考本轮授权0，不把P0诊断失败自动套到无依赖的实验FFT处理。

R6边界/A3 seed等若没有明确原剩余额度与依赖，本轮只登记真实状态，不追加金球/噪声任务。

---

## 7. 预算、先后与自动连续执行门槛

| 工作 | 本轮额度/上限 | 累计说明 |
|---|---|---|
| 新磁颗粒或金球BEM | **0** | 已完成三尺寸均匀、分层不重求，未批准新D节点/网格 |
| 错误v072真实回放纠错 | **同一7.29帧组一次完整正式重处理** | 仍只有一组真实采集，先有阶段A关键断言 |
| 3D与4D/直接DFT小ROI数值交叉 | 固定小范围，至多12像元+1个41×41参考块 | 内含于纠错回放，若一遍流式数据资源紧张可二遍 |
| 解析新增定向夹具 | **≤8项** | 仅弥补v072旧12项的缺失，不把旧12项全重跑成新物理试验 |
| 解析动态观测算子示例 | **≤4组** | 仅软件/数学验证，不生成物理粒径校准 |
| v071受控侧数组/账本 | **0侧render** | 仅纠正有空字段/错哈希的文本，缓存原样 |
| 新噪声批次、磁材料密库、新D/z/NA扫描 | **0** | 缺真实动态物理合同和可识别性证明 |
| P0 Hook | 在安全前置下最多1次，使用**原尚未消耗额度** | 禁止重试OOM、禁止rule7大参考 |
| 测试包装轻量修复 | ≤2次有记录修复 | 超过报告真实失败，不自动再授权 |

执行顺序：A（最高优先级）→B（缺项）→C（真实纠错回放）→D（有意义的实验观测诊断）；E1可平行，E2依赖工作站资源。A/B未通过就不能让C写`EXPERIMENTAL_FFT_VALID`；C未通过D只可作理论说明，不能用v072旧输出代替。不同分支独立继续。符合前置就自动运行到预算内结束，不等待GPT逐段许可。

### 统计/物理状态统一

每项独立输出`execution_status`、`validation_status`、`evidence_status`。例如v072旧真实回放`EXECUTED / INVALID_FFT_AXIS / SOURCE_CODE_CONFIRMED`；v073正确回放通过则`COMPLETED / FFT_PIPELINE_NUMERIC_PASS / COMPLETE_FOR_REPLAY`，但`experimental_validation=false`与`calibration_valid=false`不改变。磁颗粒个体粒径仍`NOT_ESTIMATED`；若未知运动导致模型不可识别就输出合理的可行D集而非点估计。旧金球检测PASS严格只用于冻结合成链限定场景，不迁移为磁材料实验准确率。

---

## 8. 单个返回ZIP、可读GitHub分支与证据闭环

**只交一个ZIP（以及GitHub可读新分支），不让用户挑零碎产物。**结果包至少包含：

```text
iscat_v073_return.zip
  00_README.md
  00_全部文本汇总_v073.md           # 当前真实总结，勿再复用v059旧汇总
  00_Codex_v073_执行指令.md        # 本文件
  status.json / review.md
  experimental/
    experimental_inputs_v073.json  # lambda=520 USER_CONFIRMED；其余实况逐项来源
    observable_contract_v073.json # PRIMARY_C400；版本、公式、索引、mask、units
    extractor_versions_v073.csv
    input_provenance_replay.csv     # 原BMP文件名/排序/原图身份，不公示私密目录细节
  tables/
    fft_axis_negative_tests.csv
    fft_fixture_corrections.csv
    fft_bin_audit_v073.csv
    fft_replay_corrected_summary.csv
    fft_replay_direct_dft_checks.csv
    fft_spectral_neighborhood.csv
    fft_mask_and_quality.csv
    controlled_ledger_v073_verified.csv
    cost_ledger_v073.csv
    physical_input_gap.csv
  numeric/
    fft400_corrected_small_roi.mat
    fft420_control_small_roi.mat
    fft_analytic_small_examples.mat
    numeric_inventory.json        # 大回放.mat在工作站：真实路径/size/shape/变量/hash
  source/
    extract_fft_v073.m            # 实际全套新源码，保留原脚本不修改
    run_v073_fft_validation.m
    run_v073_replay_corrected.m
    ...                            # 实际执行入口及差异/哈希
  logs/
    matlab_native_run.log
    original_vs_corrected_replay.log
    test_failures.log
  history/
    v072_wrong_axis_source_and_result_status.md
    prior_csv_evidence_problems.md
  manifest_sha256.csv              # 对最终返回包文件实际字节计算
```

完整2001帧原始BMP、包含全图的真实回放MAT及姓名、微信/账号/本机个人隐私路径**不得擅自推公开GitHub**。可以返回已脱敏、小尺寸数值MAT和按源文件计算的哈希；原完整结果在工作站留真实可恢复路径/变量/shape/dtype/sha256并标为`WORKSTATION_ONLY_NOT_IN_ZIP`。返回ZIP必须CRC通过、清单路径与实际字节匹配，CSV各行同列数、无非预期控制字符、无重复key或隐式NaN=0、对缺失项记录状态；至少一次独立新MATLAB会话使用保存后的小ROI重新做DFT/FFT对照。GitHub发表后锁定新commit，并从该commit回读至少status、review、修复测试、正确回放和清单。

特别注意源脚本来源`C:/Users/PC/Downloads/test_with_contrast.m`为字节核验的400 Hz原始版本（SHA-256 `d08575b1...3ea3aa`），用户另附有同名脚本时应并列记录具体hash，而不是只凭文件名说绝对同一版本。历史金球相机1506e/1ms属于其冻结合成验证，与这里真实5000fps时序及未知曝光**绝不共用**。

---

## 9. 本轮审查依据与科学结论范围

固定v072源文件：

- `source/run_v072_replay.m`：三维stack＋`fft(signal,[],4)`错误；两个箱取到的是时域切片。
- `source/run_v072_fft_fixtures.m`：12条直接DFT/FFT的数值测试及F07未实际时移、F09零掩码、F10同表达式、F12数值`%s`的问题。
- `source/run_v072_reconcile.m`与`tables/controlled_ledger_reconciled.csv`：24侧hash原值可保留，但D/z为空、源码SHA表头反置。
- `tables/fft_bin_audit.csv`：400 Hz正频率箱161为399.80009995 Hz，420箱169为419.79010495 Hz。
- `tables/fft_replay_one_case.csv`、`tables/fft_analytic_fixtures.csv`：已有报告与其范围/质量限制。
- `experimental/fft_observable_contracts.json`、`experimental/extractor_versions.csv`：两源脚本观测量定义、真实旧数据路径和哈希。
- `tables/static_identifiability_screen.csv`：仅演示静态三尺寸×焦面，不证明动态测径可逆。
- `status.json`、`review.md`、`material_identity_checks.csv`与当前用户消息：未完成的实验标定/P0，以及**真实激光波长520 nm**。

**审查者没有运行工作站MATLAB/BEM或重新读完2001份BMP；上述致命FFT维度错误来自锁定提交的源码与MATLAB官方FFT维度语义，属于确定性源码错误。**其他已报数值的接受范围均以已能检查的来源为准，不把派生表当成独立原始实验验证。

**最终研究目标不变**：对真实520 nm反射式iSCAT，在有数据来源的材料、光路、颗粒运动/高度等约束下，建立经**同一400 Hz归一化复调制对比度提取器**的粒径—观测关系、可逆域及误差；本轮纠正实验FFT只是达到该目标的前置必要步骤，既不是实验粒径已测得，也不是允许无界扩大数值库。
