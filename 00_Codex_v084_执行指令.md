# iSCAT / Fe₃O₄ v084 唯一连续执行指令

## 固定 v083 审查、非对称像元索引纠错、数值证据收口与有限空间观测量诊断

> **本文件性质：下一轮给 Codex 的执行合同，不是 v084 已经执行完毕的仿真结果。** 在 Windows 工作站使用真实历史 MATLAB/HDF5 缓存持续运行全部满足前置的项目，失败只阻塞依赖分支，不必每步停下等 GPT。结束时一次性返回**一份真实 `iscat_v084_return.zip`**与**固定 SHA 可读 GitHub `v084` 分支**。不得把本指令包或 `v083` 的 CSV 当作工作站 v084 返回包。
>
> **唯一锁定父提交：** `yyyyzoey/iscat-handoff`，`v083@79140295855c76cd42f11ae84be7f837ba96f485`（其父为 `v082@0fbebbb1db863a7ad79081ea470e907b442781d4`）。只对该不可变提交作历史事实判断；新改动另存 v084，不回写原证据。
>
> **冻结边界：** 用户确认实验激光真空波长 **520 nm**。7.29批次提取脚本记录 `Fs=5000 fps`、frames `1000:3000`、`N=2001`、目标 400 Hz 对应 `k0=160` (零基)、MATLAB bin161、实际 `399.800099950025 Hz`。候选复数观测算子为 `Cbin=2 X_160/(N Imean)`。历史200 Hz磁场、14 µm传感器像元、50×物镜均是**最终配置未核实的记录**。演示的65 nm/物方像元、5/20 nm预设横移、zf450/550 nm、Querry文献Fe₃O₄常数**不是**已经标定的实验参数；尚无磁场因果、真实运动约束或单颗粒绝对D。
>
> **硬预算：** 新BEM求解**0**；新位置复光场render**0**；7.29原BMP全量重读**0**；新粒径/焦面/材料/运动/噪声/曝光扫描**0**。已完成 v082 的24条满秩谐波、96条贡献、24条残差、16次合成曝光和v083的4个双精度全ROI、2次64节点曝光全部保留，不为报告修复重算。新增仅为后文明确授权的已有状态纯后处理。

---

## 0. 本次独立源码、表格审查裁决：正式成果与错误断言必须分开

本指令依据固定 v083 的 `status.json`、`review.md`、`source/v083_common.py`、`source/v083_pixel_identity_repair.py`、`source/v083_roi_precision_controls.py`、`source/v083_exposure64_two_conditions.py`、`source/v083_observable_screen.py`，以及对应CSV、运行记录审查。没有在 GPT 环境运行用户工作站MATLAB/大型光场；以下表格数字是已发布文件的结构与算术核对。

