# iSCAT v064：v063审查裁决、材料输入纠错与磁颗粒数值验证

**用途：本轮交给Codex的唯一执行指令。**

审查对象：`yyyyzoey/iscat-handoff` 的 `v063`，固定提交 `8fef372048c362aee1431e9fa27b1ac630a35526`。本文件是下一轮决策，不是新BEM执行结果。研究对象仍为磁纳米颗粒；金球仅为软件和方法验证。

## 0. 决策与执行方式

### 0.1 必须先执行的裁决

v063的60 nm结果**不能作为Fe3O4吸收球的数值验证通过**。源码实际是：

```matlab
nC = 2.349 + 0.0831;
mp = Material(nC^2, 1);
```

它给出实数 `2.4321`。返回CSV的 `n_complex=2.4321` 与源码吻合，原 `passed=0`。因此，首先发生的是**运行材料不符合合同**，不是已证实的“Mie不支持吸收”。[S03,S04]

固定上游 `Mie/@miesolver/absorption.m` 的实际实现为 `extinction(obj,k0)-scattering(obj,k0)`；不能把错误输入下的零吸收用于证明工具缺陷。[E02]

立即保留旧结果并标记：

```text
execution_status = COMPLETED
validation_status = FAIL
failure_code = MATERIAL_INPUT_CONTRACT_MISMATCH
scope = REAL_INDEX_2_4321_DIAGNOSTIC_ONLY
eligible_as_Fe3O4_absorbing_baseline = false
```

不要删除历史结果、覆盖为PASS，也不要将BEM/Mie复场相近解释为材料输入正确。两种算法可以共同计算同一个错误材料。

### 0.2 连续执行与优先级

完整阅读后，前置通过、输入齐全且在预算内，就连续完成可完成的任务；**不必每一步停止等待GPT**。失败只暂停依赖该失败的分支，保存证据，继续无依赖工作。最后统一返回一个ZIP及可读文本。

本轮顺序：

1. 轻量隔离错误材料结果、核对运行身份，不重建旧金球模型。
2. **优先完成材料输入守卫、无BEM的Mie测试与修正后的60 nm均匀基准。**
3. 60 nm均匀基准通过后，直接做60 nm分层生产/精细对照；随后按门槛完成30/100 nm。不要因为真实实验提取器尚未找到而阻塞明确标注的文献材料前向探索。
4. 无高内存冲突时完成解析提取器缺项、已有记录的发布补证、续跑薄封装测试。
5. 完成已授权且未完成的边界诊断及P0相对度量/贡献审计；rule7大参考最后且专属门槛齐全才放行。

不要再次用“询问GPT是否跳过吸收门槛”结束本轮；本文件已给出明确处置：**不跳过，先修输入，保持原门槛。**

### 0.3 继续冻结

- IDENTITY坐标不变，不用逐例转置、翻转、幅相最佳对齐或任意缩放。
- 金球1506 e配方、原始观测、阈值、搜索域与拟合核心保持原版本；禁多曝光、禁按粒径调光。
- 不重跑R2–R4、R5/R6批次或v063的B01–B10无噪声拟合，不新增金球统计样本。
- blocked/unblocked完整三矩阵Frobenius `<1e-10` 仍独立开放；不以0.5%或局部绝对差替代。
- 磁材料结果继续标记 `LITERATURE_MATERIAL_EXPLORATION`；真实样品、光路和提取器未匹配，不能称实验标定或绝对粒径验证。
- 同时最多一项高内存BEM/完整矩阵任务；只核对当前进程身份，不按旧PID盲杀，不改活跃生产基线。

## 1. 本轮审查证据与结论边界

### 1.1 接受并保留

**B1十个新条件。** 从完整11行CSV复算：固定真参数相对误差为 `0.00686300465009608` 至 `0.0120163666986479`；D误差 `+0.0873480727851614` 至 `+0.160724988959984 nm`；最大二维位置误差约 `0.000448046861743486 px`。十行数值均满足原2%、2 nm、0.5 px门槛。分子/分母与误差列一致。两个导出文件具有同一Git blob，属于同一组十例，不能计作二十例。[S05,S06]

**R6分组摘要订正。** B01现为81个内部标签与19个边界标签，B04为96与4；摘要中的分组均值和平方误差和可重新合并为全体值。保留这些订正，不重做采集。[S07]

