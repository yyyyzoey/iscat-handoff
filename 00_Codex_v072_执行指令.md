# iSCAT v072 唯一连续执行指令：v071审查收口、受控结果证据与实验FFT桥接

> 执行者：Codex（持有工作站MATLAB、实际文件与日志）；审查决策：ChatGPT。
>
> **唯一审查对象**：`yyyyzoey/iscat-handoff`，`v071`固定提交 `102a042a228c1b5c9c3381153df8efc318ed32b1`，提交时间 `2026-10-12T16:41:02Z`。运行时使用固定SHA，不在运行中把移动分支HEAD冒充同一次结果。另开v072结果分支，发布前校验本轮新提交。
>
> 本文件为**接下来要执行的方案与验收合同**，绝非已经执行的MATLAB/BEM/实验结果。用户最终目标是**真实反射式iSCAT装置上磁纳米颗粒的测量观测量—粒径映射**。金球为历史软件基准；Fe₃O₄ Querry 1985的光学数据与520 nm/65 nm演示装置属于`LITERATURE_MATERIAL_EXPLORATION`，不等于用户实际样品的光学性质、仪器或实验标定。

## 0. 必须先采用的v071审查裁决

### 0.1 成果接受与不能越级的边界

| 项目 | 本轮读取的证据 | 审查裁决 |
|---|---|---|
| v070先前24份数组 | v071盘点v070目录仅有日志与CSV，无可复用MAT、原持久工作区已失 | v070表保留历史诊断，不是原数组可复核证据；不因数值看起来合理而标完整 |
| v071有效侧渲染 | 6条件×`P_base/F_base/F_q7/F_bessel` = **24份侧结果**；另1次角度dead-switch探针；v071已保存`numeric/side_*.mat`清单、SHA-256、部分MAT示例 | 执行证据显著改善；24份包含**12份原基线＋12份可执行的批准数值对照**，并非原定24项四配置全部完成 |
| 原批准的控制量 | `P_common`、`F_angle`各6份=12侧`NOT_EXECUTABLE`。`P_common`须已有576解在100/151重新求far；`F_angle`须已有1444解在200/301重新求far；保存的`s`含冻结角度far/lens，没有BEM边界求解对象`sol` | 维持`NOT_EXECUTABLE`；不插值伪造，不把死开关下的0误差称数值收敛；本轮**不允许重做BEM** |
| 36个比较槽位 | 18行`COMPLETED`、18行`NOT_EXECUTABLE`；三种已完成比较各6条件；两份比较CSV在独立MATLAB会话字节一致 | 接受表格结构、标量算术与跨会话重聚合，不能叫全部36项物理闭合或独立的第二套物理求解 |
| 数值效应 | `F_q7`相对`F_base`非零；`F_bessel8001`相对`F_base4001`非零；`P_base/F_base`差仍非零 | 仅接受**指定有限配置的增量证据**，不得说差异100%由网格引起、Bessel已经证明二阶收敛，或所有后处理因素无影响 |
| 实验提取器 | 工作站旧`test.m`（GBK）由执行者报告已找到，设置420 Hz，原始BMP及既有FFT MAT输出未找到；**同项目另有先前附件`test_with_contrast.m`设置400 Hz并定义归一化复调制对比度** | 版本/观测量合同发生实质分叉：保留两套原始事实与来源；不静默采用420、不把旧灰度FFT幅值当作归一化iSCAT对比度。没有原始BMP不能声称实验回放通过 |
| 材料合同 | 新合同改正Querry年份1985、520 nm `2.349+0.083i`；根旧合同保留 | 文本更正有效，**真实SHA-256字段仍是文字占位**，时间约定`exp(+iωt)`及耗散符号需要引用实际源码/解析约定；不得签材料身份全面闭合 |
| P0/R6 | Hook、blocked/unblocked三矩阵和R6边界诊断无新完成证据 | 按真实OPEN接续，不能通过频域仿真或金球旧结论替代原门槛 |

### 0.2 本次审查的实际算术核对（GitHub源表，不是原MAT独立物理核验）