| 编号 | v083实际证据 | 严格裁决 |
|---|---|---|
| A1 | `v083_correct_center_series_identity24.csv` **24行×30列**，`SAME_PIXEL_SAME_OPERATOR_VERIFIED`共24；保存小MAT的正确中心时序与v083重建f32时序`max|ΔI|`在 **4.6566e−10至1.86265e−9**，小于已用工程守卫`1e−8` | **接受“真中心时序与小MAT在现有强度数值门槛内相容”**。不可把此结论升级为弱C400同等相对误差已通过。 |
| A2 | 同表 `legacy_col1_bug_recon_maxdiff` **24/24均超过1e−8**（**1.0998e−5至4.2394e−4**），`evidence`均明确打印`bug NOT_PROVEN`，但v083 status写`legacy_bug_proven=true` | **撤回“历史旧像元已数值证明”的总括声明**。上游MATLAB源码仍明确记录的是`Ipix(21,1,1,:)`，只是本轮Python的对应像元调用有误。 |
| A3 | `v083_pixel_identity_negative_tests.csv` 7行全部`PASS`，但其中非对称轴序负向测试未正确指向待证明的真实(row21,col1)路径 | 接受实际已运行的负向输入被拒绝，不接受它已独立认证所有坐标映射。 |
| B | `v083_harmonic_complex_closure_X0_corrected.csv` 24条复数闭合，最大`closure_full_rel≈3.92229e−14`；`|X0|`最大`3.51572e−21`；`v083_phase_columns_corrected.csv` 42行，30 RESOLVED、12 UNRESOLVED_NEAR_ZERO | 继续接受 v082 数学闭合；v083修正的显式截距项不改变其历史通过结论。近零相位不当作磁场同步相位。 |
| C | `v083_fullROI_precision4.csv` **4×25列**和4份复图；两种数值路径的整图Frobenius相对差 **1.09495e−5 至 1.15722e−4**；D60/zf450/M400/a5中心复差约 **6.00065e−8** | 保留有限数值敏感性诊断。地图坐标方向需用非中心像元独立确认；大范围Frobenius接近不代表弱中心已稳定。 |
| D | `v083_exposure64_target2.csv` **2×24列**，D60/zf450/M400/a20、合成200µs时32→64幅值增量`1.56402e−9`（相对32节点`8.85539e−4`=**0.08855%**）；M200/a20为`7.17732e−9` | 2次真实高阶纯时域评价已完成，不再补充曝光节点；只是有限采样数值趋近，τ非真实曝光。 |
| E | `v083_nuisance_observables24.csv`24状态，`v083_nuisance_feature_pairwise276.csv`276对（192跨D、84同D）。最小跨D shape-Frobenius约**0.1332647253**：D30/zf550/M400/a20 与 D60/zf450/M400/a20 | 保留为离散开发筛查；**不能**据此推出实验不可辨识、物理误差或粒径RMSE。 |
| F | P0被动Hook未执行，历史`2.58848e−7`仍高于三矩阵各`<1e−10`，rule7 0次授权 | 继续独立 OPEN，不影响纯后处理；不因0个MATLAB进程就擅自启动昂贵BEM。 |

### 0.1 确定性坐标错误及其校正

历史源 `source/run_v076_C_dynamic_center.m`（由v083 `history/v076_tseries_center_col1_bug_source.txt`引用）确实是：

```matlab
ci=(L+1)/2;             % 21
cc=o.C_k(ci,ci);         % 真中心: MATLAB row21,col21
...
 'tseries_center',double(Ipix(ci,1,1,:))  % 遗留字段: MATLAB row21,col1
```

而新 `source/v083_common.py` 明确约定接口 `block_at(D,zf,r,c)` 的`r,c`均为 **MATLAB物理像元 `(row,col)`**；内部HDF5数组`Es`空间轴顺序是 `(MATLAB col, MATLAB row)`，故该函数使用 `Es_i[:,cs,rs]`。v083主检查写了：

```python
# v083错误：这是 MATLAB (row=1,col=21)，不是(row=21,col=1)
s_bug32 = recon_series(D,zf,ttype,a, 1,21,dtype=np.float32)
# 应改成：
s_legacy21_1 = recon_series(D,zf,ttype,a, 21,1,dtype=np.float32)
```

所以**v083内部“遗留字段已数值复现”的口头结论被其自己的原表全部反证**。不可简单修正注释或改表状态冒充数值已完成。正确处理应从未改动的5个有符号锚点重新恢复**同一历史row21,col1旧时序**，与已保存`tseries_center`逐帧对比；先在不对称像元实证HDF5/MATLAB轴映射，不可用中心(21,21)的对称性规避轴交换错误。

### 0.2 历史“负向测试通过”不等于像元方向正向验证通过

`transposed_axis_recon`原实现用`fine_slice(CENTRE)`；由于中心row=col=21，这个测试不具有识别空间轴转置的能力。当前`NEG-P02b`将其与另一个不对称像元结果比较，能产生非零差，但**没有验证“正确读出MATLAB(21,1)并与历史时序逐帧相等”**。在v084必须补充针对 `(21,1)` 与 `(1,21)` 的单独正向/负向判别以及来源哈希，不得仅复用旧PASS。

