# iSCAT / Fe₃O₄ v088：v087严格审查、频谱坐标纠正、生产掩码作用域与缓存实验时间稳定性诊断

> **文件性质（关键）：** 本文是给工作站 Codex 的 **v088下一轮唯一执行合同**，不是已执行的 v088 结果。收到本文件后，从固定 v087 提交和真实工作站缓存连续运行所有满足前置、未超过预算的任务；不能每执行一步就要求 GPT 重新批准。最终一次性提供真实 `iscat_v088_return.zip`、GitHub可读 `v088` 分支及不可变commit。GPT提供的 `iscat_v088_Codex_交接包.zip` 只是指令/辅助工具包，不得冒充工作站执行结果。
>
> **固定唯一父提交：** `yyyyzoey/iscat-handoff` 分支 `v087`，commit **`900417f2cdcdec45097ea1f8c766f58d9548ac0f`**；其父 `v086@4fd783e5438a6cae3a9801711a13cb1db3c75f84`。审查不得随移动的 `HEAD` 改写历史事实。
>
> **绝对冻结预算：** 新BEM solve **0**，新Fe₃O₄位置复场render **0**，新物理粒径、焦面、材料、运动幅度/类型、曝光或噪声参数点 **0**，原始7.29 BMP重读 **0**，新模拟2001帧**0**，旧24张双精度复C400图重新生成**0**，旧276对物理条件**0**。本轮仅许可：旧数表数学/元数据修复、少量真正的生产守卫夹具，以及对**已缓存同一41×41×2001实验视频至多1次受限分段分析**。P0仍继承原最多1次**安全前置充分**的被动Hook；rule7大型参考**0授权**。预算不能静默重置。

## 0. 物理和实验输入，禁止跨层误读

1. **用户明确确认：** 真实实验激光真空波长 **520 nm**。
2. **原7.29批次脚本有证据：** `Fs=5000 fps`、`frames 1000:3000`、`N=2001`、`k0=160`（0基）、MATLAB FFT索引`161`，固定bin实际频率 **`399.80009995002496 Hz`**。主观测量是复归一化调制对比度 `Cbin=2X_160/(N*Imean)`，其中 `X_160=Σ_j(I_j−Imean)e^(−2πi160j/N)`。相位因时间原点而变；没有外部磁场相位同步就只能做诊断。
3. **历史已有但最终配置尚未核实：** 约200 Hz交变磁场、相机14 μm传感器像元、标称50×物镜、样品标称约100 nm Fe₃O₄。它们不是已知的驱动矢量场或真实物方nm/px；若无中继倍率，14 μm / 50× 才给条件性280 nm/px。不可把演示65 nm/px、NA1.3、5/20 nm横移、zf450/550nm、Querry文献光学常数当作实验实测参数。
4. **演示空间合同：** 冻结 `q=5`、全物理图65×65、物理相机ROI为全图13:53（41×41）、精细网格61:265（205×205），真ROI中心(21,21)、全图中心(33,33)。HDF5二维空间轴是MATLAB **列、行**，非对称像元已由v084证据验证。演示ROI阈值来自其**自身**的时均强度；不能拿实验全幅掩码阈值强塞给演示模型。
5. 继续保持：`calibration_valid=false`、`experimental_validation=false`、`detection_validated=false`、`single_particle_diameter=NOT_ESTIMATED`。不得宣称400 Hz磁因果、真实粒径Bias/RMSE、检出率、真实仪器噪声、连续尺寸域可辨识性或全域唯一性。

---

## 1. 对v087固定提交的严格验收裁决（不是v088新运行结果）

### 1.1 已有来源支持并应原样保留