- `controlled_plan24_v071.csv`实际**36行**，24行`COMPLETED`、12行`NOT_EXECUTABLE`；名称带“24”只指24个有效侧或计划背景，不能因此把36行误记为24行。
- `controlled_comparisons_v071.csv`实际**36行、15列**，18行完成、18行不可执行。完成组为：
  - `P_base−F_base`，六点`rF=0.00540885104726454…0.00621525910709105`；
  - `F_q7−F_base`，六点`0.000527578588885243…0.000698084727518563`；
  - `F_bessel−F_base`，六点`0.00000781381791362921…0.00000821155011163651`。
- 对18行已完成记录：`num/den`与`rF`符合未舍入浮点精度；用同条件`K_pixelL2,R×rF×eta`重新计算`|ΔS|/|S_R|`吻合。**注意：CSV名为`abs_dS`的列实际上含负数，源码写入的是带符号的`dS=sum(d(:))`，不能把它当绝对差。**下一轮分开导出`deltaS_signed`与`deltaS_abs`，原表不覆盖。
- `controlled_side_scalars_v071.csv`的`S_area`是**未乘面积的**`sum(C(:))`，无量纲；v068的`S_area_nm2`为`(65 nm)^2×sum(C)`，有`nm²`单位；绝不直接将两表数字相比。
- 例如K05 D100/zf437.5：精细`S=-0.0086979697564`，Bessel8001`S=-0.0080585857917`，标量相对变化约**7.35096%**，而整幅41×41像元`rF≈8.1922×10^-6`。这是有符号量接近抵消时的**有限数值敏感性事实**，不表示实验粒径误差或唯一误差来源。
- 仓库`controlled_comparisons_recheck_v071.csv`与原CSV是相同Git blob/5160字节；这证明相同计算路径可由落盘数组重聚合，不证明`render_system`相对另一个独立光学前向模型正确。

### 0.3 审查时额外发现的证据/实现缺口

1. `logs/matlab_native_run.log`中先后出现至少3个`run_v071_controlled.m`入口`code_sha`：`3a5ef500…`、`a13eecd1…`、`667889a4…`；最终发布manifest中源码SHA-256为`667889a4…`。K01后续日志出现`CACHE_HIT`，但缓存key仅含case/suffix/系统文件哈希前缀/ntab/q/z/网格，不含`code_sha`或`render_system_sha`。**必须审核K01旧缓存evi源码版本与此次最终发布代码的差异**；若仅日志/shape计数修正且物理输入与渲染算法完全相同，可保留；无法证明则部分状态开放，不许仅用缓存文件存在签完全可追溯。
2. `numeric/controlled_array_manifest.csv`报告24份65×65对比度侧数组，另外19个无contrast MAT（包括12份不可执行状态、6份差图及探针）。发布仓库只含一个K01的`controlled_recovered_examples.mat`和文本清单；**除K01示例外，不能声称审查端已直接打开全部工作站MAT数组**。如需要补关键证据，从现有工作站文件归档K03/K05的41×41原数组，而非重新渲染。
3. `source/run_v071_controlled.m`当前`verify`分支读取侧MAT，按同一`computeComparisons`重建CSV；`CACHE_HIT`时只读取MAT，不在公开代码中逐项比对已有文件的实际配置/完整hash和代码版本。改进守卫与失效策略，**不能为了改代码而重跑所有24侧**。
4. `status.json`把真实30/100 nm均匀基准来源笼统写为`v065`，历史上正确均匀基准实际在`v067`的`galerkin.bemsolver`路径；`v065`同名`homog`曾对应分层构建。归档时纠正来源，不重算现有数据。
5. `experimental/material_contract_v071.json`的`sha256_file_local_copy`依然填的是`Fe3O4_Querry.yml in repo`文字，不是哈希。Git blob是`37cd83a1ad859b18ddb8c6a515c29df78b2d95cb`；SHA-256应根据实际源文件再次从字节校验，历史manifest记载`c42e5a5007827fb3548df61daf222b164a7799206790fb2116c8488aefe9e802`，不得未经核对就手填。`exp(+iωt)`与正κ吸收的全套波/远场约定仍须源码/解析核对，不改变基线求解结果来迁就合同文字。