---

## 1. 执行规定与预算、状态语义

1. 冻结上述 GitHub v083 SHA、历史 v076/v074 文件SHA与真实Windows源路径；源不足时保留`MISSING`并仅暂停依赖支线，**不根据CSV构造虚假光场或新物理状态**。
2. 主体系仍保持 `N=2001, Fs=5000, k0=160, q=5`，全幅65×65物理像元、41×41 ROI为物理像元13:53、精细像元61:265（1基）。全幅物理中心(33,33)，ROI物理中心(21,21)，对应精细161:165。**这些属于演示成像网格，不是实验物方65 nm/px已标定。**
3. 数值身份检查必须包含四种正交证据：MATLAB生成行列索引、HDF5轴顺序、独立非对称像元时序逐帧差、与正确中心不同的负向结果。显示并保存`which`及运行源码SHA；优先选取真正发生空间变化的测试像元，不以中心转置不变作为轴序证明。
4. 沿用 v083已冻结的**同算子逐帧强度绝对差`<1e−8`**作为旧字段正向比对的*数值身份工程门槛*，如果不能通过则保留真实差值与失败，不允许现场放宽；相机完整复FFT比较须另报**绝对复差**及归一化、近零无可靠相对值状态。该门槛不能替代已有静态 `<2%`、复场插值 `<0.001`、P0三矩阵各 `<1e−10`、谐波复闭合 `<1e−10` 等原合同。
5. 允许Codex在单个A试点成功后自动执行全部24个旧条件的这一**纯时域后处理**；成功/失败计数只有在数组存盘、CSV合法读回、独立进程来源复核后才更新。任何 `NOT_PROVEN`不得写`PROVEN`。
6. 保留所有原文件作为只读历史；新阶段输出 `v084_*`，不能覆盖v082/v083旧数据或将旧指标改列名后当作重新验算。

---

## 2. 阶段A：单试点→24例，证明v076旧像元行列身份（最高优先级）

### A0. 只执行一条试点 `D60_zf450_M200_a5`

- 恢复实际5个`x ∈{-20,-10,0,+10,+20} nm`的原`Es/Eref`锚点与原处方`x(t)=5cos(2π·200t)`，用现存光学复场进行插值、完整干涉强度，按5×5子像元平均形成物理相机像元时序。
- 先用**独立MATLAB旧源码/对象数组**明确`Ipix(row,col,1,frame)`实际形状。如果许可证/进程不能安全启动MATLAB，则仅在HDF5非对称像元+旧MAT原字段上完成相应证据，标明仍未执行的独立MATLAB步骤。
- 分别恢复 MATLAB `(row,col)=(21,1)`、`(1,21)`和真中心`(21,21)`，在HDF5约定下对三个点分别打印精细`rs,cs`索引：`Es[:, cs, rs]`，不得在代码中从视觉直觉调换row/col。
- `v076_dynamic_center_corrected.mat` 的字段`tseries_center`应仅同`(21,1)`比较。`v076_center_roi_harmonic_small_examples.mat` 的`series`应仅同`(21,21)`比较。分别保存2001个值、源SHA、重建算法SHA、均值、逐帧最大强度差、复数`Xbin/Cbin`与中心小MAT差；设错误的 `(1,21)` 必须在选定非对称哨兵上被拒绝。
- **强制门槛**：正确历史像元比对 `max|I_old_recon-I_legacy|<1e−8`；真中心现有证据继续保持 `<1e−8`，且两个像元不能被识别为同一身份。若同源浮点路径不一致导致超门槛，应审查形状、HDF5轴、存储类型与像元积分顺序，而**不是**增加BEM或放宽阈值。
- 单case结果新会话、标准CSV及NPZ/HDF5/MAT读回完整通过后，标`PILOT_PASS`，自动放行A1。失败时A1依赖暂停，但数学谐波和曝光已通过的独立支线继续保留。

