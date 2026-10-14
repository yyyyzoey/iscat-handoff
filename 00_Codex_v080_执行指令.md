# iSCAT / Fe₃O₄ v080 唯一连续执行指令

## v079 真实源码审查、谐波结果链修复、已有曝光积分收敛与观测量资格检查

> **文件性质**：此文档是 GPT 根据实际 GitHub v079 固定提交、返回数值表、原生日志及上一轮用户提供的 v079 指令所写的**下一轮 Codex 工作站执行方案**，不是 v080 已运行结果。执行者在 Windows/MATLAB 上依照门槛自主连续执行；失败只暂停依赖分支，最后一次性返回一份 ZIP + 可读 `v080` 分支。**不得把计划、状态摘要或提前计数作为已经完成的实验结果。**
>
> **审查的冻结对象**：`yyyyzoey/iscat-handoff`，`v079` commit **`8e9bfbafe3046213b75c251009fc25b050e7f651`**；父提交 `v078` **`2e81e3ba5b882fde79763b65ffbfa1d2dfb11d9b`**。上传给 GPT 的上一轮原始执行合同为 `00_Codex_v079_v078审查与满秩谐波分解及实验观测稳健性指令.md`；该上传文件为 27922 字节，Git blob 为 `a7aca781aa2662808f299b2bf0a71e197fa9e8ae`，与仓库 `v079` 中相应指令内容身份匹配。
>
> **用户确认事实**：真实激光**真空波长 520 nm**。对7.29这一批实验数据，已用`Fs=5000 fps`、帧1000–3000、`N=2001`，正式研究候选观测量是 `C400=2X_160/(N Imean)` 的复数归一化调制对比度和其模；离散实际频率 **399.800099950025 Hz**，MATLAB bin **161**。这是测量/数值提取定义，**不是**已确认磁驱动频率、同步磁响应、颗粒检测或绝对粒径标定。`NA/实际物方像元/总倍率/曝光/磁驱动波形和相位/真实批次光学常数/位移与高度`仍未核实；历史65nm物方像元及Fe₃O₄ Querry材料常数仍属于演示设置。
>
> **冻结成本与门槛**：**新增BEM=0、任何新Fe₃O₄位置复场render=0**；不添加粒径节点、焦面、波长、噪声批次、实验数据采集；继承原2%静态前向门槛、复场插值0.001工程门槛和P0 direct/reflected/total三矩阵各`<1e-10`门槛，不得调弱。已保存的30个有符号锚点、24个留出、正确物理中心ROI及v076动态数据不得因为v079导出失败而重做BEM。

---

## 0. 真实审查结论——绝对不能照抄 v079 的 `24/24 PASS`

本次审查**确实读取**固定提交的 `status.json`、`review.md`、`source/run_v079_preflight.m`、`source/run_v079_B_harmonics24.m`、两种谐波CSV、两种中心时序CSV、曝光CSV、轻量复核表与`logs/matlab_native_run.log`，并用独立CSV结构与行计数检查。没有在GPT当前容器运行用户工作站MATLAB，也没有独立重算大型远场和完整时序；仅对可直接证明的内容下判定。

### 0.1 已经实现、有根据的部分

| 来源 | v079有证据的实际内容 | 裁决 |
|---|---|---|
| `run_v079_preflight.m`、T1/T2及stdout | 旧v078设计矩阵9列但rank=8，末列全零；修复后的9列矩阵满秩9，cond约1.4146 | **接受代码中满秩构造的修复**，不等于24条导出成功 |
| `v079_centre_series_crosscheck.csv` | 24个键各报告了2001点、均值和标准差 | **接受缓存存在性表报**；不是新鲜时序对原保存时序的逐值比较 |
| v078的奇偶/相机ROI/配对原表 | 270条三态奇偶、24条相机ROI、276对离散比较已有源 | **保留旧结果**，不反复导出或计算来凑新功劳 |
| v079曝光表 | 4个处方条件×3个τ（0/0.1/0.2ms）=12条表格记录 | **只有旧五左节点历史值重新汇总**；没有高阶曝光验收 |
| 成本声明与目录 | 无新增BEM/位置render；已有场在工作站 | 无证据要求重做场；新阶段仅修程序及已有时序 |

### 0.2 P0严重错误：`harmonics24_correct.csv` **24/24 行都是 ERROR**