### 0.4 此轮的关键策略

**接受有限q与Bessel的数值对照；对需要原边界解而不存在的角度任务维持NOT_EXECUTABLE，不为“凑齐”重跑BEM。下一轮以真实FFT处理链的“来源分叉→解析夹具→可行数据回放”优先，其次用缓存图像分析有限静态可识别性，P0独立安全推进。**

## 1. 不变的物理/统计与证据合同

- IDENTITY，观测行camera_x、列camera_y；不对图像逐条件选择转置、翻转，不以自由缩放、自由相位或删纯散射项降低误差。
- 反射式强度`|Eref+Esca|²`包含`|Esca|²`与`2Re(Eref* Esca)`；强度在子像元先求再面积积分，物理像元65 nm、q仅是积分采样，不改变像元大小。
- 历史金球开发相机recipe为1506电子/像元、1ms、1信号＋8参考；**绝非**5000 fps原实验配方。不能借此把实际曝光补为1ms，亦不许在旧验证中按D调光、多曝光。
- 旧均匀磁颗粒BEM/Mie四项各`<2%`，分层41×41展平像元L2 `<2%`，原金球D定位门槛、R5 CP与R6 Wilson不变，均只在原适用条件解释。P0完整direct/reflected/total相对Frobenius blocked/unblocked各`<1e-10`，原rule3/rule7增量 `<0.005`不可互换。
- 不新增BEM、不新增材料/直径/间隙/焦面/光强/相机噪声批次；不将三尺寸静态图拟合成正式粒径标定曲线；不把平面静态焦面变化当作磁激励下的颗粒运动（轴向运动会改变实际相对界面的几何及BEM问题）。
- 任何状态按三字段维护：`execution_status / validation_status / evidence_status`。`PASS_WITH_LIMITS`必须列真实限制；不能以检查脚本返回零退出码代替有证据的PASS。
- 禁止对只存`far/lens`的`s`做角度插值充作未保存的`farfields(sol,new_dir)`，或从均匀球替换分层球边界解。历史代码与失败保留，不改固定作者基线。

## 2. A：数值结果快速封存、来源守卫与状态纠错（零新增BEM）

### [放行条件]

工作站工程、v071_return/numeric目录能读取；无同时执行相同任务的活跃进程，源码/对象身份可核对。不要清理旧MATLAB进程而未确认PID、命令行与用户授权。

### [必查项]