| 条件/集合 | n | Bias/nm | RMSE/nm |
|---|---:|---:|---:|
| B01全合法返回 | 100 | 0.12088992490066712 | 0.29749346678487576 |
| B01 marked_reportable/interior | 81 | 0.07930015745590542 | 0.2869660816868498 |
| B01 boundary | 19 | 0.29819367032307226 | 0.3387223814985857 |
| B04全合法返回 | 100 | 0.10412247589953438 | 0.15652127737089064 |
| B04 marked_reportable/interior | 96 | 0.10746342720151181 | 0.1588352294295988 |
| B04 boundary | 4 | 0.023939644652076097 | 0.08358010621256166 |

上述仅是已导出摘要的算术核对，**不代表GPT重新读取工作站1000份原始数组**。`marked_reportable`仍是已有标记形成的描述集合，不是事后建立的冻结质量检测协议。保留原阈值越界统计与质量规则未预注册的限制。

### 1.2 磁材料必须退回输入验收

工作点数据可由外部源文件核对为：`0.5200 μm, n=2.349, κ=0.083`。该数据文件将文献标为Querry **1985**，而当前合同写1987；520 nm是实际表格节点，不需要额外插值。[S02,E01]

当前合同还同时出现 `κ=0.083`、字符串 `2.349+0.0831i`，而程序实际为 `2.4321+0i`。三者不一致，必须由一个经校验的数值入口统一，不能只修改文字。

在非磁光学近似 `μr=1` 下，正确工作点应满足：

```text
n_particle = 2.349 + 0.083i
ε_particle = n_particle² = 5.510912 + 0.389934i
```

旧实际输入对应：

```text
n_particle = 2.4321 + 0i
ε_particle = 5.91511041 + 0i
```

**吸收“相对误差”1.98701673670712e305的直接来源**是程序用 `max(abs(Mie_abs),realmin)` 作分母。返回 `Mie_abs=0` 时，它把 `BEM_abs=0.0044212589972633` 除以浮点最小正规数。这不是物理吸收相差305个数量级的证据。[S03,S04]

对于无吸收控制例，零参考量的相对误差应为未定义，不用`realmin`或epsilon填出巨大数再作物理诊断；另用预先声明的绝对/非零尺度指标。对于正确吸收材料，应先得到可分辨的非零参考吸收，再按原相对门槛比较。

### 1.3 本次额外的无BEM数学交叉核对

GPT用固定上游的Mie系数及截面公式，采用SciPy球Bessel函数重新实现标量截面计算；没有运行MATLAB或BEM。条件为D=60 nm、λ0=520 nm、外介质n=1.33、μr=1。[E02–E05]

| 输入 | Csca/nm² | Cext/nm² | Cabs/nm² |
|---|---:|---:|---:|
| 旧实际实数2.4321 | 83.44100562105729 | 83.44100562105730 | 约1.42e-14（数值零） |
| 正确复数2.349+0.083i | 73.86673175413364 | 237.97510781501106 | 164.10837606087742 |
| 控制实数2.349 | 73.65733736329930 | 73.65733736329932 | 约1.42e-14（数值零） |

第一行与v063的 `Mie_sca=83.4410056210577` 相对差约 `4.94e-15`；这加强了“结果确实来自错误实数输入”的证据。lmax=6/8/12/16的检查未显示影响上述有效位数的截断差，目标材料Cext在6与8间差约7.7e-13 nm²。

这些数值是**解析实现交叉核对**，不是对修正BEM的通过证明，也不应硬编码进结果表。Codex必须从实际加载的材料和已核对的Mie程序重新得到自身的原生结果。若原生结果不符，先核对运行源码、材料、直径、单位和介质，不调数值凑表。

## 2. M1R：材料与运行身份守卫（零BEM前置）

### [放行条件]

能取得既定材料源文件或其确切归档；运行目录、固定上游与实际函数解析路径可核查。不得凭记忆补材料，不更换物相以绕开错误。

### [必查项]