`tables/v079_harmonics24_correct.csv` Git blob `ca9a5777d159c826be34eea7b8ed00791b6a99fe`：表头**24列**，实际**24条数据均仅22字段**且`mean_I=ERROR`，每条含`无法识别的字段名称`；类型列出现`È`、`Ɛ`而不是`M200`、`M400`。没有任何完整、正常的24列谐波结果行。`tables/v079_series_crosscheck.csv` blob `6777ee97d7307f224988e4c25409669e5a24328b`只有表头，**0条**有效逐时序交叉复核。

可直接从实际源码证明根因之一：驱动循环 `for tt=[200 400]`，将**数值**`tt`放进`%s`：

```matlab
% v079错误：tt是数值200/400，%s会当字符编码打印
svKey = matlab.lang.makeValidName(sprintf('D%d_zf%g_%s_a%d',D,zf,tt,ampn));
...
caseId=sprintf('D%d_zf%g_%s_a%d',D,zf,tt,ampn);
```

这生成无法命中真实缓存字段（正确应为`M200/M400`）的伪键，如`D30_zf450___a5`。随后字段访问触发异常，`catch`将错误写入CSV；异常没有传播为任务失败。**成功计数在正式结果输出之前就已自增**，因此终端 `[079B] done: 24/24 PASS` 以及顶层status的`PASS_24_OF_24`均**不具备正式验收意义**。

**第二个独立阻塞，不可只修`%s`就结束**：v079的`R76`读取的是`v076_center_roi_harmonic_small_examples.mat`；此结构的`C400`按已发布`run_v076_D_qr_center.m`是**一个标量拟合量**，不是41×41复图。v079又写`R76.(svKey).C400(21,21)`，修正键后仍会出现标量越界。必须使用`R76.(svKey).binAbs`或从`v076_dynamic_center_corrected.mat`取真正的41×41 `C400(21,21)`，并显式核对二者实际含义，不能将两种数据对象混成相同字段。

另外：实际日志还有4次`SKIP 30 450 200 5: 索引超过数组元素的数量（<=5）`，来源堆栈未在GitHub交接中完整说明。不得预判具体源头；必须留原堆栈/源版本和对应状态，确认同一试次是否已消费计算预算。

### 0.3 P0导出语义错误：谐波长表**96/96行字段错位**

`tables/v079_harmonic_parts_long.csv` Git blob `96187032fa1519f5512e955cbc4f75cc4e26d342`，表头5字段`case_id,freq_Hz,X_re,X_im,units`，96行**全部是6字段**，例如：

```text
D30_zf450_È_a5,200,X_h200,-2.050140...e-11,-5.261120...e-12,DFT_count
```

实际源使用`'%s,%g,X_h%g,%.17g,%.17g,DFT_count'`，额外输出的`X_h200`在错位后的`X_re`列，真实实部落在`X_im`，虚部落入`units`。**长表现状不是合法的复数谐波数据结构**。不能仅把列名替换，必须从原复数变量重新输出每频率完整Re/Im、单位与正/负频率核。

### 0.4 P1其他错误：CSV、证据链、曝光和历史门槛

1. `v079_preflight_and_negative_tests.csv`表头5列，**7条中6条仅4列**；这是schema FAIL，尽管关于新矩阵rank=9的打印/源码可以单独接受。要新增正式机器可读取的preflight表和负向夹具。
2. `v079_centre_series_crosscheck.csv`24行都标`SERIES_EXISTS`，仅保存长度/均值/标准差；并没有在同一D/zf/a/类型下从正确中心`Ipix(21,21)`独立重算并比较全部2001点，不得标`SERIES_IDENTITY_PASS`。
3. `v079_light_reverify.csv`给出`T10_39nm_diff=0,PASS`，与原v078真正39nm比较的`0.00049389056893889022`冲突。**零差并不能说明“39nm错位被拒绝”**；必须查清是取错缓存、重复同一ROI还是仅错误填表，不能覆盖源结果。
4. `v079_exposure_convergence.csv`共12条（τ=0/100/200μs）；实际仅复制旧`five_node_left`值，**无16/32等更高阶求积的任何新数值或收敛指标**；review也说明`NOT_EXECUTED_RESOURCE_LIMIT`，须诚实保留。`M400`中心近零不适用相对百分比推理；400Hz sinc因子仅是**纯400Hz强度正弦项**的解析参照，不能替混合非线性强度信号的实际收敛证据。
5. `v079`的`numeric_inventory.json`中没有新保存的谐波正确参数MAT，不能以脚本中曾计算系数、旧长表有数字和stdout PASS代替结果持久化与读回验收。
6. 所谓M200`bin161/C400_fit≈0.9895–0.9897`在v077/v078已有表中存在算术证据，但**不是v079的完整有效24行重新验收**；不能称“v079已确认该科学结论”。
7. 结果文件保存失败**不得**自动把先前v075/v076/v077/v078有效BEM/插值/静态ROI算子判断成FAIL；它是本轮执行和发布证据失败，影响其依赖的谐波解释和曝光稳健性结论。