| 项目 | 已核对的真实发布证据 | 裁决 |
|---|---|---|
| 已缓存实验41×41×2001帧 `roiFrames` | v087确实对保存的单精度帧重新执行了双精度频谱求和，存储文件 SHA-256 `49c10f1b24c6798f745dd8b7f1409b0472912761ac639b71566f9c1e800582be`；原站与仓库副本字节一致 | **KEEP_NUMERIC**，无需读取BMP、无需新的光学仿真 |
| 12个预注册像元显式DFT | `v087_cached_frames_fft_probes12.csv` 12/12在原门 `rel<1e-5 OR |ΔX|<1e-7` 内，NumPy FFT与显式DFT另有接近双精度舍入的差 | **KEEP**；不代表真实成像光学或磁因果检验 |
| 全1681像元 | `v087_cached_frames_fft_operator_audit.csv` 1681×16列均可解析；独立从表值再算同一`OR`门 **1681/1681符合**：最大|ΔX|=**1.0567185548122951e−7**，中位|ΔX|≈**1.41133e−8**，最大|ΔC|≈**2.35122e−7**，最大|ΔImean|≈**8.54143e−7**。有4像元 |ΔX|≥1e−7、1个相对误差≥1e−5，但每例至少满足另一个门 | **KEEP**，不能把门改成两项均必须满足，也不能说所有像元绝对差均<1e−7 |
| 轴顺序和缓存一致性 | 两个非对称探针正确方向误差约2.52e−8，对错误转置约6.9785e−2；小ROI的复C400与旧完整图的对应裁剪在**已有保存数组**上最大差为0 | **KEEP**，这是**数据对象身份**，不是又一次独立采集 |
| 排名实际观察 | 192跨D候选，单/双精度均选择 `D30_zf550_M400_a20__vs__D60_zf450_M400_a20`（0.1332647253 / 0.1332643426） | **OBSERVED_SAME**；v086旧argmin代理已改为真实排序 |
| 排名保守认证 | 最近区间 `[0.133234360672,0.133294324624]`、次近区间`[0.133244335610,0.133462211615]`相交，原条件性三角界不能证明排名锁定 | **RANK_NOT_CERTIFIED**；区间不是实验置信区间 |
| 24张双精度模拟复图及276对 | v085/v086数组SHA+读回+数值对照已完成；v087没有新增BEM/renders/图 | 原数据继续**只读保留** |

### 1.2 新发现的三个确定性问题，必须独立修复

**X1：频率坐标统一出现一个bin的偏移，而复数频谱数值本身基本正确。**

`source/run_v087_C_cached_experimental_fft.py` 在循环 `kb in NEIGHBOUR_BINS_0BASED` 中，正确设置了 `kM=kb+1` 作为MATLAB索引，但计算频率时错误写成：

```python
freq = kM * 5000.0 / 2001.0            # v087 WRONG: kM是1基索引
# Correct (zero-based physical DFT frequency):
freq = kb * 5000.0 / 2001.0           # = (kM-1)*Fs/N
```

从发布的8行邻频表逐项检查，其 `actualFreq_Hz` 都比正确值高了 **`5000/2001 = 2.498750624687656 Hz`**（仅有6位小数舍入差）。例如：

- MATLAB bin 161 / k0=160 应为 **399.800099950025 Hz**，v087却写 **402.298851 Hz**；
- MATLAB bin 169 / k0=168 应为 **419.790104947526 Hz**，v087却写 **422.288856 Hz**；
- MATLAB bin 158 / k0=157 应为 **392.303848075962 Hz**，v087却写 **394.802599 Hz**。

这8行 `roi_mean_absX_recomputed` 与历史v073频谱记录在数值上吻合，例如MATLAB bin161均值约0.162566844、6个固定相邻非中心bin的均值约0.128472780（只是描述性比值约1.265，**非SNR、非显著性、非磁驱动证明**）。因而**本项仅更正元数据，禁止为了改频率标签又重做已正确保存的实验FFT**。保留原表只读并输出新`v088_spectral_bins_corrected.csv`。

**X2：排名决策JSON的结论句与两个已列出的argmin事实矛盾。**