1. 保存完整Querry源文件、原来源说明与许可，记录真实SHA-256、Git blob与获取来源；不再把 `sha256_file: "Fe3O4_Querry.yml in repo"` 当作哈希。当前分支目录树未包含该声称存在的YAML文件，不能把文件存在工作站或外部数据库等同已随包。[S02,S12]
2. 外部核对的blob为 `37cd83a1ad859b18ddb8c6a515c29df78b2d95cb`。优先复用本地原件并比对；如不同，记录差异，不静默换数据。
3. 520 nm转换为0.5200 μm，精确节点读取2.349/0.083；通用插值方法可保留，但本工作点登记 `exact_node=true`。文献年份按取得的源文件修正，不能保留1987作为已核实事实。
4. 数据入口用两个实数字段 `n_real`、`kappa`，执行 `complex(n_real,kappa)`。JSON/CSV分别写真实部、虚部和ε真实部/虚部，不靠字符串表示唯一运行身份。
5. 审核实际加载的 `Material`、`miesolver`、BEM驱动和包装器路径；BEM与Mie从同一**已验材料对象**取得相同光学数据。各自都在求解前导出实际readback；不能只检查共同错误的变量互相相等。
6. 时间/外向波约定必须自洽。已核对固定Mie实现的外向函数为 `j_l+i y_l`。在该外向约定下记录与之相容的 `exp(-iωt)` 约定及n+iκ的被动吸收符号。当前合同的 `exp(+iωt)` 不得未经核对沿用；若工作站包装器采用另一全套约定，需给出明确转换与测试，不允许逐例共轭择优。[E05]
7. 介质与单位：λ0=520 nm；D是直径；外介质n=1.33；`k_host=n_host*2π/λ0`；ε与μ是相对量；`μr=1`是光学模型假设，不能用静磁参数替代。

最小守卫示例（接入数据加载器，不能只作为未调用示例留在文件里）：

```matlab
% nr, kap必须来自已校验的源数据节点，而不是从旧结果抄回。
validateattributes(nr, {'double'}, {'real','scalar','finite'});
validateattributes(kap, {'double'}, {'real','scalar','finite','nonnegative'});
nParticle = complex(nr, kap);
epsParticle = nParticle.^2;  % 本探索模型mu_r = 1
assert(abs(real(nParticle)-2.349) <= 1e-12, 'MATERIAL_REAL_MISMATCH');
assert(abs(imag(nParticle)-0.083) <= 1e-12, 'MATERIAL_IMAG_MISMATCH');
assert(imag(nParticle)>0, 'ABSORBING_TARGET_BECAME_LOSSLESS');
assert(abs(real(epsParticle)-5.510912) <= 1e-12, 'EPS_REAL_MISMATCH');
assert(abs(imag(epsParticle)-0.389934) <= 1e-12, 'EPS_IMAG_MISMATCH');
% Material构造后还须经实际、已核对的访问接口readback再次验收。
```

上述1e-12是**本轮新增的常数构造/读回工程容差**，不是2%物理门槛的替换。负向夹具必须证明 `2.349+0.0831`、`complex(2.349,0)`、把nm当μm、误传半径的配置均会在BEM分配前拒绝。异常测试通过不记作物理求解。

### [失败处置]

身份或输入守卫失败立即停止材料BEM，保留读回值与错误。允许最多2轮有记录的材料加载/包装修复；不修改上游基线、不改物理数据来达到通过。实际源值与合同有冲突时输出冲突及隔离结果，不放行。

### [自动继续]

守卫通过立即进入M2P，无需向GPT逐步询问。

## 3. M2P：先在零BEM成本下验证Mie吸收与归一化

### [放行条件]

M1R通过。现有固定版Mie及其实际依赖已经定位；不是用另外一个同名函数替代。

### [必查项]

- 60 nm、520 nm、水1.33，分别运行：目标 `complex(2.349,0.083)`；控制 `complex(2.349,0)`；旧错误输入2.4321。这里只需Mie，不为两个控制例新增BEM。
- 保存Mie阶数、系数、实际材料读回、Csca/Cext/Cabs、来源与单位。先检查阶数6/8/12；必要时16只作有限截断诊断。
- 对目标材料，Csca/Cext/Cabs有限且Cabs>0；阶数8与12非零截面的相对变化≤1e-10。此项是**新增Mie数值稳定性自检**，不是BEM验收门槛。
- 对控制材料，使用 `abs(Cabs)/Cext`（Cext已证明非零）≤1e-10作为数学实现的无吸收残差自检；原始Cabs保留，不裁零。它不是BEM吸收误差要求，也不能用来放宽吸收球2%门槛。
- 固定上游吸收由消光减散射定义。检查本机是否为同一实现，记录实际代码SHA与调用结果。不得在材料尚未纠正时修改Mie算法或把abs输出强制为正。
- 可用本文附录A的独立实现或本机已有独立Mie实现核对；独立指的是不同数值实现，不是新增实验验证。无需为了这一步重新安装或更新NANOBEM。
- 能量关系若本来就是同一代码的定义式，则 `Cext=Csca+Cabs` 只算代数一致性，不算独立物理验证；不要以此替代复远场与吸收球截面对照。

### [失败处置]