### A1. 扩至原24个已有状态（零新物理条件）

- 输入固定 `D={30,60,100} nm × zf={450,550} nm × ttype={M200,M400} × a={5,20} nm` 共24个且**唯一**的旧状态。每例只恢复历史 MATLAB `(21,1)`时序并与历史存储字段比较；小MAT真中心数值不为凑数再次进行24次完全重复分析，可读v083已合格记录。
- 每例输出`legacy_row,legacy_col,true_row,true_col,matlab_ipix_shape,hdf5_axis_mapping,raw_anchor_sha,source_series_sha,N,series_dtype,mean_old,mean_reconstructed,max_abs_series_diff,relative_L2_series_diff,Cbin_Re/Im_diff,wrong_axis_diff,physical_status,evidence_status`。
- 状态只能是 `LEGACY_COL1_NUMERIC_VERIFIED`、`LEGACY_COL1_NUMERIC_FAILED`、`LEGACY_COL1_MISSING_SOURCE`；若代码仍调用`(1,21)`或只打印已有v083报表则不得标VERIFIED。
- 另外留下1个带非对称像元的独立干净会话/小MAT，既可以复核HDF5转置，也可核查真实物理像元名字与采样中心。

---

## 3. 阶段B：空间轴约定与原四张双精度C400图的审查（优先零次新的时域评价）

在A试点通过后，从v083已保存4份`v083_fullROI_double_C400_*.mat`和v076旧C图，检查以下**纯读取与数组比较**：

1. 原文件`C400`数值array的MATLAB `(row,col)`语义 vs h5py读取的(列,行)；以非中心至少3个不同的物理像元进行各自Re/Im/meanI/valid_mask的索引映射，**不能**只取中心或比较同名41×41数组的Frobenius。记录经必要固定转置后的比较和错误转置的负向结果。
2. 同一个有效掩码（交集由同一冻结阈值和两侧finite定义）比较双精度/单精度复C400的展平像元Euclidean L2：`rF=norm((C_double-C_single)(:),2)/norm(C_single(:),2)`。旧v083四行报告`1.09495e−5…1.15722e−4`保留为历史诊断，若更正空间方向后数值改变必须**两套并列**，不能覆盖。
3. 独立把一个旧条件的2001帧光强经过原`extract_fft_v073`或有源的MATLAB FFT实现后，与 Python DFT复输出比较。使用`k0=160`与相同有效掩码，保存绝对误差和公共输入哈希；输入不同或轴映射未证实时标`NOT_COMPARABLE`，不以数值相近冒充通过。
4. 将M400中心近零和整幅ROI Frobenius差分开；整图达数值精度不代表最弱中心量精度。`NO_NEAR_ZERO_RELATIVE_CONCLUSION`状态必须保留。

这项可以优先零新全ROI计算：先用4份已发布双精度复图作数据身份/朝向核验。只有证据确实缺失但原锚点仍在且预算已允许的情况下，才允许对**同4个旧条件中至多1条**重算双精度ROI以作轴序最小验证（计入下表条件恢复，不新增光学场/物理状态）。

---

## 4. 阶段C：唯一新增的**2条**有限双精度全ROI对照——只为检查最接近跨D的shape对

**前置：** A试点与B空间方向至少在对应ROI和源身份上通过；不然C标`BLOCKED_DEPENDENCY`，不新增任何后处理次数。

既有`v083_nuisance_feature_pairwise276.csv`的最小跨D shape-Frobenius对（固定且属于开发中发现的条件，**不是盲测**）：

- `D30_zf550_M400_a20`
- `D60_zf450_M400_a20`

历史shape-Frobenius：`0.13326472532638595`，用的是 v076**单精度** `C400`图；v083的4个双精度复图**不包含**这两个a20端点。因此不能在未经双精度校验时把这对当成已经验证的数字稳定shape配对。

