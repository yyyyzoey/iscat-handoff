# iSCAT / Fe₃O₄ v087 唯一 Codex 连续执行指令

## v086 冻结提交审查、排名判据纠正、7.29缓存实验视频的独立时域FFT证据闭环

> **文件性质和执行责任**：这是根据固定 v086 GitHub 提交中实际存在的源码、CSV、日志编写的**下一轮执行合同**，绝不是 v087 已完成结果。Codex 在用户 Windows 工作站上，从原文件及缓存实际内容执行所有满足依赖的任务；不要逐步等 GPT 批准。失败时如实阻断依赖并继续可独立执行的步骤，最终一次性交付**真实 `iscat_v087_return.zip` 与可读 GitHub `v087` 分支的固定 SHA**。
>
> **审查不可变基点**：`yyyyzoey/iscat-handoff@4fd783e5438a6cae3a9801711a13cb1db3c75f84`，分支 `v086`；父 `v085@9d34f12d7faea45e3f553e4dff683237b4a038e8`。冻结 source SHA 和输入文件SHA-256，禁止把上次摘要重新输出当新运算。
>
> **硬性资源**：新增BEM=**0**；新Fe₃O₄位置复场render=**0**；新粒径、焦面、场强、运动振幅、光学常数、背景噪声样本、实验采集=**0**；新合成2001帧强度时序计算=**0**；原BMP重新读取=**0**。允许对**已有的小实验缓存**最多进行一遍41×41×2001时域FFT和预先固定邻频/抽点DFT，属于旧数据重分析，**不是**重新成像或新增实验。
>
> **研究边界**：真实激光真空波长520 nm（用户已确认）；7.29已有实验脚本记录Fs=5000fps、帧1000:3000共N=2001、MATLAB bin161（0基 k0=160）实际399.800099950025 Hz。候选主观测量为复数归一化`C400=2X160/(N*Imean)`，模值主用、复数相位只为内部诊断。历史200Hz交变磁场、14μm传感器像元与50×物镜仍是未经最终装置核准的记录。演示系统65nm物方像元、NA1.3、5/20nm处方横移、焦面450/550nm、文献Fe₃O₄常数**不是**实际实验标定。
>
> **冻结数值门槛沿用**：历史静态前向2%、复场插值留出`<0.001`、P0三矩阵各`<1e−10`、谐波闭合`<1e−10`均不可弱化。新的CSV/缓存FFT一致性为另外定义的软件验收，绝不能替代以上物理验收，更不能代表实际粒径误差、磁运动因果或检测成功率。

---

## 0. v086 实际审查结果——要继承，也要撤回过度承诺

### 0.1 具有真实来源证据、可正式保留的成果

| 事项 | 固定v086源码/原表审查事实 | 严格判定 |
|---|---|---|
| 24双精度复图 | `tables/v086_24map_source_identity.csv`24行，24个`ARRAY_RECHECK_VERIFIED`，实际源文件SHA-256与v085冻结台账逐个一致；数值重算rF和ε匹配原表 | **文件身份与已有数组算术PASS**；无需新复图/BEM；没有独立物理求解证明 |
| 276对 | `tables/v086_276_pair_distance_intervals.csv`276行（192跨D/84同D）；最近跨D候选单/双精度**实际排序相同**，其余原表仍有证据 | **保留实际排序与距离**；代码中最近候选判定式需修 |
| 条件性保守区间 | 最近距离`0.13326434264817294`，区间`[0.13323436067213862,0.13329432462420726]`；次近距离`0.13335327361218305`，区间`[0.13324433560969901,0.13346221161466709]`，区间交叠 | **NOT_CERTIFIED**正确；此区间只是单/双精度数值路径差推导，不是物理真值误差或置信区间 |
| 生产校验 | `v086_identity_guard.py`真实检查key/shape/内部case_id/mask内有限值及源hash；11测试行有1正例、9类不良输入、1假validator探针，结果都报PASS | **有限共享校验器通过**；`heavy_compute_calls=0`仅由测试套件永远不调用的虚拟计数器支持，不能宣称真实全处理流水已插桩验收 |
| 7.29小ROI缓存 | `fft400_corrected_small_roi.mat`的仓库副本与工作站副本SHA-256相同（`49c10f1b24c6798f745dd8b7f1409b0472912761ac639b71566f9c1e800582be`）；内部N/Fs/k/帧元数据符合；`2X/(NImean)`对现成C400的最大**绝对**差`3.52e−9` | 只能签**METADATA_AND_STORED_FORMULA_RECONCILIATION**，尚无独立从视频帧提取X400的证据 |
| 全幅v073与历史v072 | v086将 `fft400_corrected_full.mat`与`replay_729_frames1000_3000.mat`标为UNKNOWN，因为检查器强制读取`X400/C400/Imean` | **UNKNOWN是适配器不兼容，不是科学否定**；v073全幅实际按旧源码命名`Xk/C_k`，v072则是旧错误时间轴，应单列LEGACY_INVALID |
| 物理与P0 | 新BEM=0、render=0、BMP重读=0；P0 OPEN历史约`2.58848e−7`vs每矩阵`<1e−10`，没有安全Hook；rule7无授权 | 继续遵守；`calibration_valid=false / experimental_validation=false / detection_validated=false / single_particle_diameter=NOT_ESTIMATED` |