目标输入正确但Mie仍出零/负吸收或明显不同值，查实际函数解析、ε/μ、相对/绝对折射率、半径/直径、外向波和源代码差分。没有正确参考时不启动目标BEM。不得改为“只看散射或复场就算全通过”。

### [自动继续]

M2P通过后直接进行纠正后的60 nm均匀BEM。

## 4. M2R：修正目标材料的均匀BEM基准

### [放行条件]

M1R与M2P全部通过，磁材料预算已登记，无并发高内存任务。

### [执行与必查项]

1. 新增纠正后的60 nm/1444/rule3/520 nm均匀水介质基准。保留原驱动已声明的普通、近邻和Duffy数值规则，不通过更换规则来掩盖材料错误。
2. 先保存输入、网格、材料readback、源码身份，再求解；求解后保存边界解、BEM/Mie复远场、方向/权重、截面原值和度量结果。不要只保存汇总T而丢失复核所需数组。
3. 复远场用原方向、极化、振幅与权重比较，不进行任意幅相最佳对齐。检查返回shape、复数dtype、角度权重、外介质归一化。
4. 对正确吸收目标，四项原门槛**全部保留**：

```text
raw_complex_relative_L2 < 0.02
abs(Csca_BEM-Csca_Mie) / abs(Csca_Mie) < 0.02
abs(Cabs_BEM-Cabs_Mie) / abs(Cabs_Mie) < 0.02
abs(Cext_BEM-Cext_Mie) / abs(Cext_Mie) < 0.02
```

分母需事先判为有限、非零且数值可分辨。不要用realmin/epsilon替代缺失参考。60 nm正确目标的Mie吸收预期不是近零量；原生结果异常时回到M2P诊断，不自动豁免。
5. 明确每个截面的独立性：保存其实现来源；由其他两项相减得到的数值不能额外冒称独立第三种测量。
6. 总状态由逐项数值与材料守卫共同决定，禁止 `passed=0` 的表在顶层自动变成 `PASS_WITH_TOOL_LIMITATION`。

### [失败处置]

输入错误隔离受影响产物；数值不收敛或截面/复场门槛失败按原失败记录返回，先进行保存数组和接口诊断，不启动更多大网格或自动放宽阈值。BEM求解一旦发生即计入预算，不能因失败清零。

### [自动继续]

60 nm通过后优先进入60 nm M3；再继续30和100 nm相应均匀基准，每尺寸仅一笔1444/rule3。某端点失败不抹去另一个已通过尺寸的结果，不扩大该失败尺寸的分层分支。

## 5. M3：三尺寸分层前向对照，不是实验标定

### [放行条件]

该尺寸的M2R完整通过；60 nm分层首例优先。若60 nm分层失败，暂停分层扩批做诊断，其他无依赖的均匀Mie/BEM工作在余额内可继续。

### [固定探索配置]

沿用原已授权演示配置而非声称实际仪器：520 nm，均匀Fe3O4候选球，玻璃1.50/水1.33，表面gap=5 nm，法向x偏振，玻璃侧收集NA=1.3，65 nm物理像元，q5，IDENTITY。改变D时颗粒中心高度为 `gap+D/2`，不要把焦面zf与粒子高度互换。

每尺寸生产576/rule3与精细1444/rule3各一笔，生产角度/Bessel与精细角度/Bessel分别继承已冻结预设（50/51、2001；100/151、4001，实际参数完整记录）。本轮不额外改变材料、壳层、间隙、波长和光强。

### [必查项]

- 构建之前，生产/精细两侧再次通过材料readback，不允许gold.dat或旧无吸收结果混入。
- 每笔已解系统复用到zf=450、550 nm、xy=0的后处理；不因两个焦面重算BEM。
- 保存参考/散射复场、完整干涉强度、纯散射项、物理像元积分与C图。主比较使用冻结中央41×41、同方向、同物理单位；相对前向门槛仍 `<0.02`。原已定义的复场门槛同样保留，不能只选更好看的图像量。
- 不对正负对比度取绝对值后代替原物理图；如需展示模值另列。
- 结果共最多6组D/z生产—精细对照；实际零/近零图范数的判定单列，不能用分母下限签PASS。
- 材料、均匀基准与分层图不能共享错误缓存：完成键至少含物相/数据哈希/n与κ/ε/λ/D/介质/高度/规则/源码，后处理另含焦面/像元/ROI。

### [研究输出与限制]

输出三尺寸、双焦面复场/有符号C及原门槛通过情况。可以登记响应是否随D变化，但**三个尺寸不构成已验证的连续标定曲线**，不拟合D³、不反演未知实验颗粒、不把静态C代入400 Hz模值。