**本轮显式且独立授权**：最多对这两个**已有状态**各做1次41×41复C400流式双精度时域后处理，共**最多2次**；必须复用原30个有符号复场位置锚点，不能新render或BEM。输出：两个完整复图MAT、真实数组shape/来源SHA、像元方向、公共mask、各自对v076旧图的Frobenius数值差、幅值L1/L2、中心值和形状归一化后两者距离；另输出旧单精度距离、双精度距离及其绝对差。可新增同D固定状态诊断标量，但**不允许**从这两例推出全域、噪声鲁棒性或粒径准确率。

不得再做额外新D、zf、a、频率、τ、噪声实现或自由相位/幅度配准来获得更好的距离；`shape=abs(C)/||abs(C)||F`这一消除整体幅度的操作本身会丢掉幅度信息，应与原复图、绝对幅值特征分别报告。

---

## 5. 阶段D：已完成的其他数值成果按原范围继承（零次新求积）

1. 24条满秩谐波和96条逐频贡献、24条复数残差继承v082；v083显式X0完全闭合的24条保留。不得为新v084重复24次QR拟合。复数DFT/LS不同是有限窗算子定义，不把基函数峰值直接替换为实际FFT频点。
2. v083已完成的两个64节点积分 **used=2/2**；v082原16次16/32节点已**used=16/16**。本轮新增曝光求积 **0次**。只读复核M400/a20/200µs旧32→64绝对`1.56402e−9`，M200/a20绝对`7.177315e−9`及各自状态`SYNTHETIC_TAU`。相对值不作为仪器误差。
3. 旧270条奇偶、24条相机ROI、276对既有配对保留，只读重聚合；除上述固定最接近形状两状态外不得新增独立物理条件或重复全套统计。
4. 真实520nm实验激光、400Hz目标的复数归一化提取约定继续保持。200Hz磁驱动只是历史记录，磁场幅值方向梯度/真实同步/真实位移等未确认，不能把模拟轨迹5/20nm当作实测。

---

## 6. 实验物理接口：不等用户补完参数才做纯数值工作；不冒充绝对D

必须保留独立`parameter_readiness.csv/json`：

| 参数 | 地位 | 能做/不能做 |
|---|---|---|
| 用户明确确认的真空激光波长520nm | `USER_CONFIRMED` | 允许纳入真实光学前向输入 |
| 7.29脚本Fs5000/N2001/bin161 | `EXPERIMENTAL_SCRIPT_RECORDED` | 允许据其研究本批FFT，不能推断所有采集批次一致 |
| 200Hz交变磁场、14µm像元、50×名义倍率 | `HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP` | 保留记录，不改写为最终证实 |
| 实际物方nm/px、NA/浸液/入射偏振、曝光与同步、磁场幅值/梯度/波形、颗粒批次光学性质/包覆/介质、真实运动机制与高度 | `MISSING`或`PARTIAL` | **阻止实验匹配的绝对粒径前向反演**，不阻止A-D数学后处理 |
| 演示65nm/px、横移5/20nm、zf450/550、文献Querry数据 | `SIMULATION_ASSUMPTION` | 只能描述已批准演示系统 |

在没有校准标准、噪声估计及磁场—运动动力学物理合同前，`calibration_valid=false`、`experimental_validation=false`、`detection_validated=false`、`single_particle_diameter=NOT_ESTIMATED`不变。不得假设“二倍频幅值”必然来自磁颗粒；不出论文式实验测径误差条。

---

## 7. v084唯一预算账本（新增与继承严格分列）