### 0.2 P1源码错误：所谓“观察到的两路径最近候选相同”实际用了三角界代理

固定源码`source/v086_recompute_24_maps_and_276_pairs.py`：

```python
# v086旧错误：只说明同一个pair的数值差没有超过数学三角界；
# 并没有对“两个路径各自的argmin”做比较
observed_same = (abs(nearest['d_double'] - nearest['d_single']) <= nearest['b'])
```

真实验收必须在**全部192个跨D条件**上独立计算：

```python
best_d = min(cross_pairs, key=lambda p: (p['d_double'], p['pair_id']))
best_s = min(cross_pairs, key=lambda p: (p['d_single'], p['pair_id']))
observed_same = (best_d['pair_id'] == best_s['pair_id'])
```

固定v086表**重新分别排序**证实`observed_same=YES`这一*观察事实*确实成立，不能因此把原错误代理公式认作已修复。必须增加一份**反例数学夹具**：构造两对的各自`abs(d_d−d_s)≤b`都成立，而单精度与双精度最近索引交换；旧判式错误返回YES、新判式必须NO。

排名认证条件可直接表述为`nearest_interval_hi < min(other_cross_interval_lo)`。注意：在v086使用的**以各自d_double为中心、非负b对称展开**的区间构造，以及nearest确实是最小d_double这两个前提下，原代码“与任何竞争者区间均不重叠”的判定与上述严格条件**等价**，因此**原区间判定算法本身无需判错**；改写只是使判据更直观、便于添加端点相等夹具。v086因重叠而返回NOT_CERTIFIED的实际结果正确，本轮不可试图调整`epsilon`、掩码或对齐来制造PASS。

### 0.3 P1生产守卫的覆盖边界

- `validate_map_metadata`为真实map loader所用，确实检查若干身份字段；但`q`/fine-slice属于**另外调用的几何函数**，旧测试没有穿过整条位置索引→源锚点→复图加载链。
- `valid_mask`检查了形状、1681个有效位及有限值，却**没有真正重算**`Imean>0.01×median(positive Imean)`规则；`mask_rule`目前主要是一个字符串说明。对已有演示图所有1681像元有效也不能以此证明规则实现完备。
- `source/v086_negative_tests.py`的`HEAVY_CALLS`局部计数器从未连接到真正的场/时域计算入口；“0次”仅可描述本测试用例未调用其stub，不是全系统计算入口审计。
- `NEG-G09`是人为定义会抛`RuntimeError`的假校验器，测试与生产`load_double_map`并不走同一路径；应称`TEST_FRAMEWORK_SELFTEST`，而非又一项生产数据输入守卫。
- 不得只写“PASS”，必须为每项负向测试保存**实际突变的文件/数组、具体校验函数、预期异常类型、真正错误字段**；正例必须包含**已存在的磁盘MAP**而非只含内存合成`np.ones`。对未存q/坐标元数据的旧MAT记`PROVEN_BY_VERSIONED_SOURCE`，不可伪称`SELF_CONTAINED_FILE_METADATA`。