本轮磁材料为 `OPTICAL_FORWARD_ONLY + LITERATURE_MATERIAL_EXPLORATION`。不启动新的磁颗粒噪声大批次、尺寸扫描或实验绝对标定；是否建细D库、动态模型与留出验证，依据本轮三尺寸真实返回再决策。

### [自动继续]

一个尺寸通过就继续下一个已获授权尺寸，不逐项等GPT；失败仅暂停依赖任务。

## 6. M0：解析提取器补项与真实实验合同分离

### [当前接受与缺项]

现有表有16条PASS，包含多个同频点相位、双频、背景和一个sinc数值检查。零参考项的相对误差巨大不能单独判失败，因为合同已为近零项规定绝对容差；该条绝对误差约1.46e-16，小于1e-12。[S08,S09]

但当前表**没有明确的f=400 Hz非整频点信号FFT/有限和对照行，也没有明确的曝光开始/中心时间戳相位测试行**。一个sinc常数的computed与expected相同，不足以证明曝光积分实现已经验收。当前提交亦未包含可识别的解析测试生成脚本；先取工作站实际脚本补证，不能把未提供源码写成独立已复现。[S08,S09,S12]

### [放行条件]

不依赖材料BEM通过。优先复用原16条已执行测试的源码/夹具，无需为补发布重新运行已通过项。

### [必查项与新增测试]

1. 分离 `synthetic_observable_contract` 与 `experimental_observable_contract`。65 nm、41×41、q5来自金球/演示模型，当前文件把它们列入实验known，但缺独立实测依据；移至合成合同。真实实验字段用 `MEASURED / USER_REPORTED_UNVERIFIED / DERIVED_UNVERIFIED / MISSING` 等明确来源，不用演示值填空。[S10]
2. 历史7.29记录中的5000 fps、56 nm/px仅按其既有证据等级恢复，不将56 nm/px自动升级为独立倍率标定；当前实验曝光仍未知。[C02]
3. 完成4条新增测试（同一实信号、零新BEM）：
   - `offbin_400Hz`：Fs=5000、N=2001、k=160、C0=0.2、A=0.01、phi=pi/3。FFT对照独立有限和；不能期望模值严格等于A。
   - `exposure_centered`：Δ=100 μs的时间平均，以曝光中心为时间戳，数值积分对照解析sinc及有限和。
   - `exposure_start`：同一连续信号，开始时标应含 `+πfΔ` 相位位移；与中心时标按定义比较，不修改结果择优。
   - `near_zero_metric_semantics`：期望零时 relative_error 记null/NOT_DEFINED，正式判定使用已声明绝对尺度；验证序列化和回读不会把null转0/PASS。
4. 明确区分矩形曝光平均与相机曝光物理增光：这些是已知信号的解析测试。Δ=100 μs继续标 `TEST_ASSUMPTION`，不声称真实曝光。
5. 数值程序测试继承非零相对L2≤1e-10及近零绝对1e-12尺度规则。曝光积分对照可采用两档充分精细的确定性积分检查（不重复调用同一sinc表达式充作两种实现）。
6. 实际提取器有界定位只补缺证据，不能再全盘漫无目的搜索。已有历史文件名/目录按原合同核对；可取得源文件时确认编码、帧序号、FFT定义和实际输出字段。未找到则给出目录、模式、结果的检索清单，`experimental_replay=NOT_RUN`，但不暂停M2/M3文献探索。

### [自动继续]

解析测试失败只停其依赖的动态/实验应用；静态材料前向可继续。真实脚本未找到时不要把参考实现改名成实验提取器。

## 7. 已有验收的剩余补证、边界与P0

这些工作继续完成，但不把本轮再次变成仅改摘要而没有磁材料求解。

### A：轻量一次性完成

- `status_semantics.json`在状态中被引用，但当前提交未找到该文件；`r5_rechecked_summary.csv`的CP字段在所审提交仍是空值；`task_status.csv`仍为旧阶段。先从工作站真正完成产物补齐并使现行顶层指向一致文件，历史原件保留，不覆盖掉历史。[S01,S12,S13]
- 阈值检测与质量检测分开：quality规则未预注册，不得事后用81/100等当原检测协议的结果。保留描述性分组、全体分母与阈值统计。
- A4按已有授权实现实际薄封装并提供测试，不再只有 `future fixed` 描述。ID固定为计划ID，与本次nPerCond无关；旧记录加载并加入汇总；匿名估计输入不含D真值路径；这些都用小型伪记录测试，不重跑1000次。
- A3最多4份旧seed重建仍是诊断，不是恢复原始帧、不新增独立验证样本。仅在源码/版本/seed/输入可确定时执行；输出 `DETERMINISTIC_RECONSTRUCTION_NOT_ORIGINAL`。原始帧缺失保留为缺失，不伪装补齐。