**正式当前状态**：`A_rank_fixture=PASS_WITH_SOURCE_AND_PRECHECK`；`B_harmonic_execution=FAILED_24_OUTPUT_RECORDS`；`B_harmonic_part_csv=SCHEMA_FAIL_96`；`B_time_series_identity=NOT_EVALUATED`；`D_exposure_high_order=NOT_EXECUTED`；`C_odd_even/E_pairwise=INHERITED_READ_ONLY`；`P0=RESOURCE_GATED_OPEN`；`experimental_validation=false`，`calibration_valid=false`，`detection_validated=false`，`single_particle_diameter=NOT_ESTIMATED`。

---

## 1. 执行硬约束、预算继承与门槛优先级

- **零BEM求解、零位置render**。现有三尺寸D=30/60/100 nm、两焦面zf=450/550 nm、两个处方频率M200/M400、运动振幅5/20 nm，N=2001 Fs=5000，真实波长520nm，其他光学参数只用于演示；本轮不得扩展任何物理条件。旧24条合格复场留出工程门槛仍为每条`<0.001`，不为v079失败重新求解。
- 历史已花成本不清零。优先从 v076 `v076_center_roi_harmonic_small_examples.mat`读取24条中心2001点时序，及`v076_dynamic_center_corrected.mat`读取正确中心C400复图；已有v074 30锚点、v075 24留出不重渲染。
- `run_v079_B_harmonics24.m`可借用正确满秩B矩阵和数学公式，但**输出路径不能继续复用本轮故障脚本而不修其结构错误**。写统一共享函数构造频率/时序/设计矩阵/复数DFT/CSV；禁止依赖MATLAB base workspace持久状态。
- 全部强制门禁：**(1) 来源和shape;(2) 源码负向测试;(3) 满秩与幅相恢复;(4) 复数投影加残差闭合;(5) 单位/数值断言;(6) CSV合法读回;(7) 保存成功并新会话复核**。只要任一步失败，同一case不得计PASS。
- 不用原有2%前向、0.001留出或P0三矩阵`<1e-10`门槛给当前FFT拟合伪造“既定物理误差合格”。谐波代数阈值沿上一轮`closure_rel<1e-10`（同一归一化定义），解析双精度夹具门槛由代码事先冻结，不能回头调容差。

## 2. A：最小真实入口和故意失败测试——**先验收导出，后批量计算**

### A0. 源身份、缓存类型、正确中心

必须核对 `which`与磁盘SHA-256：`render_system.m`、`pixel_mean.m`、`extract_fft_v073.m`、`position_key.m`、`run_v076_D_qr_center.m`、`run_v079_B_harmonics24.m`；v076 MAT中每个`series`为2001点、存在且有限、`mean(I)>0`，`binAbs`标量，`C400`在**QR小文件中为标量**；v076动态完整MAT中`C400`为41×41复数组，使用`(21,21)`。注意序列与整图可能有单精度/累积顺序差，按预先约定的绝对+相对精度进行数值比较并公开残差；绝不能因数值不字节相同就自动重求BEM。

### A1. 必须拒绝的7种错误

1. 将数值`tt=200`直接代入`%s`作为轨迹字段，生成非ASCII伪键；测试必须FAIL，正确标签只可为精确的`M200`/`M400`。
2. 对来自`v076_center_roi_harmonic_small_examples.mat`的**标量**`C400`执行`(21,21)`访问；必须被形状守卫捕获（负向成功）。
3. 导出字段数与表头不等：`24 cols vs 22`、`5 vs 6`、`5 vs 4`必须FAIL。
4. 复数`X_h`写成单个字符串或者把`X_h200`混入`X_re`列，必须FAIL。
5. 对失败的case在`catch`中仍递增成功计数、或在没有CSV读回前把`24/24`写入status，必须FAIL。
6. 时间序列只有“长度/均值/标准差”而没有可重算`Xbin`、实际像元和源数组哈希，就声称逐值身份PASS，必须FAIL。
7. 将T10真正39nm偏移零差写成“负向差异被检测”，或将空的新高阶求积列写PASS，必须FAIL。