### 0.4 P0实验FFT接口的关键机会和标签错误

v086仅从已存`X400`和`Imean`重组`C400`。但历史真实源：

`source/run_v073_replay_corrected.m`（v086提交中可读）保存：

```matlab
roiFrames = stack(ri,ci,:,:);  % HxWx1xN, 41x41x1x2001, single
roi=struct('roiFrames',roiFrames, ...
           'X400',P.Xk(ri,ci), 'C400',P.C_k(ri,ci),...
           'Imean',P.Imean(ri,ci), 'validMask',P.validMask(ri,ci),...
           'meanFloor',P.meanFloor,'k',P.k,'actualFreq',P.actualFreq,...);
```

这意味着**小ROI原始2001帧已经缓存**，可以不访问任何BMP而独立产生`Xk`及`Ck`。严格不把“`X400`导出后再代数算`C400`”称为“从时间视频独立FFT”。此外v086源自称“相对1e−6”，实际判断`err < 1e−6*max(1,max|C400|)`；当`max|C400|<1`时相当于**绝对1e−6门槛**。已报`3.52e−9`为最大**绝对**差，不要把它误写成相对误差。

另一源`source/run_v073_replay_corrected.m`：全幅MAT的正确键为`Xk`,`C_k`,`Imean`,`validMask`,`k`,`meta`，而v086 `inspect_h5`硬取`X400`,`C400`，因此全幅被误记UNKNOWN。旧`v072`的`fft(signal,[],4)`针对3D数组曾错误地在**时间维以外**操作；`replay_729_frames1000_3000.mat`仅作`LEGACY_WRONG_AXIS_NEGATIVE`，不能升级为正确实验观测。原v073已有12像元直接DFT对照表`tables/fft_replay_direct_dft_checks.csv`（12行全标PASS），但v087仍需从小ROI缓存作真正独立的逐像元重算并注明计算精度。

### 0.5 P0为什么这轮绝对不能输出测径

当前只有用户确定的光源520nm及7.29脚本的频率/帧；14μm传感器像元和50×物镜是历史未核实设置。小实验ROI41×41**形状相同不意味着**演示41×41区域具有同样的物方nm范围，真实物方scale尚未知。`NA/浸液/照明偏振与入射/参考场/实际曝光与触发/200Hz磁场矢量梯度和同步/颗粒固定或悬浮状态/复介电常数与涂层/背景噪声与独立标定`均不完整。不能从400Hz谱峰单独推出二倍频磁响应因果，更不能把处方振幅5/20nm或Querry文献常数当真实材料的绝对D标定。

---

## 1. v087执行顺序（每一阶段都能独立验收）

### 阶段A：固定源、修复排名索引及区间语义（纯后处理）

1. 固定v086 commit及 `v086_276_pair_distance_intervals.csv`、`v085_pairwise_276_stability.csv`实际Git/文件SHA；检查276键唯一，192跨D/84同D，数据正、有限、各状态24个无重复。
2. 真正分开计算192跨D候选中`argmin(d_shape_single)`、`argmin(d_shape_double)`，按`(distance,pair_id)`稳定排序并保存**pair_id与实测距离**；保留并核对旧距离`0.133264342648...`、`0.133264725326...`。
3. 对所有跨D以原来的`b_ij=epsilon_i+epsilon_j`计算`I_ij=[max(0,d_double−b),d_double+b]`；最近认证条件冻结为 `nearest_hi < min(other_lo)`；相同端点/零间隔时判 NOT_CERTIFIED，禁止通过小于原门槛的数值舍入来制造间隔。
4. 录入三角界**不保证**真实粒径、任意数值路径或未知真值的解释；区间只给定两条计算路径之间的经验路径偏差界，**不是**物理精度或置信区间。
5. 前置解析反例（不耗仿真）：A/B两对，各自`|d_d−d_s|≤b`，但实际argmin交换，旧判式给错误YES；新判式必正确返回NO。另测试两个区间恰好在端点接触的情形，严格认证必须NO，并对真正分离的两个区间设置正向PASS夹具。
6. 输出`v087_rank_logic_fixtures.csv`、`v087_rank_actual_argmins.csv`（至少两路径各1行）及`v087_ranking_decision.json`，保留`observed_rank_same=YES`、`triangle_interval_certified=NO`（如真实文件重算不同，输出真值与原因，不许硬写预期结果）。无需重读/重算原24张复图的时域过程；需要数组身份证据可复用v086已验证的SHA。