### B2：继承的边界诊断，零新BEM

不重跑已通过的B1十例。已有23个边界标签及受影响条件的非边界对照，最多32份既有观测；先核对原目标函数、退出/起点记录与边界距离。确有必要时最多4份、每份21个域内zf点进行profile（固定zf再优化D/x/y）。不得把一维slice叫profile、不得将profile叫已校准置信区间。保持原域、不换B01/B04、不扣批次偏差。

### P0：不得从旧局部绝对差继承相对PASS

当前status一处写layout PASS carried，另一处写相对范数INDETERMINATE。正式口径沿用后者，保留局部运行与绝对差成果，不升级。[S01]

1. 优先读保存数组补SL/DL各自的绝对差、完整差范数、参考范数及相对Frobenius；局部相对门槛继承≤1e-10。只有CSV时按旧余额有限补9个候选小例和必要的6个有效baseline，不反复触发Npair=1原失败。
2. blocked/unblocked完整direct/reflected/total三矩阵仍各 `<1e-10`；先贡献/索引/权重/规则核对，不预认“纯浮点顺序”。
3. Hook必须记录实际duffy1/eval2命中次数与调用栈；未命中标TARGET_PATH_NOT_REACHED。不要用其他路径fill成功替代。
4. 原参考工具修复预算不清零；仅度量和记录包装的既有余额可使用。旧规则允许的贡献/候选小例迭代按真实消耗扣除，未知余额不是零消耗。
5. 只有局部相对回归、覆盖/资源和原完整矩阵门槛等专属前置全部满足，才自动放行原最多1笔D35.5/1444/520/rule7，并按原0.5%增量验收。否则仍OPEN，不启动。
6. P0独立OPEN不自动阻塞未受影响的磁材料rule3；若实际证明共享路径受影响，按影响范围停止，不机械坚持不阻塞。

## 8. 预算、修复与停止边界

### 8.1 本轮明确新增的预算决策

原磁材料预算9笔中，v063已消耗1笔错误材料均匀BEM，**这一笔成本保留，不能算作正确Fe3O4基准**。

本轮明确新增**1笔纠正60 nm材料输入的均匀BEM授权**，并继承原未用8笔，因此：

| 项目 | 本轮最多新增 | 授权来源 |
|---|---:|---|
| 纠正后的60 nm均匀基准 | 1 | 本轮明确新增纠错额度 |
| 30/100 nm均匀基准 | 2 | 原未用余额 |
| 三尺寸分层生产/精细 | 6 | 原未用余额，逐尺寸前置 |
| 磁材料BEM合计 | **9** | 8笔余额＋1笔明确新增 |
| P0 rule7大参考 | ≤1 | 原有条件授权；不挪用磁材料额度 |
| 新金球统计批次 | **0** | 不授权 |
| B1重跑 | **0** | 本轮已有结果接受 |

若9笔全部执行，磁材料探索累计消耗为**旧错误1笔＋本轮9笔＝10笔**。不得写成原9笔里隐含无限修复。已有符合全部身份的正确缓存扣除新计算，不按文件名盲复用。

Mie/解析/记录测试不算BEM，但也不无限迭代。材料加载与Mie包装最多2轮有记录轻量修复；BEM发生即扣预算。除上述一笔明确新增纠错外，不自动增加网格、扫描或补点；超出停止相关分支、交证据。

### 8.2 自动继续规则

- PASS且所有前置真实满足：立即下一项，无需逐步请求GPT。
- 物理门槛FAIL：保留，暂停依赖项；无关分支继续。
- 源数据/实际材料/路径身份冲突：不允许先跑后补合同。
- 出现已知材料输入错误：不是工具限制，不跳过失败指标。
- 预算用尽：不清零；完成无BEM可执行工作后统一打包。
- 不把没有原始证据的任务标COMPLETE；执行、验收、证据三个状态分开。

## 9. 返回包与发布检查

唯一ZIP建议含：