建议先只执行**D60/zf450/M200/a5**一个case，在MATLAB执行器外用Python标准`csv`（也可另一个纯读MATLAB会话）严格检查行宽、数值、类型和状态，再扩批其余23条。**一个case最小可复现未通过，则不启动B批量；其他独立历史归档照常执行。**

### A2. 正确类型和缓存读取示例（请Codex查实际结构后适配）

```matlab
% tt 数值仍可用于轨迹函数，但**不得直接格式化为 %s**
tt = 200;  D = 60; zf = 450; a = 5;
ttype = sprintf('M%d', tt);
caseId = sprintf('D%d_zf%g_%s_a%d', D,zf,ttype,a);
assert(isfield(R76, caseId), 'MISS_CENTRE_SERIES: %s', caseId);
f = R76.(caseId);                         % v076中心小MAT对象
assert(isfield(f,'series') && numel(f.series)==2001);
assert(isfield(f,'binAbs') && isscalar(f.binAbs));
% f.C400 是QR拟合标量，不允许 f.C400(21,21)！
RMap = load(fullfile(v076Root,'numeric','v076_dynamic_center_corrected.mat'));
assert(isfield(RMap,caseId));
cmap = RMap.(caseId).C400;
assert(isequal(size(cmap),[41,41]));
Cbin_pixel = cmap(21,21);
```

若`isfield`、类型或已保存标量不一致，应检查实际保存脚本和运行身份并记录最小复现；不可通过重命名字段掩盖错误。所有case物理身份以及`a/tt/zf/D/q/N/Fs`必须与源文件匹配。一个公共`caseId`进入所有MAT结构、CSV和manifest，不能出现三种别名互相无法对账。

---

## 3. B：24条 **真正**满秩谐波与复数有限窗投影闭合

### B0. 正确的数学与程序合同

对每个正确中心像元强度时序`I_j`，设`N=2001`，`Fs=5000`，`j=0..N-1`，`Ibar=mean(I_j)>0`，`y_j=I_j-Ibar`。频率集合固定为：

```text
M200: [200, 400, 600, 800] Hz
M400: [400, 800, 1200, 1600] Hz
```

**满秩基矩阵**：第1列常数，后4个谐波各有正/余弦列，共9列。

```matlab
freqs = [200 400 600 800]; % M200例
B = ones(N, 1+2*numel(freqs));
for h=1:numel(freqs)
    B(:,2*h)   = cos(2*pi*freqs(h)*tj);
    B(:,2*h+1) = sin(2*pi*freqs(h)*tj);
end
assert(rank(B)==size(B,2));
assert(cond(B)<1e8);
coef=B\(double(I(:))-mean(double(I(:))));
yhat=B*coef;
r=double(I(:))-mean(double(I(:)))-yhat;
A_h=complex(coef(2:2:end),-coef(3:2:end)); % 已是正弦幅值的复系数
C_h=A_h/Ibar;                             % 不再乘2/N
```

原始bin161复DFT计数与实验定义的复归一化系数：

\[
X_k=\sum_{j=0}^{N-1}(I_j-\bar I)\,e^{-2\pi i k j/N},\qquad
C_k=\frac{2X_k}{N\bar I},\quad k=160.
\]

定义闭式核`G_N(u)=sum_j exp(2*pi*i*u*j)`，近整数参数使用稳定的直接求和/`expm1`分支规避`0/0`。令`A_h=a_h-ib_h`，每条正弦基的**原始DFT计数**贡献：

\[
X_{h\to k}=\frac{A_h}{2}G_N(f_h/F_s-k/N)
+\frac{A_h^*}{2}G_N(-f_h/F_s-k/N).
\]

同时明确第1列截距对应`b0*G_N(-k/N)`，以及残差DFT`X_r`，验算**复数**恒等式：

\[
X_k=\sum_h X_{h\to k}+b_0G_N(-k/N)+X_r.
\]