### 阶段B：校验器通路与mask规则（只读/小夹具）

1. 为`v086_identity_guard.py`增加**可供生产加载和异常测试共同调用**的掩码规则实检：`expected=finite(Imean)&(Imean>meanFloor)`，`meanFloor`作为具有来源的**全幅算子阈值**输入。对旧演示MAP若没有保存阈值/几何元数据，只能使用可追溯的公共源源码合同重算或标`SOURCE_METADATA_ONLY`，不能随意用局部样本中位数代替全幅阈值。
2. 真实负向夹具：有效mask包含低于冻结阈值的像元；无效mask藏有大于阈值的像元；Imean NaN/Inf；错误full-frame/ROI形状；错误q或fine slices；源hash不符。必须拒绝**正确类型异常**，先执行实际可通过的磁盘文件正例，不能让每个输入都无条件抛异常。旧`valid_mask=all1`不是全局规则的逻辑证明。
3. 通过真实`load_double_map`读取至少一个原源MAT，记录该入口确实经过文件SHA、case_id、shape、mask/mean-map一致性；`q`/slice不能由旧MAT文件内容直接证明时，另以实际共享`block_at/fine_slice`导出带源代码SHA的几何证据，不写成loader自含字段。
4. 删掉/独立标记`HEAVY_CALLS`未连接的伪真实计数；拒绝“所有生产计算入口都已插桩”结论。`NEG-G09`保持为`TEST_FRAMEWORK_SELFTEST`，不是数据级负向案例。
5. 输出`v087_mask_guard_live_tests.csv`、`v087_geometry_source_contract.csv`、`v087_guard_readback.csv`；失败不能覆盖或修改v086旧表，只创建v087文件。

### 阶段C：从缓存41×41×2001真实实验视频**重新做时间FFT**（本轮科学重点）

**唯一来源**：先读取`github_handoff/numeric/fft400_corrected_small_roi.mat`（与v073工作站原件SHA比对，历史已报完全相同），文件存在才能进行，且必须真正存在`roiFrames`字段。不可从已有`X400/C400`倒推出伪造的roiFrames。