| 工作 | v084允许新增 | 执行条件与计数 |
|---|---:|---|
| 新BEM solve | **0** | 绝不重算均匀/分层的30/60/100旧场 |
| 新Fe₃O₄位置复场render | **0** | 原30有符号锚点只读 |
| A试点历史(row21,col1)纯时域重建 | **1条** | A1包含该例，不得重复计账 |
| A阶段完整旧row21,col1 24状态数值复核 | **最多24条** | 包含试点；前置失败则暂停批量 |
| B原4幅双精度ROI的文件/像元身份核对 | **零新评价优先** | 如确缺源证据，最多1条既有状态小范围时间恢复，**只用于身份**，不得扩成额外5个ROI |
| C最接近跨D固定配对的额外双精度全ROI | **最多2条件** | **本轮明确新增的窄范围纯后处理授权**，通过A/B前置才执行 |
| 已执行v082的16/32曝光 | **0新增** | 历史16/16已耗，不得重置 |
| 已执行v083两个64曝光 | **0新增** | 历史2/2已耗，不得重置 |
| v082/v083谐波、奇偶、24ROI、276对 | **0新物理计算** | 只读核查和派生计算 |
| 原7.29 BMP全量重读/新采样/噪声批次 | **0** | 与本任务无关 |
| 新D、zf、磁场、波长、a、τ参数点 | **0** | 不得更改物理问题 |
| P0被动Hook | **继承原最多1轮** | 许可/进程安全前置通过时才执行；MATLAB进程为0不是安全凭证 |
| rule7大参考 | **0** | 保留P0三矩阵各`<1e−10`和原rule7全部专属门槛 |

所有原v083消耗“24中心重建+4ROI+2x64”不清零；v084额外的2个ROI、24条错误像元重建为本次**明确新增**的有限数值后处理额度，不是扩大BEM预算。

---

## 8. 返回交接规范——**用户下次要的是v084结果ZIP，而非计划文件**

Codex必须在本机产出`iscat_v084_return.zip`，实际包含以下内容并发布同样路径到可读GitHub `v084` 分支：

```text
iscat_v084_return.zip
├─ 00_README.md
├─ 00_全部文本汇总_v084.md
├─ 00_Codex_v084_执行指令.md
├─ status.json / review.md / manifest_sha256.csv
├─ source/
│  ├─ run_v084_asymmetric_pixel_pilot.py
│  ├─ run_v084_legacy_col1_recheck.py
│  ├─ run_v084_roi_orientation_validation.py
│  ├─ run_v084_nearest_shape_pair_double.py
│  └─ actual_tools_sha256.csv
├─ tables/
│  ├─ v084_asymmetric_pixel_pilot.csv
│  ├─ v084_legacy_col1_identity24.csv
│  ├─ v084_pixel_axis_negative_tests.csv
│  ├─ v084_roi_orientation4.csv
│  ├─ v084_nearest_shape_pair_double2.csv
│  ├─ v084_existing_harmonic_exposure_inherited.csv
│  ├─ v084_parameter_readiness.csv
│  ├─ v084_cost_ledger.csv
│  └─ v084_p0_status.csv
├─ numeric/
│  ├─ v084_asymmetric_pixel_pilot.npz
│  ├─ v084_double_C400_D30_zf550_M400_a20.mat    # C前置PASS时才有
│  └─ v084_double_C400_D60_zf450_M400_a20.mat    # 同上
├─ logs/
│  ├─ native_or_python_run.log
│  ├─ independent_csv_mat_readback.log
│  ├─ case_failures_and_stacktraces.log
│  └─ cache_source_identity_sha256.csv
└─ history/    # 保留v083的真实bug NOT_PROVEN记录和旧摘要，不覆盖
```

每个case必须记录`execution_status`、`validation_status`、`evidence_status`和`scientific_scope`；源时序/复图MAT在工作站而未交到ZIP时严格写`WORKSTATION_ONLY`和真实路径/尺寸/hash。**0个错误行、正确数量、CSV字段等宽、唯一键、字节/变量身份、干净会话独立读回**是宣称完成的前置条件。Git blob SHA-1不得当文件SHA-256。对新2幅ROI必须从真正计算数组提交，不能把v076旧图改名。