`tables/v087_ranking_decision.json` 明列 `argmin_single_pair == argmin_double_pair`，`observed_rank_same_between_two_paths=YES`，但 `interpretation` 文本却称两路径选了 **DIFFERENT** 最近对。修正该字段及全套来源注释；保持 `triangle_interval_certified=NO`。另外 `FIX2_endpoint_touch` 用`d1=.10,b1=.01,d2=.11,b2=.01`，实际 `hi1=.11`、`lo2=.10`，**不是端点相触**；测试将`NO`结果直接写入CSV，而不是执行真正认证函数。因此不能声称该旧夹具已覆盖严格相触边界。下一轮以精确十进制/分数构造 `hi1==lo2` 并**实际调用**同一严格函数；另外交换argmin及间隔分离夹具也必须执行函数，而不是手写结果。无需重跑276个物理状态。

**X3：实验全图掩码规则与演示ROI的掩码上下文被混用，且守卫尚未真正嵌入地图加载正例。**

v087新增的 `check_mask_rule(Imean,mask,floor)` 可以检测人为注入的阈值错误，但 `load_double_map` → `validate_map_metadata` 的真实调用路径**并未调用它**；v087的LIVE-POS01磁盘地图甚至不需要传入`mean_floor`，因而不能据此宣布“掩码规则已由生产地图加载强制执行”。同时 `run_v087_B_guard_and_mask.py` 将**实验全图**取出的阈值 `0.00011761607311200351` 用在**演示模拟**的Imean_map上，二者来源不一致，即使刚好都是1681有效像元也不等于物理/算法语义正确。

修复要求：

- `EXPERIMENT_FULL_FRAME_SOURCE`：从旧v073完整图 `Imean` 的**正且有限值**计算或核对 `floor=0.01*median(positive_full_Imean)`，实验小ROI继承全图阈值，不允许使用小ROI自己的中位数；旧无效像元仍复数NaN；
- `DEMO_ROI_LOCAL`：冻结`extract_fft_v073`对演示41×41模拟图的自身时均强度规则（若旧实现采用ROI中位数，必须真实代码逐条核实）；不允许传入实验阈值；
- 数据源/掩码作用域作为有版本、SHA、契约的**外置元数据**传入生产入口，不必也不得重写旧MAT导致原SHA改变；未明确作用域或传错阈值时拒绝；保留v085/v086历史真通过的数值图与旧门槛。必须用坏掩码+真实磁盘文件或在真实生产入口的对象复本中注入错误，正例和负例都经过同一函数。q/fine-slice仍需额外版本源码证明，不能仅由未存入旧MAT的字段“自动证实”。

---

## 2. v088阶段安排、依赖与真正的计算预算

### A：来源SHA与数值发现冻结（纯只读，零新物理）

- 冻结v087 SHA、`numeric/fft400_corrected_small_roi.mat`字节SHA-256、`tables/v087_cached_frames_fft_operator_audit.csv`、`tables/v087_spectral_neighbors_fixed.csv`、历史`tables/fft_spectral_neighborhood.csv`、v085/v086的24图/276对数值表与算法版本。
- 从**实际发布CSV**重新核算1681像元全部OR门、绝对差的p50/p90/p99/max及4/1两个边界计数；除这些已有来源外不能杜撰噪声模型、颗粒类别、标准粒径或现场MATLAB验证结果。
- 旧独立DFT的12像元验证继续只读继承，不为制造新报告再读原始BMP。sourceSHA缺失或改变只停止依赖的实验支线。

### B：频谱坐标和排名元数据严谨纠错（零FFT、零复图生成）

- 使用包内`tools/v088_spectral_index_correction.py`对8个频谱标签**仅重新计算对应频率**并与v073历史表同bin匹配；必须输出正确的`k_matlab, k0, actualFreq_Hz, roi_mean_absX`，保留v087原表与源SHA。正确频率门可取纯数学精度`|f−k0*5000/2001|<1e−10 Hz`（注意CSV输出有效数字）。
- 使用包内`tools/v088_ranking_decision_audit.py`对v086冻结276行重新计算192跨D的两个真实argmin；用**实际执行的功能调用**验证：F1最近候选交换、F2严格端点相触、F3真正分离、F4重叠。F2可用`Decimal`或`Fraction`实现完全相等，不能再写`.11==.10`。
- 新JSON中`interpretation`必须由真实布尔结果模板化生成：`OBSERVED_SAME=YES`但`RANK_CERTIFIED=NO`；如实际结果发生变化，不得按期望答案写死。不要将区间称为置信区间。
- 修复上述元数据**不消耗新时域FFT**、不新增BEM、render或任何case；结果表独立读回、唯一键、正确SHA。