1. **先检查结构不作假设**：`h5py.visititems`/MAT结构，记录`roiFrames`实际维度、dtype、compression、MATLAB`HxWx1xN`至h5py可能反序的轴映射、`rows`,`cols`、时间原点、`N/Fs/k`、full-frame全局`meanFloor`、`validMask`。源脚本显示实验完整传感器像为296×352，中心ROI全幅行128:168、列156:196（MATLAB 1基）；此为脚本定义的ROI而非颗粒定位。不要因为41×41空间对称就自行默认哪条h5py空间轴是行。
2. **源帧FFT独立验收**：必须从`roiFrames`每个像元的2001个**真实缓存采样强度**计算时均`Imean`、正确时间轴的复`X_160`、`C400=2X/(2001 Imean)`；所有FFT的起始采样为局部j=0..2000，不是物理场同步相位。先用2个非对称像元（且不互为相同数值）证实HDF5行列方向：正确X与缓存`X400`相容，错误转置必须被拒绝。**不能只靠`C400`代数恒等式判断时间轴正确**。
3. 选择固定的12个ROI内部抽点作double显式DFT vs NumPy FFT vs 已存MATLAB单精度`X400`，含角点、中心和非对称坐标；抽点在计算前固定，不能因为误差结果换点。原v07312像元实验DFT历史合同为`relative<1e−5 OR |ΔX|<1e−7`，其中绝对判据专用于近零；这一原工程门槛**只用于同等定义的抽点对照**，不扩展为模型物理验收。Double FFT/显式DFT另作独立浮点夹具，要求数值复位/相位一致；所有1681像元记录真实复差、最大值与分位数，近零行报告绝对差而非无意义巨大的百分比。
4. **重核有效mask**：必须使用**全幅源记录的`meanFloor`**（约`0.00011761607311200351`，最终以实际源值为准），与从缓存帧重算的ROI Imean比较`validMask = finite(Imean)&Imean>meanFloor`；禁止从**41×41ROI自身中位数**重算全幅阈值并冒充原方法。无效像元复C应为`complex NaN`并排除统计，而非零填充。
5. **full/small schema对齐**：只读`v073_return/numeric/fft400_corrected_full.mat`，按历史正确源`Xk,C_k,Imean,validMask,meanFloor,k,Fs,N,meta`适配；从全幅裁剪原`rows/cols`后对小ROI `X400,C400,Imean,validMask`逐项检查。适配不成就记录`UNKNOWN_SCHEMA`附打印实际字段清单，不用改源MAT或把不存在的键硬造出来。旧`v072_return/...replay...`须显式`LEGACY_WRONG_AXIS_NOT_VALID_REFERENCE`，不能拿其400Hz输出作新的正例。
6. **有限邻频诊断**（共享这一份缓存时间FFT，不另申请FFT）：固定MATLAB bins `158,159,160,161,162,163,164,169`，其中161是主400Hz，169是420对照；可另列200Hz bin81作为先验物理关联的**探索性观察**，必须独立标`EXPLORATORY`。按相同ROI与同一掩码输出每频段的强度计数/归一化复对比度**不同单位**、局部6邻频统计和同ROI背景诊断。邻频峰、400/420差别均不证明磁场因果、颗粒检测或其位移幅值；无场关闭/同步记录时不得给FPR或绝对D。
7. 该阶段只授权**从已有压缩MAT读取一次41×41×2001数据并进行必要纯计算**，不扫描BMP、不调用`render_system.m`、不新增物理轨迹/强度帧/曝光条件。缓存`roiFrames`不在或格式无法解码：输出`BLOCKED_SOURCE_MISSING/SCHEMA_UNKNOWN`及真实列名/shape，不从旧谱表拼凑时域波形。
8. 输出`v087_experiment_roi_schema_and_hash.csv`、`v087_cached_frames_fft_operator_audit.csv`（至少12探针＋全ROI汇总）、`v087_full_small_crop_identity.csv`、`v087_spectral_neighbors_fixed.csv`、至少一个非对称像元的真实2001点时序＋复FFT小NPZ（源字节SHA、shape/dtype和时间轴）；保存不具有实验尺度配准或绝对D含义的`NUMERICAL_TIME_FFT_PASS/FAIL`。

### 阶段D：实验物理门、标定计划和下一轮有条件物理阶段（零新求解）

保持实验参数分层：`USER_CONFIRMED`（520nm）、`EXPERIMENTAL_SCRIPT_RECORDED`（Fs/N/帧/bin）、`HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP`（200Hz场、14μm传感器像元、50×物镜）、`SIMULATION_ASSUMPTION`（65nm/像素、NA1.3、5/20nm横移、zf450/550、bulk Fe3O4光学常数）、`MISSING`。

拟进入磁场—运动—光学绝对D模型之前，必须有至少下列**来源明确的参数合同**，不能由GPT/Codex猜：

- **光学量尺**：实际物方nm/px或真实总倍率＋量尺样片；物镜完整型号、NA/浸液、照明方向/偏振、参考光路、基底/介质。
- **相机**：真实曝光τ、增益/位深、帧触发及时间原点，实际频率是否每批同为5000fps。
- **磁驱动/动力学**：200Hz实际磁场幅值矢量、空间梯度、B(t)实测/线圈位置与驱动同步；颗粒固定、受限或悬浮/旋转/平移机制。仅有频率比2不能证明磁响应因果。
- **材料/校准与负对照**：Fe₃O₄批次核/包覆/尺寸分布、介质黏度及离界面高度；TEM/SEM/可靠标准球，独立背景/空白/磁场ON/OFF对照。无这些不能把24状态的形状距离转为测径准确率或噪声统计。

建议的未来实验设计（本轮只写方案不主动采集）：同一FOV固定增益曝光、配套B(t)同步记录的磁场ON/OFF、驱动频率改变的锁相频谱对比、物方尺度标定标准；每项必须先规定对照、盲区域与成功判据。**不是**在没有输入时启动新BEM、粒径曲线或新实验样本。