1. **逐项按冻结完成键核对**全部24个有效侧：`case, D,zf, suffix, scene/layers, mesh, material, wavelength, axis, q, actual_lens, actual_far_dirs, ntab, system_file_sha256, render_source_sha256, wrapper_source_sha256, array_sha256`。额外检查数组shape=65×65、finite、字段`C/I0/Cs/Cint`是否可用、41×41坐标、参考强度分母。
2. **固定六条件，不得改变或按好坏挑选**：`K01=(D60,zf512.5)`、`K02=(D60,zf515)`、`K03=(D100,zf425)`、`K04=(D100,zf435)`、`K05=(D100,zf437.5)`、`K06=(D100,zf450)`（直径与焦面单位均为nm）。区分`system_file_sha256`和真正求解对象`sol`：当前`sol_sha256`字段实为保存的`s`系统MAT文件的SHA-256，不可在文档里暗示BEM `sol`已持久化。`s`已含旧远场不是任意角度方向下的完整解。
3. 针对K01多入口`code_sha`，查本地历史源文件及diff；比对`render_system_sha`是否恒定及入参/返回是否变过。如只变诊断日志、缓存身份可说明原因，允许接受旧K01数组；如无法验证则标`SOURCE_LINEAGE_INDETERMINATE`。**仅当旧缓存不能证明数值同源且确实需要重新验证时，授权最多4份K01侧render的新增一次性纠错上限**（限`P_base/F_base/F_q7/F_bessel`，不新增BEM）；其余20份不重跑。
4. 输出`controlled_ledger_reconciled.csv`，同时列原v070的未保存数组历史、v071本轮24次侧render/一次探针、本轮为纠错新增的0–4次、12个不可执行任务、其余对照18个不可执行比较。**不是把所有版本的每次CSV重新累计成独立仿真。**
5. 从已有数组**只做重聚合**：36行旧比较，不覆盖原版本；新表加`deltaS_signed`、`deltaS_abs`和`S_ref_sumC`三列；`S_area_nm2=4225×S_sumC`另列。负值的`abs_dS`不能继续冒充绝对差。对可执行的18行，分子分母、K₂/χ₁/η与逐次数组结果一致；另存比值分母为0时`REL_UNDEFINED`的规则，不用`realmin`伪造无穷/通过。
6. 将K03、K05重要的**已保存**生产/精细/控制图41×41数值与真实来源字段打入小MAT或可读CSV，供下轮复核；不可用显示归一化PNG替代真实C。
7. 附源YAML真实SHA-256、材料实例的实际n/κ/ε读回和代码/仿真时间相位约定来源。只修归档不改已通过的物理计算。保留旧v063材料合同历史。将M2_30/100来源纠为`v067`真均匀基准、M3来源为v064–v068分层，不再让`v065`的错误homog标签复活。
8. 已确认无sol且安全检索其他历史系统/归档无相同分层sol时，把P_common/F_angle的12项正式标为`NOT_EXECUTABLE_UNDER_ZERO_BEM_BUDGET`并停止重复试探；若偶然恢复**身份、材料/层结构均匹配**的原sol，先在K01单例验证输入相同，再按仍未花费的旧额度提交额外控制渲染方案；**此轮不自动重新分配物理求解**。

### [失败处置]

缓存/源码/数据不一致仅暂停受影响case，不因此推翻独立有效的均匀基准或27条件结果。无原始场而保留的表标为`EVIDENCE_PARTIAL`，不可手工重构虚假完整数组。不可执行项不再无限循环尝试。

## 3. B：区分两份真实存在的实验FFT脚本（零BEM，最高优先级）

### [研究必要性]

v071确实找到了本机原`C:\Users\PC\Desktop\课题\test.m`，SHA-256（由工作站报告）`fdc918e691b13b33cbae8b32ecaacd1e63ec27be3e23b61b0701d0e595aea684`，GBK。其静态合同报告：`Fs=5000`，`startFrame=1000,endFrame=3000`，`targetFreq=420`，逐像元时间均值移除、无窗、正频率单边幅值`2|FFT_k|/N`及相位`angle(FFT_k)`；路径指向一个BMP文件再glob文件夹，目前不能回放。

**此外本项目用户提供的另一个源文件 `test_with_contrast.m` 明确设置`targetFreq=400`且定义**：

\[
C_f(x,y)=\frac{s_k\,F_k(x,y)}{N\,I_{\mathrm{mean}}(x,y)},\qquad s_k=2\ \text{(普通正频率)},
\]

并保存`normalizedComplexContrast`、`normalizedAmplitudeContrast`、`normalizedPhaseContrast`，用`meanFloorFraction=0.01`相对正时间均值中位数建立有效背景掩码。该脚本**不在v071 GitHub发布树内**；它的存在来自本项目较早提供的附件，不能宣称Codex本机已找到、已经运行或正式替代用户当前处理程序。

这两套脚本输出**不是同一个标量**：原`test.m`的FFT灰度幅值使用`im2single`强度尺度；`test_with_contrast.m`还除以逐像元`Imean`并对低背景像元置无效。它们都不能未经光学时序正向仿真直接等同静态`(I-Iref)/Iref`。

### [放行条件]

只读取得原`test.m`（字节SHA先校验），并优先在本机/原项目已知附件路径查找`test_with_contrast.m`（无则标`SOURCE_NOT_ON_WORKSTATION`，不臆造其源SHA）。任何脚本的原版不覆盖、不重写；需要可测函数抽取时创建单独版本的只读等价包装，保存diff与原字节身份。

### [必查项]