量纲标记：`X_*`是 `DFT_count`（输入强度强度计数单位×采样点数），`C_*`是dimensionless。**同一加法式不得混进归一化的C字段；不能把复数模值相加代替复数重构**。统一发布绝对闭合与`closure_rel=|delta X|/max(√N||y||_2,预声明绝对尺度)`；**原规定`<1e-10`保持不变**。但该恒等式即使通过，也只是参数化分解的算术性质；可靠性还取决于满秩、条件数、拟合残差、相位恢复及源时序身份。

### B1. 解析前置夹具（零BEM；最多8项，先锁定再执行）

须至少包括纯200 Hz、纯400 Hz、有非零相位400 Hz、200+400混合且两相位非零、400+800相位组合、常量或已知零系数、正确中心静态场无运动、以及一例低幅/单精度数值极限。每项保存构造幅相、均值、`X_exact`、`X_dft`、`Cfit`、`Cbin`、秩、条件数、复闭合、单精度差异和PASS/FAIL；明确模型拟合分量/有限窗bin不总相等。旧错误矩阵必须FAIL；`%s`格式错和标量索引错必须FAIL。双精度固定解析公式容差在运行前冻结（可以使用此前固定夹具绝对`≤1e−12`或相对`≤1e−10`；近零先适用绝对值判据），不以真实样品或噪声名义放松历史门槛。

### B2. 严格逐条件处理、写盘和验收的24条序列

- 先通过单case完整门槛，再读取其余23条已存中心强度时序。**禁止从零构造24组新物理状态**；有缓存就只重算QR与DFT，回放无需时域重生。只有个别源时序确实缺失才在**原有位置场、不做新render**的前提下恢复该时序并精确计入恢复次数；总上限为既有24条，而非24条新实验。
- 每条保存`D,zf,tt,a,N,Fs,lambda,correct_center_row_col,source_sha,series_hash,rank_B,cond_B,mean_I,resid_RMS,Xbin_Re,Im, Cbin_Re,Im, C400fit_Re,Im, individual X_h_Re,Im, intercept_Re,Im, residual_Re,Im,closure_abs,closure_rel,status`。数组、表、哈希来源共同生成。
- `type`字段只能是**ASCII精确**的`M200`或`M400`；用`ttype=sprintf('M%d',tt)`。`bin161_absC`只能写`abs(2*Xbin/(N*Ibar))`；原始`abs(Xbin)`单独命名`Xbin_abs_DFT_count`，不可错单位。
- 独立于拟合的验证：保存的`f.binAbs`（来自v076正确中心单像元提取）与本轮直接DFT经归一化的模逐条件核对；若有`v076_dynamic_center_corrected.mat`完整图，再与`C400(21,21)`核对（考虑单精度、数值稳定下限）。将`f.C400`标为 **LS拟合标量**，绝不写`f.C400(21,21)`。
- 一条case只有**实际保存、独立CSV严格读回、独立MAT读回、原源身份和所有断言通过**才可计入success。逐行`try/catch`允许记录错误并继续独立任务，但计数必须位于最后，catch必须产生完整合法`status=FAILED`行并保留`ME.identifier/report`，总状态不能再输出“24 PASS”掩盖错误。
- 如1个case FAIL，整个`B_all_pass`不得为PASS，待完成其他允许工作后统一返回修复状态、失败case列表和明确budget记录，不准“假设全通过”。

### B3. 正确数据表结构（固定必须满足）

1. `v080_harmonics24_validated.csv`：**24条固定条件**，`24`表示每个计划case均有状态记录；科学完成条数只计`validation_status=PASS && evidence_status=COMPLETE`。CSV表头/数据列完全同宽，正负相位及强度幅值均独立列。
2. `v080_harmonic_parts_long.csv`：`24×4=96`条频率贡献，每行`case_id,freq_Hz,term,X_re_DFT_count,X_im_DFT_count,C_re,C_im,source_sha,status`；另建`v080_harmonic_residual24.csv`保存bin、总模型、残差与截距，避免历史错误的`X_h200`插入复实部。`X_re`必须是可解析double，不是`X_h200`字符串。
3. `v080_time_series_identity24.csv`：24条逐样本来源、中心位置、哈希、保存时序与新鲜重算/原FFT对照的最大复误差；不能只保存mean/std就宣称强身份一致。
4. `v080_preflight_regressions.csv`：所有负向夹具、满秩/残差/格式检查，严格5列等宽。用外部`csv.reader`和另一个干净MATLAB会话读回所有CSV，验证无NUL/控制字符、唯一case键及语义单位；旧文件保持历史，不覆盖。

---

## 4. C：继承已接受的奇偶/相机ROI/276对，不重复耗算