### C：两种掩码上下文与生产调用链（最多8项轻量软件夹具）

- 通过真实旧源码确认`DEMO_ROI_LOCAL`和`EXPERIMENT_FULL_FRAME_SOURCE`各自适用的`meanFloor`运算区域、非有限值处理、`>floor`严格比较、有效掩码、存储的复数NaN约定。选择同源对象，不得把模拟Imean与实验全幅的阈值放在一张数值验收表里比较。
- 对实验全图 `fft400_corrected_full.mat` 的真实字段名 `Imean`、`meanFloor` 做只读验证（源适配使用`Xk/C_k`,不是`X400/C400`）。核对计算得到的全幅median floor与存储阈值，在单精度舍入范围内记录绝对/相对差；小ROI继承该floor及对应空间mask。禁用以局部中位数重算然后覆写旧ROI。
- 修改**同一生产入口**的掩码作用域参数和实际调用路径，正例必须通过，阈值作用域串用、合法正值低于floor却被错误纳入、掩码声称无效但值高于floor、Imean NaN、SHA不符等坏例需由相应GuardError拒绝（缺陷类型要与注入相符）。不要编写`raise ValueError('bad')`充当守卫，不能仅调用不与生产入口连接的辅助方法。
- 旧代码可以作为历史保留；新工作流在真正要使用图像阵列前执行新验证器。成功仅为软件掩码合同验证，**不能代替真实实验光路/噪声校准**。

### D：有界的实验缓存分段/谱诊断（本轮唯一新的缓存视频时域分析）

**前置：** A、B的真实来源/频率已经通过；实验缓存SHA仍与v087固定原件一致，掩码作用域由C锁定。否则此阶段标`BLOCKED_DEPENDENCY`而不得合成假视频。

- **唯一输入**：既有`fft400_corrected_small_roi.mat`的`roiFrames`，HDF5形状`(2001,1,41,41)`、原单精度采样、实验全图meanFloor和validMask。只允许**读缓存一遍**（内存后处理可复用），**不重读任何BMP、不新增物理采样**。
- 预注册两个不重叠窗口：原2001样本的`j=0..999`和`j=1000..2000`，即`N_1=1000,N_2=1001`。不可看到结果后重新划分最佳窗口、平移中心或筛选有利ROI。
- 预注册三个次要诊断频率：`f∈{200,400,420} Hz`。对**每个窗口**使用相同全局时间原点的连续频率复解调：

  `C_f^(w)(p)=2/[N_w * Imean_w(p)] · Σ_{j∈window}(I_j(p)−Imean_w(p))exp(−2πi f j/Fs)`。

  必须以原始全局`j`而非每窗重置时钟；需要明确输出端点、N_w、源SHA、复杂Re/Im或能读回的复图、均值/有效掩码。