1. 输出`experimental/extractor_versions.csv`：至少区分`test.m_420_unnormalized`与`test_with_contrast.m_400_normalized`，记录准确路径、字节SHA、文件编码、确认级别、FFT算法、背景分母、低背景掩码、频点、是否有原始BMP、是否有原输出MAT、是否是**用户确认的当前正式实验提取器**。不能从文件名/创建日期自动推断哪个是用户最后用于测径的正式观测量。
2. 从源码逐项读取真实`Fs、targetFreq、startFrame、endFrame、processMode、grayWeights、N、window、mean-subtraction、FFT轴、k-index、single-sided scaling、complex phase convention、time origin、Imean floor、ROI、spatial postprocessing、输出字段与单位`。`R2019b`注释与当前工作站R2024b应记录差别；输出图的`min-max`仅用于显示，不能作为测量复振幅。
3. **固定N=2001、Fs=5000时的数学预期必须与源码实现对账**：`Δf=5000/2001≈2.498750624687656 Hz`；目标400 Hz对应索引`k=160`（MATLAB 1-based `161`），实际频点`399.800099950025 Hz`；目标420 Hz对应`k=168`（MATLAB 1-based`169`），实际`419.790104947526 Hz`。这两个不同处理目标均应进行**解析夹具验证**，但不得将420不经用户确认改为400或将两者数据合并。
4. 从时域合成**仅用于验证处理程序**的3×3或5×5灰度像元小信号，无实际磁颗粒/轨迹/光学响应冒名：常量背景、精确bin纯余弦已知幅相、非整bin 400与420、已知双频混合、空间变化背景、时间起点改变/相位参考、背景为零和低背景掩码、RGB灰度映射、非有限输入阻断等；固定至多12组夹具，不生成大BMP或未经授权的虚拟实验颗粒。
5. MATLAB当前算法与独立的直接DTFT/DFT求和参考比较复系数、单边幅值和相位（相位在幅值可辨时wrap比较）；为单精度输入提前声明测试容差，例如`abs_tol=1e-7, rel_tol=1e-5`仅作为本轮程序夹具判据，失败保存完整数值；若真实执行涉及8-bit量化，使用量化后的输入参考而非理想实数幅度。近零参考用绝对差、phase UNDEFINED；可对每个fixture保存预期值、实算值、误差与接受状态。禁止按结果重新挑容差。
6. **特别检查有限记录与相位**：`startFrame`改变并不改变FFT幅值但可以改变phase的采样原点；实验中未提供磁场驱动参考相位时，FFT相位不能直接称绝对磁响应相位。若`N=2001`为奇数，无恰好Nyquist-bin特殊点；相关单边系数保持正确。
7. 按用户已有的400 Hz FFT结果历史与当前脚本420 Hz**报告冲突来源**：已知历史FFT文件频点399.8001 Hz，证明曾有400 Hz处理；当前旧`test.m`的420并不自动代表所有实验均为420。保存`FREQ_VERSION_CONFLICT_PENDING_USER_CONFIRM`，可并行完成两套解析夹具，只有实际数据来源核实后才指派哪套为正式观测量。
8. 若曝光未知，**不能调用金球1 ms配方**。可用明确的解析曝光积分单位测试（给定演示τ且标`ANALYTIC_FIXTURE_ONLY`）核对sinc衰减与曝光起点/中心时间戳，但不能宣称已使用真实相机曝光/磁响应；频域算法本身的程序回归可以不需要真实曝光。

### [失败处置]

没有第二脚本工作站副本时，保留其项目附件合同作为候选，不声称两代码已经逐字比较完成。没有真实帧时只标`ANALYTIC_EXTRACTOR_TEST_PASS`，而不是`EXPERIMENTAL_REPLAY_PASS`。若脚本伪缺陷涉及原变量作用域或文件路径，只允许新的包装/路径映射，不静默修改归档原件或展示PNG来推真实振幅。

## 4. C：真实数据路径盘点、一次小回放与测量单位（零BEM）

### [放行条件]