- 原`v078_evenodd_270.csv`、`v078_camera_roi24.csv`、`v078_identifiability276_audit.csv`和`v078_T10_true_39nm_negative_test.csv`直接只读复核来源SHA、行数、唯一键和必要数学关系；**原有效结果继续有效**，不重新计算所有表以制造新版本增量。
- T10正确39nm错位在v078已有`0.00049389056893889022`（对应特定位置/指标），而v079轻量复核写`0,PASS`；v080必须**从v078的真实两ROI数组**或原有静态哨兵重新复核并说明指标单位。只在确有错误算子判别或重复拷贝时才重算该一个小测试，不为校正日志重渲染复场。预声明逻辑是：**错位与正确窗口不应被识别为相同物理身份**；不允许以零差将负向测试判PASS。
- 276对距离依旧只支持**24个演示参数组合下的有限离散筛查**；最近跨D幅值图对约`0.26465`的对称相对距离来自已发布表，不能以无噪声有限距离推出实验粒径唯一性。按参数变化分组，可给出中心单标量与完整41×41幅值图在相同尺度下的最近跨D候选，但这些是**已有结果的派生统计**，不得宣称新盲测或检出率。

## 5. D：兑现v079原本未执行的**合成曝光积分收敛**额度

**放行前置**：B数学与时域入口至少单case通过，且既有D60/zf450四个处方条件的光学位置缓存/中心时序身份清楚；否则标`BLOCKED_DEPENDENCY`，可继续独立归档。

冻结原8个非实测条件：`D60/zf450 × (M200,M400) × a=(5,20)nm × tau=(0.1,0.2)ms`，τ=0基线仅从原已验证值读取。既有五点左求和作为**历史近似**保存，绝不改写或冒充精确曝光。

**唯一允许新的高成本后处理**：在原v079合同未消耗的条件性额度内，**最多16条额外时域评价**，即原8个条件×两种事先冻结的更高精度数值积分方案（例如`16`与`32`节点的中点/Gauss合格方法）。二者必须在同一物理帧起始、同一τ、同一参考强度及同一中心/41×41ROI上计算；仅更新时域曝光积分，**零新位置render、零BEM**。不自作主张添加新τ或新运动节点。

- 先在纯400Hz强度正弦的可解样例上测试积分规则，`|sinc(400τ)|`只是这一频率分量的解析幅值衰减参照。`M200`产生的400Hz二次分量也应对照400Hz而非200Hz，但混合强度信号不能仅由一个sinc完全描述。
- 保存所有原8例的左5、中16、中32等**实际新数值**，同一个正确复FFT观测量的幅值、相位、两级增量，近零时保留**绝对差与精度标志**。不得因幅值百分比特别大或特别小就择优解释。
- 正式“收敛”至少要有实际不同节点结果，不能写`quadrature='5_node_left'`然后将`sinc_ref`列更新称之为收敛通过；一个高阶结果未执行如实标`NOT_EXECUTED`，剩余额度不移给BEM。

## 6. E：观测量稳健性和实验输入（方法学派生，不发展新标定库）

- 在确有可靠的B阶段数值/正确中心复C400全图时，将固定24个演示状态的**中心`|C400|`、固定41×41模值图、复图诊断**分别做多参数影响分组。相位参照未证实前复数图只供方法开发，不能当真实实验可用相位。
- 分别比较“同D改变a/zf/type”的自然变化尺度，与“跨D改变未知参数”出现的最小观测差异；不使用任何未来实验统计精度、噪声阈值或反演成功率的虚构数字。
- 不对齐任意自由幅度、相位、中心或ROI以压低差异后宣称实验唯一性。若为了研究失配做方法开发对齐，须另列`DIAGNOSTIC_ONLY`并保存额外自由度，不覆盖正式指标。
- 真实520nm波长、5000fps及bin161仍保持确认；曝光、实际NA/倍率/物方像元、磁驱动波形/参考相位、样品批次复杂介电常数、实际位移/高度逐项查工作站已有元数据，找不到记`MISSING`，不代填“65nm”“a=5/20nm”“Querry bulk”。
- 真实实验FFT目前只能支持**一组7.29数据中的频谱/ROI诊断**；无运动—散射参数标定、噪声模型和独立样品标定时，严禁输出实验绝对D、Bias/RMSE、检测FPR或“磁响应已被证明”。

## 7. F：P0独立支线及安全要求