### 阶段E：P0独立资源门

保留P0三矩阵direct/reflected/total分别`<1e−10`门槛；历史最好约`2.58848e−7`未达。仅在许可证、进程身份、安全条件和旧继承预算同时满足时，最多一次**被动只记录Hook**；MATLAB进程数为零并非许可证安全依据。`rule7`新大型参考预算**0**。P0不得阻断不涉及该求解路径的纯实验缓存FFT。

---

## 2. v087资源预算及停止逻辑

| 工作 | 本轮允许额度 | 不可越界 |
|---|---:|---|
| 新BEM solve、新位置复场render | **0 / 0** | 历史已做的24双精度图不得重算 |
| 新处方轨迹2001帧或新合成曝光、噪声批次 | **0** | 本轮不扩物理模型 |
| 原7.29 BMP重新读取 | **0** | 仅使用压缩小ROI旧视频缓存 |
| 排名与区间判据修正 | 192跨D排序＋276原表只读、2个纯数学负向夹具 | 不改变距离、掩码、场或既有ε |
| 生产guard规则与几何来源复核 | 1个磁盘正例、必要无昂贵成本的错误夹具（≤8项） | 新增工程守卫不能覆写老图原数组 |
| 实验缓存FFT | **最多一轮原41×41×2001缓存视频沿时间维FFT** | 不是新增实验/重新BMP |
| 时域显式DFT抽点 | **固定12个像元，每点N=2001** | 双精度数学核验、独立于存储X400 |
| 固定邻频诊断 | bins158:164及169（MATLAB索引），从同一FFT取得 | 200Hz bin81若诊断须独立标探索 |
| 全幅与ROI文件契合 | 仅读已有2份MAT（零新全图FFT） | 适配源schema，不修改文件 |
| P0被动Hook | 旧剩余最多一次，安全前置成立才执行 | rule7 0笔 |

**自动执行**：A判据独立修正→B生产守卫→C实验缓存FFT/全幅匹配→D参数与实验设计→E安全P0；每支线失败只暂停依赖子分支，其他工作继续。实际无法读视频缓存时**不许临时读BMP或重复任何BEM**。任一工作对用户新增计算成本，必须严格记入账本而非零填。

---

## 3. 正式验收与唯一返回物

Codex必须发布真实可读的`v087`分支（commit SHA）并一次性交回真正的`iscat_v087_return.zip`，包含：

```text
iscat_v087_return.zip
  00_README.md / 00_全部文本汇总_v087.md / 00_Codex_v087_执行指令.md
  status.json / review.md / manifest_sha256.csv
  source/
    run_v087_A_rank_and_interval.py
    run_v087_B_guard_and_mask.py
    run_v087_C_cached_experimental_fft.py
    run_v087_C_full_small_adapter.py
    ... 实际用过的脚本及测试、SHA256 ...
  tables/
    v087_rank_logic_fixtures.csv
    v087_rank_actual_argmins.csv
    v087_ranking_decision.json
    v087_mask_guard_live_tests.csv
    v087_geometry_source_contract.csv
    v087_experiment_roi_schema_and_hash.csv
    v087_cached_frames_fft_operator_audit.csv
    v087_full_small_crop_identity.csv
    v087_spectral_neighbors_fixed.csv
    v087_experimental_parameter_readiness.csv
    v087_budget_ledger.csv / v087_p0_status.csv
  numeric/
    ... 至少固定两个非对称实验像元真实2001点序列/复DFT小NPZ ...
  logs/
    commands_versions_actual_sources.txt
    source_SHA256_and_lineage.csv
    independent_csv_npz_readback.log
    failures_and_skipped_dependencies.log
  history/
    ... v086纯数学成果索引、原表SHA与SOURCE_ONLY说明 ...
```

强制有`execution_status,validation_status,evidence_status,scientific_scope,source_SHA,budget_used`。所有CSV必须严格行宽、唯一键、正确单位/复数Re-Im、NaN/mask策略，实际新生成的小数组独立读回并与原源SHA关联。MATLAB源码与Python复算来源必须清楚，不得以已保存X400/C400的代数回代冒充时域独立FFT。未运行、读不出或源缺失必须输出真实`BLOCKED_*`，不得以“方案预计”充PASS；旧v086科研成果保留，不为改报表重算。