从现有项目源目录、前期用户资料和本机实际盘点数据，不执行网络抓取用户私人BMP，不向公开GitHub上传真实原始图像/轨迹/私有路径。可访问一组实际原始BMP并能核对其批次、帧排序及帧率时，方可开始一次与源码一致的实验回放；如果原BMP和旧结果都缺失，明确停止这一子阶段，不用合成图伪装。

### [必查项]

- 只读检查`C:\Users\PC\Desktop\课题\7.29\7.29\BMP100053022-20260729-105610`及另一个旧E盘路径是否存在、目录长度与BMP排序；验证样本归属、采集日期、文件数≥3000、图像dtype及帧数。已知`select2/4/5`是不同60 fps样本，不能替代7.29的5000 fps合同。
- 若实际原数据存在，最多**1组真实2001帧**，按照明确选定的源脚本做回放和元数据检查，保留一个小ROI或与原输出可比的必要数值；400和420作为版本敏感性并列时，应使用相同输入与独立输出标签，不能按拟合更好的频率选择实验真值。
- 对`im2single`/灰度幅值给出实际单位来源（原始DN归一化到像素动态范围），对`normalizedComplexContrast`明确均值分母、低背景掩码及分母对相位/幅值的作用；缺空白/背景、曝光、激光、相机总倍率、像元标定时不要输出绝对几何直径。历史标称100 nm非独立尺寸真值。
- 实验的FFT幅值可以来自真实粒子、照明起伏、振动或玻璃寄生反射；没有足够独立证据时只称“频点响应”，不把每个亮点自动当单颗粒。静态Fe₃O₄ C曲线与400Hz `|FFT|`之间**没有现成标定乘数**。
- 输出`experimental_data_inventory.csv`、`fft_replay_one_case.csv`（无数据时明确EMPTY_REASON）、`observable_validation.json`，保持`calibration_valid=false / experimental_validation=false`直到实际数据/仪器闭合。

## 5. D：缓存静态Fe₃O₄信号的可识别性诊断（零新增BEM/可零render）

### [放行条件]

复用`v068_27condition_clean.csv`、`v068_aperture_dependence.csv`以及v071六条件现有表。无需新增D或zf点，无需再render完整27条件；不使用误设单位的数据直接相连。

### [必查项]

- 以精细1444静态结果按**固定**D=[30,60,100]与zf=375:25:575（27点），输出有符号`C_center`、固定41×41 `S_area_nm2`与数值K₂；注明来源与具体n/κ、NA、65 nm像元及演示焦面。生产/参考差异单独列，不把fine当解析真解。
- 找出同一焦面下三个尺寸的有序关系、两种标量随zf过零与非单调点，检查**现有离散样本**是否出现符号重复、不同D的幅值可能交叉、以及对焦面自由度的敏感性。利用已有表做局部有限差分时声明步长及`DEVELOPMENT_DIAGNOSTIC`，不能从只有30/60/100三个D点估计连续D可识别导数或最终精度。
- 对所有差异给出`abs_err`、原ROI全图`rF`、标量正负、`K2`与`eta`，特别K03、K04、K05、K06；不把某一更稳定孔径作为后验新正式验收指标。高χ₂/条件因子描述数值敏感性，不是磁核心/流体力学直径不确定度。
- 本节结论限于`STATIC_DEMO_IDENTIFIABILITY_SCREENING`；真实FFT物理标定还需要磁驱动下的运动/构型与曝光/采样过程。**不得以扫描静态焦面代替颗粒轴向运动**（真实颗粒改变与界面的几何关系）。没有运动幅值、材料批次、照明等约束，不放行9–13节点正式磁颗粒库/3–5个直接留出/大量噪声批次。

## 6. E：P0与R6支线接续；禁止变成主线无限阻塞