- **严格区分算子！** 上述分段精确200/400/420 Hz解调是**SECONDARY_WITHIN_RECORD_DIAGNOSTIC**；它不是主合同`N=2001, k0=160, f_bin=399.800099950025 Hz`的FFT估计。段长不同、频率网格不同，禁止直接把次级分段幅度当作主频数据替换或造出“实验位移”等参数。
- 每个f两段的输出：固定1681像元公共mask及变化像元数、ROI中位`|C_f|`、复图L2、两窗归一化复内积的模`|<C1,C2>|/(||C1||||C2||)`（仅描述空间复图在该次记录中的一致性）、两窗复图绝对/相对变化，必要时记录局部控制f的结果。高比值/高相干不能当作磁因果或独立重复实验；420 Hz是经验对照频率，**不是已证明的无信号噪声分布**。
- 总计最多**2窗口×3频率=6张次级复解调图**，属于**一轮读取缓存后的数学后处理**，不是6条新粒径/磁运动仿真，也不是新的光学场。原7月29日全批BMP和完整图不用重读。
- 输出时保留真正零/弱信号的绝对差；不可使用`realmin`制造有意义的相对百分比；只有固定频谱邻域才能展示“400bin局部突出”等**描述性**指标，不输出p值、SNR、FPR、磁颗粒检出率或颗粒标签。
- 可以直接复用包内`tools/v088_cached_roi_segment_diagnostic.py`，需验证其SHA、实际数据路径及预注册窗口。在工作站完成并保存真正原始来源导出的6张次级图之后才允许标`COMPLETED_REAL_CACHED_DATA`。工具的合成`--selftest`与这一步完全不同。

### E：实验参数门与下一真正物理仿真建议（不启动新BEM）

目前已具备的是**演示前向+正确实验FFT提取算子的数值证明**，尚未具备真实**磁场—颗粒运动—光学复散射—相机时域积分**链的物理输入。需按证据优先级更新：

1. **最优先：** 实际相机物方`nm/px`（最好载物台/标尺实测），或真实总倍率及中继光路；物镜型号、NA、浸液、入射角、偏振和参考反射光路。保留历史50×、14µm记录，但不得推断实际65nm/px。
2. **同等优先：** 相机真实曝光、触发时序、增益、实际磁场`B(t)`幅值（mT、峰值/有效值）、方向、空间梯度、波形、与相机帧的同步关系。历史约200Hz不证明400Hz颗粒二倍频因果，5/20nm都是处方假设。
3. **真实材料/运动状态：** 颗粒是否固定或悬浮、水/玻璃/包覆层厚度、颗粒批次、磁核与水动力直径区别、TEM/SEM/DLS、材料520nm光学常数先验、颗粒实际高度和运动机制。
4. **独立标定和控制：** 空白基底/无颗粒、无磁驱动与有磁驱动对照、驱动相位参考、独立颗粒粒径标定及噪声背景数据。未获得前仅可作频谱描述，不得算实验D或置信区间。
5. 全部参数必须带`status_category`：`USER_CONFIRMED / EXPERIMENTAL_SCRIPT_RECORDED / HISTORICAL_RECORDED_UNVERIFIED_FINAL_SETUP / SIMULATION_ASSUMPTION / MISSING`。只有前置充分且用户明确批准新增计算预算后，才在**未来单独物理阶段**决定是否需要新的BEM大小/介质/焦面格点以及动力学模型；不是v088任务。

### F：P0独立安全支线

- 原冻结门槛：`direct/reflected/total`三矩阵各 **`<1e−10`**；历史报告约`2.58848e−7`仍为`OPEN`。v084–v087未安全执行的P0被动Hook只有继承的最多1轮额度；0个MATLAB进程≠许可证/任务安全。没有安全证据则继续`NOT_RUN_RESOURCE_GATED`。
- rule7大型参考仍 **0授权**，不改旧物理 `<2%`、场插值 `<0.001`、复谐波闭合 `<1e−10` 门槛，也不把这一支线的失败套到独立FFT纯后处理。

---

## 3. v088唯一预算账本（工作站必须照此计账）

| 作业 | v088新增上限 | 备注 |
|---|---:|---|
| BEM求解 / 位置复场render | **0 / 0** | 旧场与旧数值验证一律只读 |
| 新D、zf、波长、材料、运动、τ、噪声节点 | **0** | 禁止扩大演示状态池 |
| 已完成24张双精度C400、276对配对 | **0次重新生成** | 源文件+结果只读、有限派生修复 |
| 8条邻频元数据修复 | **8条CSV纯运算** | 改频率标注、不重算已经正确的FFT复系数 |
| 排名决策修复与真实夹具 | **4个小型纯数学夹具** | 另读取旧192跨D行，不重新跑24图 |
| 掩码作用域/生产守卫 | **至多8个小型软件输入夹具** | 无重采样、无新FFT/BEM |
| 缓存实验41×41×2001视频分析 | **最多1次文件读取/段分析会话** | 2段×3频率固定次级诊断；不得重读BMP |
| 次级200/400/420 Hz复解调图 | **最多6张** | 数学后处理，必须与原主FFT估计分开 |
| 7.29原BMP重读、完整批次处理 | **0帧/0次** | v073原缓存直接使用 |
| MATLAB/P0被动Hook | **继承最多1次，安全前置充分** | rule7大型参考0次 |