P0历史`2.58848e−7`仍未满足同一问题direct/reflected/total三矩阵各`<1e−10`。只有工作站没有和正在运行的高内存求解冲突、许可证与历史PID身份清楚时，才按以前明确剩余额度**最多进行1轮只记录的被动Hook**；不满足直接`NOT_RUN_RESOURCE_GATED`，不得自动清理/杀死他人或历史未知MATLAB进程；**rule7新大型参考0笔授权**。P0与正确的实验FFT纯后处理是独立依赖，除发现共享源码真正受污染，否则互不阻断。

---

## 8. v080严格预算与合法依赖

| 项目 | v080本轮允许上限 | 说明 |
|---|---:|---|
| **新BEM solve** | **0笔** | 不重求30/60/100nm均匀或分层已有系统 |
| **新Fe₃O₄位置侧render** | **0次** | 所有正负位移从旧场读取 |
| 满秩QR、复DFT、CSV逐条件补算 | 只限原24条时序 | 必须输出24条合法证据才可声明24/24 |
| 条件性缺失时序恢复 | 最多原24条中的实际缺失条数 | 源系列存在则仅读取，恢复不增加物理状态 |
| 新解析/负向小夹具 | 最多8项核心解析+必要不耗成本I/O错误测试 | 不增加光学采样与BEM |
| 旧曝光高阶后处理 | **最多16次**（8组×2规则） | v079未消费的上限，不可偷换成新8个条件 |
| 奇偶270、相机ROI24、离散276对 | 只读核验及必要派生统计 | 不算新Monte Carlo或新盲测 |
| 7.29 BMP重新全量扫描/新实验采集 | **0** | 不因CSV错位重新读2001帧 |
| 新D、zf、波长、磁参数、曝光条件、噪声批次 | **0** | 不增加物理节点 |
| P0被动Hook | 继承至多1轮且安全门通过 | rule7大参考0授权 |

**自动连续执行顺序**：A单case完整通过→B余23条及独立读回→C继承证据复核→D按安全与前置进行高阶曝光→E干扰参数派生统计→F安全P0。一个单分支失败则只阻断相关分支，其他依赖独立工作继续；每阶段必须写`execution_status,validation_status,evidence_status,scientific_scope`，不得仅填总体PASS。

## 9. 最终唯一ZIP、v080可读分支与成功条件

统一打包`iscat_v080_return.zip`，内容从**本轮实际生产文件**生成，不复制历史错误表改名；同时发布GitHub新可读`v080`分支和完整文件树。建议：

```text
iscat_v080_return.zip
  00_README.md
  00_全部文本汇总_v080.md
  00_Codex_v080_唯一执行指令.md
  status.json / review.md
  source/
    run_v080_A_preflight_and_schema.m
    run_v080_B_harmonic_fix.m
    run_v080_B_independent_recheck.m
    run_v080_D_exposure_quadrature.m
    ... 实际执行的共享函数和测试 ...
  tables/
    v080_regression_negative_tests.csv
    v080_input_cache_identity.csv
    v080_harmonics24_validated.csv
    v080_harmonic_parts_long.csv
    v080_harmonic_residual24.csv
    v080_time_series_identity24.csv
    v080_exposure16_incremental.csv
    v080_T10_camera_identity.csv
    v080_nuisance_observable_screen.csv
    v080_budget_ledger.csv
    v080_p0_status.csv
  numeric/
    ... 至少D60/zf450/M200/a5及两个敏感M400案例的完整中心时序/模型/残差/复数投影可复核MAT ...
  logs/
    matlab_native_run.log
    actual_commands_and_source_hashes.txt
    per_case_failures_and_stacktraces.txt
  history/
    v079_FAILED_harmonic_result.csv
    v079_SCHEMA_FAIL_harmonic_parts.csv
    v079_SCHEMA_FAIL_preflight.csv
    ... 只读原结果、不覆盖 ...
  manifest_sha256.csv
```

每个case按**唯一key**存`status`及`reason`，并且必须有同一个case从MAT→源时序→FFT/QR→复数DFT各项→数值CSV→独立读回的闭合证明。大MAT在工作站则登记具体Windows路径、shape、dtype和实际字节SHA-256，绝不能标成已上传。Git blob SHA-1不能混填文件SHA-256。