- P0 Hook：只在实际CPU/内存/进程状态安全、目标`duffy1/eval2`运行路径已经确认时，按原额度**最多一次被动Hook**，保存被动日志，命中目标才称`TARGET_PATH_REACHED`。没有命中或被旧`std.get.npts`截断时写`TARGET_PATH_NOT_REACHED`，不得说“环境OOM根因已证实”。必要时停止P0分支，不影响已有身份明确的磁材料rule3结果。
- blocked/unblocked完整`direct/reflected/total`相对Frobenius各`<1e-10`仍OPEN（历史约2.58848e−7）；不以局部绝对差、0.5%参考增量、候选能跑或FFT解析测试替代。大型1444/rule7本轮**新授权0笔**，无原前置不能启动。
- 旧R6边界质量与A3四种子回放只用原合同的未用预算和真实独立数据，若前置不满足则记`BLOCKED`；不重新开展金球统计、R2–R6采集或更新旧冻结阈值。

## 7. 算力预算、运行顺序与失败边界

| 任务 | 本轮额度/上限 | 备注 |
|---|---:|---|
| **新增任何材料BEM** | **0** | 不能为角度参照而重跑旧分层求解 |
| v071有效控制数组、旧27条件 | 直接复用 | 不能因交接再跑24/27/162组 |
| K01必要的源码身份纠错补渲染 | **至多4侧** | **新增一次性、条件性**；源码变化无法核验且必需时才使用；非BEM，其他case不受益自动扩额 |
| 两套FFT解析夹具 | **总计≤12组** | 不生成大实验图、不虚构真实磁运动；本轮新开发预算 |
| 实验原数据回放 | **≤1组真实2001帧** | 有真实数据、条件与来源满足才执行；缺数据为BLOCKED，不用合成替代 |
| 静态可识别性 | **只分析已有27+6表** | 不增加D、zf、BEM、渲染 |
| P0 Hook | **≤1次被动目标探针** | 承继原有限额度，需安全及真正命中目标 |
| 新金球采集、磁材料密库、大相机噪声、rule7 | **0** | 缺物理观测定义和对应前置 |

**连续执行，不逐项停等GPT**：A/B可同时开展低资源只读核对；B解析夹具不需要真实BMP，找到原数据后自动进行C的一组有条件回放；D零计算可并行；P0只在工作站安全、与E1独立时执行。若实验原数据不存在，B仍必须完成能完成的解析夹具及双脚本差异合同，不能整轮再次只有`DATA_MISSING`。如需新的物理/材料/磁运动模型、标定观测量选择或任何BEM预算，收口返回，不擅自批准。

## 8. 返回物与发布硬检查（一个ZIP＋可读v072分支）

必须返回一个含可读状态、证据和必要数值的小ZIP；无需上传全部大BEM。至少包括：

```text
iscat_v072_return.zip
  00_README.md
  00_全部文本汇总_v072.md                # 新版本事实，不要复制v059旧汇总宣称为本轮
  00_Codex_v072_执行指令.md
  status.json / review.md / axis_contract.json / active_material_contract_v072.json
  tables/
    controlled_ledger_reconciled.csv
    controlled_comparisons_semantics_fixed.csv  # 已存原表不覆盖
    six_condition_scalar_consistency.csv
    material_identity_checks.csv
    fft_extractor_versions.csv
    fft_analytic_fixtures.csv                   # 所有12以内fixtures，单边幅值和复系数的独立DFT参考
    fft_bin_audit.csv                           # 400/420的k、actualFreq、N和源脚本身份
    experimental_data_inventory.csv
    fft_replay_one_case.csv                     # 无数据有原因，不伪造PASS
    static_identifiability_screen.csv
    p0_hook_actual_state.csv                    # 未运行亦标NOT_RUN
    compute_cost_ledger.csv
  numeric/
    K01_K03_K05_recovered_examples.mat          # 只能归档确有文件/数据，不能假生成
    analytic_fft_fixture_small.mat
    source_numeric_manifest.csv
  experimental/
    source_inventory.csv / fft_observable_contracts.json
    source_diff_and_hashes.md
  source/                                    # 真实新入口及父版diff、独立DFT参考
  logs/                                      # 原执行命令、失败/输出/验证及旧状态
  manifest_sha256.csv
```