历史v082 16次合成曝光、v083 2次64节点、v085 18张旧状态双精度图以及v087完整ROI FFT已完成，费用不清零、不额外重复。

## 4. 实施状态和失败处置

1. `A_source_preflight -> B_metadata_math -> C_guard_scope` 是严格前置；若只B的排名夹具失败，可保持历史24图与原实验FFT PASS，但应阻断依赖这一错误结论的排名发布；不影响只读实验视频本身。
2. D只有在正确的缓存文件SHA、时间索引、掩码作用域已证明后才能开始。只允许因导出/读取错误**重写CSV而不重新执行物理任务**；已有实验FFT数值成果不因一列频率标错而宣判无效。
3. 所有CSV必须从**真实数组或真实前驱CSV**产生，使用标准库独立读取：准确行宽、无控制符、键唯一、复数Re/Im和单位明确；逐案例写`execution_status/validation_status/evidence_status/scientific_scope/source_SHA`，不可提前计数PASS后捕获异常却依旧总报成功。
4. 允许各独立分支在其他分支阻塞时继续执行；但状态不能汇总称总实验物理PASS。历史旧表与旧脚本保留只读；新增文件均`v088_*`。已有Git blob SHA-1和真实文件SHA-256严格分开。对不在工作站的源必须标`MISSING_SOURCE / NOT_EXECUTED_DEPENDENCY`，不能通过复制发表数值伪装独立重算。
5. 这轮允许借助Python工具包，但工具自带纯数学/合成视频`--selftest`仅校验代码可用性，**不构成工作站的真实实验数据复核**。

## 5. Codex v088返回交接包规范（必须是一份真正执行结果ZIP）

```text
iscat_v088_return.zip
  00_README.md
  00_全部文本汇总_v088.md
  00_Codex_v088_执行指令.md
  status.json / review.md / manifest_sha256.csv
  source/
    v088_spectral_index_correction.py
    v088_ranking_decision_audit.py
    v088_mask_scope_and_prod_guard.py  # Codex须把守卫真正接入生产入口
    v088_cached_roi_segment_diagnostic.py
    ...实际执行的源文件、版本、SHA及入口...
  tables/
    v088_source_identity_preflight.csv
    v088_spectral_bins_corrected.csv              # 8条，修复k0→Hz
    v088_rank_fixtures_validated.csv              # 4条，执行真实逻辑
    v088_rank_decision_corrected.json
    v088_mask_scope_source_contract.csv
    v088_mask_prod_live_tests.csv
    v088_experimental_full_floor_identity.csv
    v088_cached_segment_spectra6.csv             # 仅D执行成功才有
    v088_cached_segment_summary3.csv             # 仅D执行成功才有
    v088_budget_ledger.csv / v088_parameter_readiness.csv / v088_p0_status.csv
  numeric/
    v088_cached_segment_maps.npz                  # 2x3次级复图，条件成功才有
  logs/
    actual_commands_versions_source_sha256.txt
    independent_csv_npz_readback.log
    failures_and_skipped_dependencies.log
    ...不覆盖历史v087的真实数值证据...
  history/
    v087_wrong_freq_and_fixture_evidence_index.md
```

必须明确所有源文件是否`WORKSTATION_ONLY`，若是则给出实际路径、size、SHA-256及可追踪访问方式；ZIP及GitHub发布内容需一致。所有新计算量属于既有数据处理；不输出未完成步骤的空表假PASS。