```text
iscat_v064_return.zip
  00_README.md
  00_Codex_v064_材料输入纠错与磁颗粒验证指令.md
  status.json / review.md / decisions.json
  contracts/
    material_contract_v064.json
    synthetic_observable_contract.json
    experimental_observable_contract.json
    status_semantics.json
  materials/
    Fe3O4_Querry.yml
    source_record.json
  tables/
    material_runtime_checks.csv
    mie_preflight_checks.csv
    magnetic_homogeneous_checks.csv
    magnetic_layered_checks.csv
    analytic_extractor_tests_completed.csv
    wrapper_tests.csv
    task_status_current.csv
    p0_relative_norms.csv             # 未执行则明确缺项
    p0_three_matrix_checks.csv        # 同上
  numeric/
    本轮均匀首例完整小数组/复场/方向权重/截面
    失败案例原始数值与来源
    其他大数组清单
  source/
    真正执行的材料加载、守卫、驱动、Mie/解析测试、聚合与薄封装
    相对实际父版本的diff/哈希
  logs/
    命令、运行材料readback、预算、错误、每阶段检查点
  inventory.json
  manifest_sha256.csv
```

**发布门禁：**

1. every PASS必须指向原值、门槛、来源与执行记录；总体状态由这些记录生成，不另写更乐观的散文状态。
2. material合同、运行readback、结果表三者的n/κ/ε必须一致；故意注入旧错误输入能使机器检查失败。
3. 数值0、未执行、未定义和缺失分开。禁止把null/NaN转0后签PASS；近零参考使用其专属已声明规则。
4. 确实发布所引用的YAML、解析源码、状态语义与新指令。不能只有文件名或路径文字。
5. 新manifest从最终发布字节计算，区分工作站原字节、Git blob与规范化文本。此次两个抽查CSV的manifest SHA对应CRLF，而Git内容为LF；这说明发布字节口径未区分，不能据此指控数值被改，也不能声称原manifest与Git原字节逐项吻合。[S13]
6. Git发布后核对所需小文件实际存在；历史大数组不必重复上传，但列清真实变量、dtype、轴、文件哈希与是否随包。遵守原隐私边界，不新增公开实验原数据/凭据。
7. 修正后的有效60 nm结果与旧错误材料结果必须分开路径与完成键，避免下一轮误引用。

## 10. 来源与审查边界

### 项目内来源（均固定于8fef372048c362aee1431e9fa27b1ac630a35526）

- S01：`status.json`、`review.md`，本轮执行声明与尚未完成项。
- S02：`material_contract.json`，blob `a2998d741a84216f07f76140358e8c9441b04719`。
- S03：`source/run_v063_m2_fe3o4.m`，blob `70a1abaa2b9e8dada64a6c253d19dabd2a073f0c`。
- S04：`tables/magnetic_three_size_numerical_checks.csv`，blob `dcfafe61bedcdcab790a07c6ae3f1894c32dd4dd`。
- S05：`tables/r6_new_conditions_forward.csv`及同blob的noiseless导出，blob `41c8174180c2b83e55eb25a92ce9c8507cf3f2c1`。
- S06：`source/run_v063_b1_new_conditions.m`，blob `1d62680cfd6cfbe79636cf9e0a49014f4b11c2c2`。
- S07：`tables/r6_quality_stratified_summary_fixed.csv`，blob `a1823667e88fbde95527bea73ff44986d09dd5d5`。
- S08：`tables/analytic_extractor_tests.csv`，blob `8c9d8e219f8de487e3711864949c26f26b137676`。
- S09：`analytic_fixture_contract.json`，blob `50c7becbd2669f2c776c84070391a7a45bc8e804`。
- S10：`experimental_observable_contract.json`，blob `2fe7bb45f532b8f0911cb120ceb0b70d5d275f29`。
- S11：`experimental_inputs.json`，blob `fccf5adf72c0494fbc4592f5be68d79e62e1b195`。
- S12：固定提交完整Git目录树，`truncated=false`。
- S13：`manifest_sha256.csv`，blob `37b9b4f18776f13f303efc866531567a564a0a7b`。

### 本次额外查证的外部来源（不是v063已上传执行证据）