- 所有CSV列数、条件键、有限性、零分母/相位未定义、null、重复ID、编码、单位和`execution/validation/evidence`三字段验证；**保留状态未完成行**。正确源文件SHA必须从实际字节计算；Git blob SHA1不是SHA-256，不可混用。
- 对外发布前检查路径和实验文件是否含个人账号、聊天缓存、真实实验未授权BMP，匿名化公共证据；原始真实文件保留本机，GitHub仅发布经过用户许可的文本和少量非敏感数组。
- 一份 `README` 报告本轮**实际**BEM数、新增fixture数、回放案例数、K01重计算数、P0调用数以及每分支为何停；缺工作站数据不得说已完成实验测径。`M1 corrected text but hash/sign still partial`、`M2/M3 exploratory numerics`、`experiment_targetfreq_400_vs_420 unresolved`如实保留。
- 再次从已提交的新固定SHA读取至少`status/review/fft_bin_audit/fft_analytic_fixtures/controlled_ledger`，核对内容/哈希，不以git push退出码替代发布验证。

## 9. 源码及结果证据索引

固定GitHub提交：`https://github.com/yyyyzoey/iscat-handoff/tree/102a042a228c1b5c9c3381153df8efc318ed32b1`。

| 来源路径 | Git blob SHA1 | 可核查的范围 |
|---|---|---|
| `status.json` | `313923181143366ac20a872d05717637eafe9a48` | v071结果、12不可执行、实验脚本存在/原帧缺失、P0开放 |
| `review.md` | `51deb13053367bf31c3a209fe53447260f09601f` | 执行者观点、源阵列盘点和限制 |
| `source/run_v071_controlled.m` | `078547f1643b335ff97685ba0acd077b025b4d5f` | 实际MATLAB后处理、缓存键、数组保存和重聚合实现 |
| `tables/controlled_plan24_v071.csv` | `a7ee4efc83c7b857df65ba1564155abd5e1b8883` | 36行：24完成/12不可执行 |
| `tables/controlled_comparisons_v071.csv` | `08b85067a0a70a0d62cc68cf326a82a81bc146d6` | 36行：18完成/18不可执行，实测比值与η |
| `tables/controlled_side_scalars_v071.csv` | `bc3d3e42e6264c309b0fa9e54930329e6628312a` | 24行、41×41的无量纲∑C，χ₁与两侧K₂ |
| `logs/matlab_native_run.log` | `53d89000c358429fbf1d1696cc41924bf36abd0f` | 多源码哈希阶段、真实执行入口/旧缓存 |
| `logs/checkpoint_roundtrip.log` | `e2c759232ffc288c3480774bb43b9640e422dbcb` | 独立会话重聚合相同CSV，不是独立BEM |
| `numeric/controlled_array_manifest.csv` | `4b3def6d6b129d92944bfda98f70ae3cce267cf6` | 24个含contrast的侧数组SHA/shape，审查端没有全部原数组 |
| `experimental/experimental_observable_contract.json` | `5d580434501c4033578782530ead08dabf1928d4` | 执行者对旧test.m/420Hz的源码解释，原BMP缺失 |
| `experimental/material_contract_v071.json` | `7088f1e684e250a7cd3d9ece4c323707851b8b21` | 1985和`2.349+0.083i`的文本更正，其它身份仍待核对 |

**项目另有早期附件**`test.m`（内容中420 Hz）与`test_with_contrast.m`（内容中400 Hz、归一化复调制对比度），它们并不位于上述v071 GitHub树内；本轮审查还读取了两个上传文件的对应源代码段。下一轮必须把这些**观测量版本差异**作为首要研究事实处理，而不是只按v071 inventory称“只有420 Hz无归一化FFT”。

---

## 给Codex的单句启动指令

> **请完整执行本v072唯一指令，从v071真实断点连续接续。保留有效24侧数值、不为补P_common/F_angle而重做BEM；先封存源码与缓存身份、订正单位及有符号差字段，然后优先建立400/420 Hz两种实际脚本观测合同及≤12组解析FFT夹具。有真实原BMP且来源一致时再回放一组；无数据则明确BLOCKED，不冒称实验验证。并行整理既有静态可识别性和安全P0状态。所有门槛、预算、身份与实际结果如实保存，不必每步停等GPT，最后统一交回一个ZIP与可读v072分支。**