冻结最终科学状态：`calibration_valid=false`、`experimental_validation=false`、`detection_validated=false`、`single_particle_diameter=NOT_ESTIMATED`。只有未来物理参数、独立标定和磁驱动对照提供后，才另行申请真实磁运动—光学耦合与新的BEM预算。

---

## 4. v086固定证据路径（Git blob SHA-1仅作版本身份）

| 证据 | 路径 | blob SHA-1 | 对应事实 |
|---|---|---|---|
| V1 | `status.json` | `3d7ce422b94085ffacc03ff7cf6fc690d83e9f54` | v086顶层宣称；与表/源码拆分 |
| V2 | `source/v086_identity_guard.py` | `7841ac89cdc4a0a18995c42ef979a70cc9b47f4b` | 部分真实数据守卫、mask未实际重算历史规则 |
| V3 | `source/v086_negative_tests.py` | `c19762dfb3fdf3d5a124d06f78d9fad39f03aa71` | 11行测试（1正、9实际错误注入、1假validator探针），虚拟heavy counter |
| V4 | `source/v086_recompute_24_maps_and_276_pairs.py` | `ba7e1ac8523259fba373b87649ada2966863a2e8` | observed_same使用三角界错误代理；区间判定需严格重构 |
| V5 | `source/v086_experimental_cached_observable_interface.py` | `9f95c77d6670dfd4c47ea843f61d72ac6ebaead5` | X/C回代、k160/161宽松、全幅schema不匹配 |
| V6 | `tables/v086_24map_source_identity.csv` | `f9f05d67363d9a73c5cb30913b5ee6bbd342e942` | 24实际文件、SHA和算术比对 |
| V7 | `tables/v086_276_pair_distance_intervals.csv` | `4f42c319e1abb5e7631dc0b8167b06bacdb4e4d4` | 276对距离、区间、两路径观测最近对 |
| V8 | `tables/v086_cached_experimental_observable_interface.csv` | `9c3493ffcfdd534becebbe4a273244e0fbe89d5f` | 小ROI source同SHA、存储变量X→C最大绝对差3.52e-9、full/replay未适配 |
| V9 | `experimental/observable_contract_v073.json` | `a85c0a21dc08d65a6b1cbee84f061d5cd4457d0e` | 真实观测定义、全幅mask、bin与NaN策略 |
| V10 | `source/run_v073_replay_corrected.m` | `7088af0d96522a595be04ba491172a68f2f1bf39` | `roiFrames`真实保存、full Xk/C_k与small X400/C400、timeDim4 |
| V11 | `source/extract_fft_v073.m` | `d0d165d2a739f27c226184fe054f1a7932d402a1` | FFT与mask正确纯函数、时间轴守卫 |
| V12 | `source/run_v072_replay.m` | `7c03614ce541e76857d8791d13bc729ea7b67877` | v072历史3D误用FFT第四维，负向对照 |
| V13 | `logs/v086_ranking_certification_summary.json` | `fb1856a7ad4d5bdda1642ae7ebc85182e17f71f7` | 最近区间交叠，排名NOT_CERTIFIED |
| V14 | `tables/v086_budget_ledger.csv` | `5686b6a092345ad77e6fc8e2b328615e2b1649a6` | 零BEM/零新时间评价成本约束 |

**交给Codex的唯一执行口令**：请从锁定的`v086@4fd783e5438a6cae3a9801711a13cb1db3c75f84`和工作站真实缓存连续执行v087指令。保留24张双精度复C400图和276对已通过的数组证据；以独立argmin修复单/双精度候选排序判据，按严格interval upper<others lower给出认证（不得伪造PASS）；真实生产guard补mask规则与磁盘正例；从v073小ROI缓存的真实`roiFrames`直接FFT并比对已存`X400/C400/Imean/validMask`，适配全幅`Xk/C_k`，旧v072错误时间轴仅留作负控。零新BEM/位置render、新物理/曝光节点、零原BMP重读；参数未证实继续冻结实验绝对D与磁场因果。满足条件自动连续执行，最后一次性返回真正的`iscat_v087_return.zip`和GitHub v087固定分支。