**发布门槛**：完整24个计划条件均被赋予合法状态，所有声称PASS的条目有满秩、有限值、正确源对象、复数闭合、CSV表宽与独立读回；全24真正PASS才可写`PASS_24_OF_24`。任何条目异常时`B_overall`必须是`PARTIAL/FAILED`，不能复用v079的提前计数。D曝光只有真实高阶数字才可写“收敛检查已执行”，否则`NOT_EXECUTED`并保留原旧五点数值。

研究层面冻结：`calibration_valid=false`、`experimental_validation=false`、`detection_validated=false`、`single_particle_diameter=NOT_ESTIMATED`；即便B阶段24/24通过，也只证明规定演示系统中时域—谐波处理算子正确，**不**证明真实磁驱动或可绝对测径。

---

## 10. v079固定证据索引（不得从新版本状态臆造源信息）

| ID | 路径（均在`v079@8e9bfb...`） | Git blob | 本次证据支持的范围 |
|---|---|---|---|
| V1 | `status.json` | `10145b6a054fce74519e372a88f9a93a15607bbb` | 执行者报告24 PASS；被正式输出直接反证 |
| V2 | `review.md` | `f163a50a369645ce0085abb79c6a2aa11e6df63c` | 自认高阶曝光未做，历史摘要 |
| V3 | `source/run_v079_preflight.m` | `0da5442fe2c4953bb1e84a2d3ebe3d6db8d6ea72` | 确认新B矩阵rank=9；其它CVS仍有格式缺项 |
| V4 | `source/run_v079_B_harmonics24.m` | `157eac7dac35ac9c6739f8d927ca8e85cab7bf0d` | tt数值用%s、标量C400当复图索引、提前nPass、长表格式错 |
| V5 | `tables/v079_harmonics24_correct.csv` | `ca9a5777d159c826be34eea7b8ed00791b6a99fe` | **24 ERROR、24行宽22而表头24** |
| V6 | `tables/v079_harmonic_parts_long.csv` | `96187032fa1519f5512e955cbc4f75cc4e26d342` | **96行宽6而表头5**，X_h文字占实部列 |
| V7 | `tables/v079_preflight_and_negative_tests.csv` | `fd3944101f346363310e63a5580bdb03cac3a38a` | 7数据行中6行宽4而表头5 |
| V8 | `tables/v079_series_crosscheck.csv` | `6777ee97d7307f224988e4c25409669e5a24328b` | **零数据行** |
| V9 | `tables/v079_centre_series_crosscheck.csv` | `7d77a3f3c20f3304e2db92c1eecdfd55a1f3a774` | 24条series存在，长度/均值/标准差；非像元身份验证 |
| V10 | `tables/v079_exposure_convergence.csv` | `98f3a3471a574c8a7ddc25bf285daec193121e7d` | 12行仅旧五点结果，无高阶收敛数据 |
| V11 | `tables/v079_light_reverify.csv` | `3fca8b2d2a652d3022a228b8161c5d688f7c55c0` | T10写`0,PASS`与真实负向差值冲突 |
| V12 | `logs/matlab_native_run.log` | `03663ff5f3f0da24e179cf015af25edc255bb638` | 原日志自报24 PASS同时有SKIP异常，非成功凭证 |
| V13 | `numeric/numeric_inventory.json` | `0c1be02ce3624fcdd3abc7a63621443fb9878f3d` | 只有历史工作站缓存目录，新谐波MAT未列出 |
| V14 | 原v079执行合同 `00_Codex_v079_执行指令.md` | `a7aca781aa2662808f299b2bf0a71e197fa9e8ae` | 原冻结额度与验收要求；v080只使用剩余授权，不清零 |

固定审查链接：`https://github.com/yyyyzoey/iscat-handoff/tree/8e9bfbafe3046213b75c251009fc25b050e7f651`

### Codex唯一执行口令

> **从 v079 固定提交与工作站真实缓存继续，先确认满秩基修复且拒绝`%s`数值轨迹名和标量C400(21,21)错误，完成1个case的源身份→QR/复DFT→存盘→CSV读回→独立新会话验收；合格再批量修正其余23条。严格禁止根据提前nPass或旧摘要宣称24 PASS。修复长表/入口表结构以及T10误报，并在原未用额度最多16次额外时域评价内完成真实高阶合成曝光积分。继承旧270奇偶、24相机ROI、276对可识别性，不新增BEM/位置render/物理节点，不放宽验收门槛；失败只暂停依赖分支，最终一次性交回一个ZIP和可读v080分支。**