## 6. 固定v087的关键证据与Git blob索引（仅作仓库源码身份）

| 证据 | GitHub固定路径 | Git blob SHA-1 | 验收用途 |
|---|---|---|---|
| 锁定状态 | `status.json` | `bc2e4ddfdc9ceb32ee4a78f8bbf411d892955d0e` | v087整体结论，不可超越原CSV |
| 独立FFT代码 | `source/run_v087_C_cached_experimental_fft.py` | `1ab699e289e846d381cea9b2642b91c4b97ba798` | HDF5视频FFT正确、邻频标注错误 |
| 已发布邻频8行 | `tables/v087_spectral_neighbors_fixed.csv` | `a72e9557c678346adce5a0dcf96441f2ca8739f3` | 每行频率错误高1个bin |
| v073历史正确频率 | `tables/fft_spectral_neighborhood.csv` | `1cf07c9f2942b2d63d383ca093a2c7ca625c` | 同一固定bin均值复核 |
| 排名源码 | `source/run_v087_A_rank_and_interval.py` | `9badc7eb8cfd555828c1bf22571e60f9362a01a9` | 真实argmin正确，夹具未真正执行 |
| 排名JSON | `tables/v087_ranking_decision.json` | `069be56f2117d88f27a7c3b169f405942ce46ee5` | 同一JSON内部SAME与DIFFERENT冲突 |
| 排名夹具 | `tables/v087_rank_logic_fixtures.csv` | `6fe34a4b140ea8652a1b44d01c77d557feb9126b` | F2未构造相触，3条结果写死 |
| 新掩码守卫 | `source/v086_identity_guard.py` | `a8f4acb81c20fb1dcf90cae6a0ae0fb35fba0dbd` | check_mask_rule存在但未进入load入口 |
| v087掩码夹具 | `source/run_v087_B_guard_and_mask.py` | `6ced0637e9f7cfe3a8de946ce620ea0b387a61a5` | 实验阈值与演示MAP的作用域串用 |
| 1681像元FFT审计 | `tables/v087_cached_frames_fft_operator_audit.csv` | `860667cb5a70cda991c8f2af344b9a34830b6575` | 已有从真实帧独立重算；全部历史OR门通过 |
| 小ROI来源视频 | `numeric/fft400_corrected_small_roi.mat` | 固定文件树读取其真实blob（不得混作SHA256） | 原ROI缓存的真实SHA256见A节 |
| v073提取算子 | `source/extract_fft_v073.m` | `d0d165d2a739f27c226184fe054f1a7932d402a1` | 区分源阈值和N/Fs/bin定义 |
| 实验复图裁剪审计 | `tables/v087_full_small_crop_identity.csv` | `4f499b8095787bc6a26a5bd17046c67da1cffc67` | 旧全幅和小ROI复C400裁剪差值0 |

## 最终唯一执行口令（Codex）

> 从固定 `v087@900417f2cdcdec45097ea1f8c766f58d9548ac0f` 和实际缓存连续执行v088。**首先修正**8条邻频频率标签：以`k0=(k_matlab−1)`计算`f=k0*Fs/N`，不要重跑已经有效的FFT；同时修正v087排名JSON的SAME/DIFFERENT矛盾和未真正相触的FIX2，强制数学夹具实际执行函数。**其次**使实验全图掩码与演示ROI掩码按各自来源契约在真实生产入口被验证，禁止把实验meanFloor施加到演示Imean。**最后**如缓存SHA及作用域前置通过，最多只读一次原已保存41×41×2001实验视频，以冻结的[0:1000]/[1000:2001]两段和精确200/400/420Hz次要解调生成六张限界诊断图，明确它与主399.8001Hz FFT算子不是同一估计量。禁止新BEM、render、物理条件、BMP重读、真实D拟合或磁场因果结论。所有已通过的24图和276对仅只读继承。按约定完整记录成本、异常和来源，最终交付**真正的**`iscat_v088_return.zip`与GitHub可读固定v088分支，不必逐步等待GPT批准。 