总判定：A试点未通过时`legacy_col1_proven=false`，即使旧源码显然使用`Ipix(21,1)`也不得盖章“数值已证”；如果C前置失败，则只能报告`NOT_EXECUTED_DEPENDENCY`。零新增BEM和旧门槛保持，已完成历史数学成果按其各自范围保留。最终仅交**一个真实执行结果ZIP和固定commit的v084分支**，无需每步GPT批准。

---

## 9. 固定v083关键证据路径与SHA-1(blob)索引（供Codex逐项核对）

| 编号 | 固定提交内路径 | Git blob SHA-1 | 证据 |
|---|---|---|---|
| V1 | `status.json` | `b9c54c7d1a17eaffebf43e1be1a4639f0b51bc0a` | `legacy_bug_proven=true`，与原CSV相矛盾 |
| V2 | `source/v083_common.py` | `94eddf8ccc4f1f7ee83604a9b68ccceae3005efe` | HDF5轴顺序与`block_at(r,c)` |
| V3 | `source/v083_pixel_identity_repair.py` | `ce7de1421cde2dfdec2ba58c1e583fdc6f9e326d` | `recon_series(...,1,21)`误用；原`bug NOT_PROVEN` |
| V4 | `tables/v083_correct_center_series_identity24.csv` | `6f8d8f8781bd0966427e0db7b6b51c39f2ef4749` | 24例同中心通过、24例旧列数值未证 |
| V5 | `history/v076_tseries_center_col1_bug_source.txt` | 从固定文件树读取实际SHA | 原MATLAB `Ipix(ci,1,1,:)`源码引用（原数值9.3e−10未证） |
| V6 | `tables/v083_pixel_identity_negative_tests.csv` | `1ab1a0d34ebb7005409e109bdc1c1c569abc969a` | 7条旧负向；不能证明正向(row21,col1) |
| V7 | `tables/v083_fullROI_precision4.csv` | `7f42148e4e406b41357570da977e5e20514fcbca` | 4条数值路径有限精度诊断 |
| V8 | `tables/v083_exposure64_target2.csv` | `789f5aee854b03c838e4f13e0bbf9dd5d9d2805a` | 两次真实64节点时域后处理 |
| V9 | `tables/v083_harmonic_complex_closure_X0_corrected.csv` | `a83f651c2f0377f1079c5da718a00f8793addd81` | 24条X0显式复数闭合 |
| V10 | `tables/v083_nuisance_feature_pairwise276.csv` | `c53f8667fab16147bbc158929a66a003ab8853ce` | 276对，最小跨D shape 0.1332647 |
| V11 | `tables/v083_experimental_parameter_contract.json` | `5e7d93c4fac93a007b1655cc8df21e263681f4d4` | 六大实验参数缺口 |
| V12 | `tables/v083_cost_ledger.csv` | `ed22570d2fe0faca32b9cf69deb0d99095badd67` | v083预算已经消耗 |

### 给Codex的唯一执行口令

> **请完整执行此v084唯一指令，从 `v083@79140295855c76cd42f11ae84be7f837ba96f485` 与真实工作站缓存继续。第一优先修复HDF5轴转置下的非对称像元调用，必须用 `recon_series(D,zf,ttype,a,21,1)` 而不是旧的 `(1,21)`，先完成D60/zf450/M200/a5试点真实逐帧数值比对和负向测试，再自动处理至多24个历史条件。保留24条正确中心已通过和旧数学结果；检查4张双精度图的像元朝向，若通过则在本轮新增至多2个现有固定状态的全ROI双精度纯后处理检验最接近跨粒径shape对。零BEM、零位置render、零新物理节点、零新曝光评价，不放宽门槛；实验参数缺口保留，P0仅按原安全条件独立处理。完成全部可执行任务后一次性返回真正的 `iscat_v084_return.zip` 和GitHub可读v084分支，不必逐步等待GPT。**