- E01：`polyanskiy/refractiveindex.info-database`，`database/data/main/Fe3O4/nk/Querry.yml`，读取blob `37cd83a1ad859b18ddb8c6a515c29df78b2d95cb`。源文件引用Querry 1985，原表520 nm节点为2.349/0.083。只确认读到的来源和节点，不把它视为用户颗粒实测。
- E02：`uhohenester/nanobem` 固定提交 `ce49f77f096337db8be54c46d83696d37b0b23d5`，`Mie/@miesolver/absorption.m`，blob `58db03a02a8146a50d20637a792664c8cfd45b34`。
- E03：同提交 `Mie/@miesolver/scattering.m`、`extinction.m`，blob分别为 `39e105d43b1ac2503ca95328b2477662d0fbf1ad`、`7d38cb39aa04bf877020901595158f0638cd3a8a`。
- E04：同提交 `Mie/@miesolver/miecoefficients.m`，blob `698304e880f5157778594009a7eeca30427a8a09`。
- E05：同提交 `Mie/riccatibessel.m`，blob `af81ae0f80c5ae261250737160b880d1f19056ea`；外向球函数实现j+i*y。
- E06：MathWorks官方复数构造说明：`https://www.mathworks.com/help/matlab/ref/complex.html`、`https://www.mathworks.com/help/matlab/ref/i.html`。

### 已有合同

- C01：用户已提供的 `00_Codex_v063_审查决策与磁颗粒推进指令.md`。本次已读取其材料、解析夹具、B1/B2与P0/预算章节；没有把计划当作执行。
- C02：`progress(2).md`的实验数据与冻结规则章节，只作历史证据与目标，不覆盖v063新结果。

### 本次GPT实际完成与未完成

已读项目状态、源码、关键小表和完整摘要，并锁定提交；将M2完整CSV与B1完整CSV的工具文本在本地重建，Git blob均吻合后执行算术核对；对B01/B04摘要进行分组恒等式核对；执行附录A的Mie数学交叉核对。没有直接运行MATLAB/BEM，没有访问工作站全部原始数组，没有重新验证1000条观测与全部随机来源。

本文件中新守卫、Mie预检和新增一笔纠错预算为本轮决策；其余保留原门槛与尚未消耗授权。没有把文献探索改称实验标定。

## 附录A：本轮已执行的Mie标量交叉核对参考实现

这是独立数值实现的审查辅助，**不是BEM求解器，也不替代本机固定Mie的运行身份检查**。使用NumPy/SciPy；原环境没有这些库时可用既有MATLAB数值函数进行等价独立核对，不为该步骤擅自更新主工程依赖。

```python
import numpy as np
from scipy.special import spherical_jn, spherical_yn

def mie_sections(n_particle: complex, diameter_nm: float = 60.0,
                 wavelength_nm: float = 520.0, n_host: float = 1.33,
                 lmax: int = 12) -> dict[str, float]:
    """Homogeneous, nonmagnetic sphere; lossless host; cross sections in nm²."""
    if not (diameter_nm > 0 and wavelength_nm > 0 and n_host > 0 and lmax >= 1):
        raise ValueError("Positive diameter/wavelength/host index and lmax required")
    if not (np.isfinite(n_particle.real) and np.isfinite(n_particle.imag)):
        raise ValueError("Finite refractive index required")
    k0 = 2*np.pi/wavelength_nm
    k1, k2 = k0*n_particle, k0*n_host
    z1, z2 = k1*diameter_nm/2, k2*diameter_nm/2
    Z1, Z2 = 1/n_particle, 1/n_host
    ell = np.arange(1, lmax+1)
    j1, j2 = spherical_jn(ell, z1), spherical_jn(ell, z2)
    h2 = j2 + 1j*spherical_yn(ell, z2)
    d1 = j1 + z1*spherical_jn(ell, z1, derivative=True)
    d2 = j2 + z2*spherical_jn(ell, z2, derivative=True)
    dh2 = h2 + z2*(spherical_jn(ell, z2, derivative=True)
                   + 1j*spherical_yn(ell, z2, derivative=True))
    a = (Z2*z1*j1*d2 - Z1*z2*j2*d1)/(Z2*z1*j1*dh2 - Z1*z2*h2*d1)
    b = (Z2*z2*j2*d1 - Z1*z1*j1*d2)/(Z2*z2*h2*d1 - Z1*z1*j1*dh2)
    sca = 2*np.pi/k2**2*np.sum((2*ell+1)*(np.abs(a)**2+np.abs(b)**2))
    ext = 2*np.pi/k2**2*np.sum((2*ell+1)*np.real(a+b))
    return dict(Csca_nm2=float(sca), Cext_nm2=float(ext), Cabs_nm2=float(ext-sca))

for index in (complex(2.4321, 0), complex(2.349, 0.083), complex(2.349, 0)):
    for order in (6, 8, 12, 16):
        print(index, order, mie_sections(index, lmax=order))
```

**接续结论：先让材料源数据、运行对象和输出结果一致；修正60 nm吸收球后按原门槛连续完成可执行的三尺寸分层验证。不要删吸收指标，不重跑已通过金球任务，不把低误差的共同错误输入当成物理正确。**
