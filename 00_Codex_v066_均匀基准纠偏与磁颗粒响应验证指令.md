# iSCAT v066：v065审查裁决、均匀基准纠偏与磁颗粒响应验证

> 执行者：Codex；审查与决策：ChatGPT。完整阅读后连续执行前置满足的任务，不要每一步停止等待GPT。
> 审查对象：`yyyyzoey/iscat-handoff`，`v065`固定提交 `acbd2e771b5c5c741f4ea070d99afd6638bc2fe2`。
> 本文是下一轮执行授权，不是新的MATLAB、BEM或实验结果。文中标为“本地数学审查”的数值来自审查端Python，不得改写为工作站结果。
> 最终目标仍为真实反射式iSCAT中磁纳米颗粒的观测量—粒径关系。当前材料和光路只属于 `LITERATURE_MATERIAL_EXPLORATION`；不作实验绝对粒径结论。

## 0. 必须先采用的审查裁决

### 0.1 保留成果，但撤回无证据的总括

1. **Mie球函数修正有依据。**v065的`mie_ref`已改用半整数球函数及Riccati导数递推。审查端以两种球函数构造重算，三尺寸截面相互一致并与v065日志的8位有效数字相容。此结论只覆盖数学公式和所列条件，不等于工作站完整预检已执行，更不等于BEM/Mie对照通过。[S03,S04,E02,E03]
2. **保留v064正确材料60 nm均匀基准。**其原结果表仍在v065且字节身份不变；三项截面误差从原值复算符合2%。原复远场只有摘要可读时继续标证据部分，不重求这笔BEM。[S10]
3. **v065的30/100 nm均匀基准尚未建立可接受证据。**驱动中标记`homog`与`layered`的1444分支使用相同`iscat_config('camera')`、同样字段、同一个`build_system(c)`，没有可见的无界水介质/无基底切换。字符串`tag`和输出文件名没有传入求解器。对确定的构建函数，这两段对应相同配置问题，而不是两个不同环境。实际MAT对象与未发布的构建实现仍需本机核验；不得仅凭本次文本审查宣称每个缓存一定是哪一种场景。[S03]
4. **端点四项BEM/Mie验收并未在新驱动中执行。**新脚本只计算并打印独立Mie截面，没有逐尺寸提取均匀BEM的三截面、复远场并与Mie比较，也没有四项联合断言。不能把分层图像比较的6个布尔值当成均匀基准四项通过。[S03,S05,S06]
5. **六组图像指标用了错误范数口径。**`norm(Cp(ix,ix)-Cf(ix,ix))/norm(Cf(ix,ix))`在41×41矩阵上使用谱范数。合同要求像元展平L2，即Frobenius相对范数。保留旧表为`REPORTED_SPECTRAL_RATIO`，从已有图/解重算正确指标，不能直接重命名旧数值，也不能预断新指标必过或必败。[S03,S05,S06,E01]
6. **计算账本冲突尚未解决。**status称6笔且60 nm复用v064缓存；发布日志有9条`BEM start`、9条`solve`，其中包括60 nm三笔，没有`cache hit`。源码只查v065本输出目录文件存在，不证明跨版本缓存复用。先恢复实际run/source/对象身份。不得忽略日志，也不得未核对日志来源就断言恰发生9笔独立新求解。[S01,S03,S04]
7. **有符号响应表未在本分支得到证明。**完整目录树不含约定的`magnetic_response_three_sizes.csv`，新驱动只写`three_size_forward.csv`，没有输出`C_center`/`S_area_nm2`。摘要的“约0.19到9.75”和“随D单调”不作为材料响应结论。绝对峰值不是有符号中心值或面积积分；三个离散尺寸也不证明连续单调或唯一反演。[S01,S02,S03,S08]
8. **材料常数变量正确不等于运行对象已验。**新驱动中常数为`complex(2.349,0.083)`，但没有实际材料对象读回、源文件驱动入口、场景负向拦截或独立参考断言的完成证据。根材料合同仍是旧版本。修复发布与真实入口，不臆断数值一定已经错误，也不据正确常数字符串签生产对象通过。[S03,S07]

### 0.2 本轮优先级

```text
A  核对实际求解账本/缓存场景，完成同一生产入口的守卫与调度测试（零BEM）
B  正确独立Mie与作者Mie逐尺寸、逐阶数预检（零BEM）
C  用现有分层系统重算Frobenius/公共方向复场，补真实有符号响应（零BEM）
D  查找并验收真正的30/100均匀解；确实缺失时各补一笔（本轮新增条件授权≤2）
E  合格三尺寸静态响应：原双焦面6条件＋域内九焦面27条件（零新BEM）
F  解析提取器补项、旧恢复/边界/P0在剩余额度内继续
→ 所有能执行的工作统一打包，最后交GPT审查
```

C可在D之前做诊断，不必等新BEM；只有相应尺寸的物理身份和所需门槛全部满足，才将其升级为已验磁材料响应。某分支失败只暂停依赖该分支的任务。不要又只改一条README后结束本轮。

### 0.3 冻结约束不变

- IDENTITY，行camera_x/列camera_y；禁止转置、翻转、相位/幅值对齐择优。
- 保留完整干涉强度和像元积分，不删纯散射项、不作显示归一化。
- 原1506e合成相机配方不改、不按D调光、不多曝光；本轮不启动新噪声/相机批次。
- 均匀基准四项分别`<0.02`；分层规定图像/复场门槛不放宽。工程常数读回`<=1e-12`、数学参考交叉检查`<=1e-10`不是物理门槛替代。
- P0完整direct/reflected/total相对Frobenius各`<1e-10`，参考增量`<0.005`仍独立。
- 不重建金球库、不重跑B1、R2–R6已完成批次，不将旧金球检测阈值迁移为磁材料检出率保证。
- 固定作者基线不改；候选或包装修改有父版本、差分和真实路径。

## 1. 审查证据、复核范围与状态语义

审查端读取了固定提交的status/review、完整目录树、完整v065驱动、日志和六行前向表，并核对旧60 nm结果和v065实际执行合同。将三份小文本从连接器原文重建后，Git blob全部匹配：

| 文件 | Git blob | 本次检查 |
|---|---|---|
| tables/three_size_forward.csv | e8478ba803fd81e255768f8ffbe0a6700bec6429 | 6个D/z键无重复，原值与百分比换算 |
| logs/matlab_run.log | 773f4bbc6d0b5726773c1c0348a5521cb693b322 | 9 start、9 solve、0 cache hit；不据此最终认定独立新求解数 |
| tables/m2r_fe3o4_60nm_results.csv | 1938c4959e731c93e05c18d2738491027afca771 | 3截面相对误差算术复核 |

没有取得工作站完整MAT对象、C数组或新的原始复场；因此本审查**没有**重算六组真实Frobenius误差、验证实际solver class或独立计时。源码有问题与原始数值物理失败分开登记。

源表六个旧值为0.00561928518215751、0.00564036674802079、0.00527492053848303、0.00533721440382991、0.00667965525638135、0.00566611849688412。它们是发布代码所计算的谱范数口径；不能抄入新Frobenius列。

状态分别使用：

```text
execution_status: NOT_STARTED / RUNNING / COMPLETED / FAILED / INTERRUPTED / UNKNOWN
validation_status: NOT_EVALUATED / PASS / FAIL / INDETERMINATE
evidence_status: COMPLETE / PARTIAL / MISSING / CONFLICTING
```

本轮初始状态：Mie公式修正可接受；原60均匀摘要PASS、原数组证据按实标；端点均匀待核验；分层原谱范数只为诊断；正确分层Frobenius未评；有符号响应未证明；计算账本CONFLICTING。实际补证后由程序更新，不手填乐观总状态。

## 2. A：场景身份、成本账本、同一入口守卫（零BEM）

### [放行条件]

能访问工作站真实工程、源码、v064/v065产物。先核对运行身份，不按旧PID停止进程，也不启动第二份相同任务。高内存计算串行。

### [A1：逐笔恢复账本]

读取实际日志、调用命令、源文件hash、运行ID、时间戳和MAT元数据，列出9个“命名槽位”：3尺寸×(homog1444、layered576、layered1444)。每个槽位可映射到旧缓存、新求解、错误场景、重复计算或无法确认。

必须区分 `planned_slot`、`actual_solver_call`、`unique_physical_problem`、`reused_artifact` 四个计数，不把两份文件当两个独立参考，也不因命名错误或门槛失败抹去成本。

- 60 nm重点与v064原文件交叉核对，不能只看数值恰好相同。
- 相同场景的重复求解保留历史，不重复当独立验证；若原系统有效，可选一个完整且身份明确的缓存供后处理。
- 若发现日志混拼或摘要填错，提供可定位解释和原件；不重写旧日志。
- 缺少时间记录就填null；不将网格数、摘要猜测或文件修改时间等同solve_seconds。

输出`solve_ledger_reconciled.csv`，包含任务/源run/文件/实际类型/哈希/是否新调用/旧缓存来源/计数依据/冲突状态。账本不能证明时保留UNKNOWN，不虚构唯一求解次数。

### [A2：从真实对象验证物理类型]

恢复实际使用的`build_system.m`、`iscat_config.m`、`render_system.m`及材料分支，保存源码身份与必要差分。检查`constant_index`是否真的进入材料对象，不能仅证明cfg里有这个字符串。

| 合同 | 均匀水介质M2 | 玻璃/水分层M3 |
|---|---|---|
| 外部环境 | 全空间均匀水，n=1.33，无玻璃平面 | 玻璃1.50/水1.33，有界面 |
| 球位置 | 原均匀基准原点，D是真直径 | 表面gap5 nm，中心h=5+D/2 |
| 构建路径 | 经验证的均匀Galerkin路径 | 已有分层路径 |
| 可用解析参考 | 同环境球Mie | 不把均匀Mie当分层真值 |
| 后处理光路 | 公共球面方向/权重作远场比较 | 玻璃侧NA1.3等原配置 |

来源链至少含实际solver class、实际背景/层结构/材料对象读回、球几何、照明、λ0、规则和配置。仅看类名仍不足，必要时读构建调用链及对象域。

如果新脚本中两个1444分支确实产生同一有基底配置，标`SCENARIO_CONTRACT_MISMATCH`，原`homog`文件只作其真实场景缓存/诊断，不得以改名让它通过M2。反之，若运行时确有不同实现或分派，必须交回该实现/原日志；不能靠口头解释。

### [A3：同一生产入口与强制拒绝]

继承v065的物理输入和原工程容差：Fe3O4 Querry源节点520 nm→0.5200 μm，n=2.349、κ=0.083、ε=5.510912+0.389934i，μr=1。采用`complex(nr,kap)`；源YAML由已知blob和完整SHA-256双重记录。根材料合同纠正到1985、精确节点和正确相容时间/外向波约定，旧合同保留在历史区。

由Mie/M2/M3调用同一个经验证输入入口。将实际Material读回与源节点/不可变计划比对，不只与同一个局部常数互比。恢复`<=1e-12`，不能沿用未经批准的1e-5或1e-9作为签证。

负向测试必须注入生产入口、捕获异常，并断言BEM构造/求解回调计数为0。除原实数相加、丢虚部、源字节变化、单位、半径/直径外，本轮新增两项：

1. 把分层配置送入均匀M2计划，必须拒绝；不能打印`homog`后接受。
2. 将有基底旧缓存改名为M2输出，完成检查必须拒绝；不能只用`isfile`跳过。

五项原夹具及两项新增夹具都不是实际BEM，不计物理预算。不能用`assert(bad~=expected)`代替生产入口拒绝测试。

### [A4：断点和预依赖真实生效]

完成键至少含物理类型、D、材料源/读回、λ、几何/层结构、规则、求解器源码哈希和输入配置。图像后处理键另含焦面、像元/ROI/积分、成像配置和源sol哈希。不要把zf加入BEM键而引发重复求解。

- 不同outRoot中的同身份缓存可复用；输出目录名称不是完成证明。
- 完成文件写后回读，临时/损坏文件不得跳过为成功。
- 先5再100、同一任务重复启动等伪记录测试沿用原授权，不生成新相机数据。
- M2未通过时，任何新的依赖M2计划都不得进入求解回调。本轮没有新增分层求解，但此守卫仍需为后续准备。

### [失败处置/自动继续]

已知输入不符或场景未建立时，不启动新BEM。恢复记录、解析/导出、其他明确无依赖检查继续。缺失完成记录不意味着必须重算：先解/复场、再后处理、最后才考虑第5节明确允许的两笔纠错。

本轮新增最多2轮合并的“场景分派/同一验证入口/数学预检/导出”定向实现迭代；旧修复账完整保留，不重置。不得用这项授权修改作者物理核、增加网格或放宽门槛。

## 3. B：三尺寸Mie预检必须落为数值断言（零BEM）

### [放行条件]

A输入与实际作者库路径通过。固定基线仍为`ce49f77f096337db8be54c46d83696d37b0b23d5`，不静默升级。检查实际`Material`、`miesolver`解析路径，避免类缓存和旧包遮蔽。

### [必须执行]

复用v065已经修正的半整数参考，不再用旧错误helper。参考不得调用正在验证的作者miecoefficients作为独立核。

- D=30、60、100；λ0=520 nm；外部无损水n=1.33；μr=1；目标n=2.349+0.083i。
- 作者Mie和独立参考各返回未舍入Csca/Cext/Cabs，逐非零截面相对差`<=1e-10`。
- 阶数6/8/12/16保存全精度；8→12与12→16各非零截面相对变化`<=1e-10`。
- 无损控制用原`abs(Cabs)/Cext<=1e-10`；不把Cabs强制裁零，近零普通相对误差为null并写明专属判据。
- 旧2.4321实数只作错误输入诊断，不作为目标。
- 注入错误参考返回值/NaN后预检必须失败，求解回调计数为0。
- 所有判据聚合为机器布尔，不能只打印三行截面后继续。

审查端本地结果（nm²，仅为调试对照，禁止硬编码成执行结果）：

| D/nm | Csca | Cext | Cabs |
|---|---:|---:|---:|
| 30 | 1.1141977267924568 | 19.14117607876315 | 18.02697835197069 |
| 60 | 73.86673175413402 | 237.97510781501168 | 164.10837606087767 |
| 100 | 1624.8257290252168 | 2592.4202464128443 | 967.5945173876275 |

本地两种实现相对差最大约6.6e-15；v065日志只有8位有效数字，因此只能说“打印精度相容”，不能说由该日志证明1e-10原生一致性。

### [失败处置/自动继续]

未通过则停止新均匀BEM；保留具体误差、API、输入和路径，不删除吸收指标。通过后直接进入C/D，不逐尺寸请求GPT。

## 4. C：已有分层系统的正确范数与物理身份验收（零新BEM）

### [放行条件]

相应缓存已在A中确认真实材料、几何、层结构与源身份；有C数组、场或sol可复用。门槛未完全满足时可以做诊断，但不得标正式磁材料PASS。

### [C1：原六组像元L2重算]

原合同指标为中央41×41公共ROI，像元65 nm、q5、同轴、同物理归一化。按实际坐标确定索引，数组确为65×65且中心确在索引33时才用13:53；不能拿错误单下标掩码替代。

可使用以下片段接入已有后处理；这不是审查端已运行MATLAB代码的声明：

```matlab
P = Cp(ix,ix);
R = Cf(ix,ix);
assert(isequal(size(P),[41,41]) && isequal(size(R),[41,41]), 'ROI_SHAPE');
assert(all(isfinite(P(:))) && all(isfinite(R(:))), 'NONFINITE_ARRAY');
Delta = P - R;
num = norm(Delta(:),2);
den = norm(R(:),2);
assert(isfinite(den) && den>0, 'REFERENCE_NORM_NOT_VALID');
rF = num/den;
pass_image = isfinite(rF) && rF < 0.02;
rSpectral_diagnostic = norm(Delta,2)/norm(R,2);
% 写两个不同列；不能用二者最小值，也不能沿用旧gate2pct。
```

输出真实分子、分母、相对值、百分比、指标定义、ROI、源数组/系统/脚本hash和门槛。参考范数近零/零时原相对值不能计算则如实标INDETERMINATE，保存绝对差，不能加realmin或调相位使通过。

本轮新增零BEM指标负向夹具：R为41×41仅R(1,1)=1的矩阵，Delta=0.006*eye(41)。谱范数比为0.006，Frobenius比为0.0384187454。测试必须按Frobenius拒绝2%门槛；这只是数学反例，不是六个真实场的估计。

### [C2：复场与对象读回]

同D的生产/精细散射复场在相同公共方向和权重比较。两边原角度网格不同则用各自已有sol重算公共方向，属于后处理；不能直接比较不对应的数组或重新求BEM。保持原原始复场相对L2门槛和原度量定义；保存共同角度、权重、原场，不作自由相位或幅值拟合。

实际读回并报告：D、n/κ/ε、glass1.50/water1.33、gap5、h=5+D/2、λ520、法向x偏振、玻璃侧NA1.3、物方像元65、q5、生产50/51+Bessel2001与精细100/151+Bessel4001、IDENTITY。配置与镜头实际收集介质都要核对，不只读JSON里1.50。

保留完整`|Eref+Esca|²`，以及对应参考强度。若检查`It=Iref+Isca+Icross`，这是代数自检，不当作独立物理准确性证明。

### [失败处置/自动继续]

谱范数旧表保留；新FrobeniusFAIL如实报告，只停相关场景扩展。不要以“旧数小”预判新数通过，不重复整个批次。只有现有表、没有sol/场/图时证据PARTIAL，不自动新建全部分层解。

C2相关条件通过后导出第6节原双焦面有符号响应。D端点均匀缺项独立推进。所有已有分层结果都不能替代M2真均匀对照。

## 5. D：30/100 nm真正的均匀基准（新增条件授权最多2笔）

### [放行条件]

A/B已通过；真实缓存搜索完成；物理问题明确为无界均匀水中的目标球。对应场景身份未建立时不得通过文件名复用。

### [先复用，再有条件计算]

逐尺寸先找真实均匀sol或完整均匀复场/截面，来源可证则直接验收/后处理，不新求。

确实不存在合格均匀缓存时，本轮**明确新增**最多各1笔：

| plan_id | D/nm | 环境 | 网格 | 新BEM最多 |
|---|---:|---|---:|---:|
| M2H_D030_CORRECTED_V066 | 30 | 全空间均匀水1.33、球原点 | 1444 | 1 |
| M2H_D100_CORRECTED_V066 | 100 | 同上 | 1444 | 1 |

这不是把v065已消费的错误场景计算算成“没跑”，也不是重置旧余额。旧求解成本全部保留；两笔本轮纠错单独入账。有匹配缓存时相应授权不消耗、不转作其他D或网格。

### [正确构建与比较]

以已读v064均匀驱动的实际路径为基准，参数化D而非换文件名：

```matlab
p   = trisphere(1444, D_nm);        % 保持均匀基准原点
mw  = Material(1.33^2, 1);
mp  = Material(epsParticle, 1);     % epsParticle来自共同已验入口
% 在此补真实mp/mw读回与计划/单位守卫
 tau = BoundaryEdge([mw,mp],p,[2,1]);
% 使用原galerkin.bemsolver均匀路径、原普通/近邻/Duffy规则和激励。
% 不用未经证明能切换场景的build_system('camera')冒充此路径。
```

参数继承v064：普通triquad3、近邻triquad11、nduffy3、relcutoff2、order3、原x偏振+z传播、公共sphere_rule(48,97)及原复场比较。调用接口以实际固定源码为准，不重写作者算法。

保存sol、tau/材料读回、eB/eM、公共dir/w、两侧Csca/Cabs/Cext、原始分子分母及每项判断。四项分别`<0.02`且必须全部纳入阶段gate：

1. 同方向/权重原始复远场相对L2；
2. 散射截面相对误差；
3. 吸收截面相对误差；
4. 消光截面相对误差。

所有参考量有限且非零、可分辨后才相除。BEM吸收与消光/散射恒等式只能作辅助自检；不能用同一公式两次得到相等就替代独立Mie对照。

### [失败处置/自动继续]

求解发生即记成本，失败也扣。每个端点只有这1笔，不增加网格或重试额度。导出失败但解仍在时保存并续后处理，不再次求解。一个端点失败不阻止另一已满足前置的端点。

原60 nm均匀数值仍保留，不另求一笔“统一风格”。若全部原解/场丢失继续摘要PASS、证据PARTIAL，不能编造恢复。新的字段/函数不能用不同目录强制重跑60 nm。

## 6. E：实际输出有符号响应，扩展为有界静态焦面研究（零新BEM）

### [E1：先完成原双焦面六条件]

分别输出生产和精细的：

- `C_center`：实际x=y=0物理像元的有符号对比度；固定位置，不找最亮峰。
- `S_area_nm2 = 65^2 * sum(C(central_41x41),'all')`：保留面积单位，不能变成max(abs(C))。
- D、zf、光路/源场/单位/ROI/轴/提取脚本hash、P/R绝对差和已验图像/复场相对误差。

无中心像元时按事前声明的坐标规则处理，不为了响应更强选择附近像元。描述量接近零时普通相对误差记null并报绝对差；它们不是新的自动放行门槛。

完整有符号C数组与两侧输出一并保存，写后读回表格，逐行由同一数组重算。必须实际生成`magnetic_response_three_sizes.csv`；没有生成时状态NOT_STARTED，不将最大绝对峰值口头描述替代文件。

不要沿用没有Fe3O4图像来源的“0.19→9.75”。这串数字目前未建立材料来源，既不能作为真值，也不因怀疑来源而删除历史。

### [E2：本轮明确新增的零BEM研究规模]

相应三尺寸在规定范围内完成验证后，利用已有分层sol开展静态焦面探索：

```text
D_nm = [30, 60, 100]
zf_nm = [375, 400, 425, 450, 475, 500, 525, 550, 575]  # 9个，不是11个
xy_nm = [0,0]
最大条件数 = 3*9 = 27
生产/精细各一次后处理，最多54个render任务；已有6条件输出复用。
新增BEM = 0
```

这是本轮新增的`EXPLORATORY_STATIC_FOCUS_SWEEP`，不是v065已完成任务，也不是改变物理模型。每个D的几何h=5+D/2固定，改变的是zf，不是移动颗粒高度。不超出原工作焦面范围，不增加D/材料/波长/间隙。

每个焦面都记录原P/R图像门槛；新焦面失败标该条件失败，不因两旧焦面通过就自动签全域通过。对尚未通过必要物理前置的尺寸可保留诊断，不纳入已验响应结论。

研究问题：同D随zf的有符号响应是否变号/接近零；在各相同zf上三个D的观测排序如何；中心与积分量是否给出不同趋势。输出事实和对比，不预写“递增”结果。

最多只报告实际离散点排序，以及30→60和60→100的有限差商；不称连续导数、不把三个点拟合成可靠D^3标定、不得从离散点宣布无多解或全域可逆。源数据未支持时明确说尚不能判断。

### [本轮明确不放行]

不建立原32节点式Fe3O4全密库，不开9–13个新D扫参或噪声批次，不凭这27个静态条件反演未知实验颗粒。真实提取量是约400 Hz时，仍需要运动→曝光→采样→同一提取器；静态曲线不能替代它。

后续建库需根据这次实际响应、目标可测量定义和有约束的参数域另作决策，而不是按版本号自动扩展。

## 7. F：其他支线的有限继续

1. **解析提取器**：继承未完成的400 Hz非整频点有限和/FFT、曝光积分与开始/中心时间戳相位、近零null序列化检查。Fs5000/N2001/k160、100 μs仅为夹具；保持ANALYTIC_REFERENCE_ONLY。补真实生成源码，而不是只继承16条PASS表。源实验test.m/数据集按已知路径有界恢复；未找到就记录范围，不用参考实现冒名替代。
2. **实验输入**：源文件中尚缺真实样品/提取器，这不阻止已标注文献模型的静态探索；但65 nm、q5、中央ROI仍是合成合同，不作为实测仪器参数。真实7.29数据与select数据不能混用。
3. **旧R5恢复**：原最多4个seed重建余额仅在源输入/代码可确定时执行，标`DETERMINISTIC_RECONSTRUCTION_NOT_ORIGINAL`。不增加独立样本，不恢复为历史原帧。
4. **B2**：继续原未用32份既有观测诊断、最多4份×21个zf剖面的预算；不改域、阈值、优化器或删边界记录。该任务不是磁材料前向完成的统一前置。
5. **P0**：先补保存数组的SL/DL相对Frobenius与完整贡献/映射证据；不从旧绝对max差继承相对PASS。Hook需命中实际duffy1/eval2并记录次数/stack/shape/资源；未命中标TARGET_PATH_NOT_REACHED。只要局部回归、覆盖/资源、原direct/reflected/total各`<1e-10`全部前置通过，才可执行原最多1笔rule7参考，增量`<0.005`。未通过不启动，不把原因预写为纯浮点。

高内存P0和磁材料BEM不能并发；P0独立OPEN不自动阻塞未受影响的rule3，但发现真实共用缺陷时按影响范围暂停。旧修复和求解次数不清零。

## 8. 本轮预算及连续执行边界

| 项目 | 本轮上限 | 授权性质 |
|---|---:|---|
| 30 nm真实均匀缺失纠错 | 1笔BEM | 本轮明确新增条件授权；合格缓存存在则0 |
| 100 nm真实均匀缺失纠错 | 1笔BEM | 同上 |
| 60 nm任何重求 | 0 | 不授权 |
| 新的分层求解 | 0 | 已报告存在的系统仅复用/核验 |
| 正确范数、实际对象、原六条件响应 | 0笔BEM | 未完成验收补证 |
| 九焦面探索 | 最多27条件/54个render，旧结果扣除 | 本轮明确新增零BEM后处理 |
| 新金球、相机/噪声、D或波长扫描、全密库 | 0 | 不授权 |
| P0大rule7参考 | ≤1笔 | 原有独立条件授权，不占/不挪磁材料额度 |
| 本轮包装/场景/守卫合并定向实现迭代 | ≤2轮 | 明确新增，旧修复账保留 |

累计旧成本须先查账；不能根据尚冲突的6/9报告填一个确定历史总数。两笔新纠错单独计入，不能把错误旧求解当作未消耗。预算耗尽时仍完成无BEM可执行工作，不借另一目录重复运行。

每任务必须有输入和完成哈希、失败记录、依赖关系。PASS且全部前置真实满足就自动下一任务；需要改门槛/光路/范围或超预算时只停对应分支。不要每一笔等GPT，也不要在数值FAIL后继续把依赖结果标正式通过。

## 9. 交付：一个ZIP，一份当前可读汇总，发布前自检

结果统一为`iscat_v066_return.zip`。至少含：

```text
00_README.md                         # 明确本次固定源提交和当前结果范围
00_Codex_v066_执行指令.md
00_本轮全部文本汇总.md               # 由当前JSON/CSV生成，不冒用v059旧内容
status.json / review.md
current_artifact_index.json          # 当前权威文件与history区明确区分
material_contract_current.json / axis_contract.json
solve_ledger_reconciled.csv / dependency_checks.json
source/                             # 实际加载的关键源码、参数化M2/M3入口、评价器、diff
logs/                               # run_id/命令/源hash/原始异常/守卫和阶数结果
numeric/                            # 新均匀完整可核对小例；既有分层C/公共复场与必要元数据
 tables/
  material_scenario_guard_tests.csv
  mie_reference_crosscheck.csv
  mie_order_convergence.csv
  homogeneous_bem_mie_four_gates.csv
  layered_forward_frobenius.csv
  layered_complex_field_checks.csv
  magnetic_response_three_sizes.csv
  magnetic_response_focus_sweep.csv
  runtime_cache_resume_tests.csv
  task_status.csv
  publication_checks.csv
manifest_sha256.csv
```

未执行项不用空CSV伪装完成，给明确状态及原因。旧结果保留history并标来源，根表不继续同时混入v063错误材料数值作为当前三尺寸检查。阈值/轴原件不篡改；当前质量未验证不能被历史synthetic_detection_validation字符串盖过。

发布前必须机器检查：

- 字段数、类型、唯一ID、非有限值、引用文件、表/JSON/日志结果一致。
- 物理模式与solver/对象读回一致；图像指标定义固定Frobenius；旧谱范数只列诊断。
- 四项均匀门槛缺一项就是未完整验收，不聚合为PASS；六张分层图不等于四项M2。
- 当前有符号响应确由对应Fe3O4数组重算，缺文件不得写已生成。
- 哈希按实际要发布的字节计算，区分工作站字节与行尾规范化后的发布字节；所有关键文件引用可解析。哈希清单不宣称为自己的签名。
- run_id、缓存命中、新求解和预算账一致；不能出现有九条新求解日志却没有说明的“只用了六笔”。
- 原始实验数据、凭据、个人信息和完整本地路径不因交付需求被无授权公开；公开仓库可读文本需去敏，工作站原记录保留。

真实数值大文件超限制可留工作站，明确路径/变量/shape/轴/hash和未随包状态。当前只有文本表可读时不能称原数组全部独立验算。

## 10. 来源与外部核验

所有S条目均固定在 `yyyyzoey/iscat-handoff@acbd2e771b5c5c741f4ea070d99afd6638bc2fe2`，除H条目为已上传历史合同：

- S01 `status.json`，blob `dfd0bf84b17c773325940db0ba9db89d20dccc24`。
- S02 `review.md`，blob `56fb3a83561b64d84c64401fa72ec364f5e900bb`。
- S03 `source/run_v065_three_size.m`，blob `302abcd844965f5a814347b15c5003fba6e11187`；本次全文阅读。
- S04 `logs/matlab_run.log`，blob `773f4bbc6d0b5726773c1c0348a5521cb693b322`；原文本重建/blob核对和计数。
- S05 `tables/three_size_forward.csv`，blob `e8478ba803fd81e255768f8ffbe0a6700bec6429`；原文本重建/blob核对。
- S06 `00_Codex_v065_参考实现修复与三尺寸磁颗粒验证指令.md`，blob `e45e2fd813ee5c1a2d4f9ff1c121bf3f1263f5ba`；尤其第2—6、8节，含明确Frobenius、四项M2、六笔与60缓存规则。
- S07 `material_contract.json`，blob `a2998d741a84216f07f76140358e8c9441b04719`；仍是旧v063合同。
- S08 当前提交递归目录树，`truncated=false`；没有约定有符号响应表和端点均匀四项表。
- S09 `source/run_v064_m2r_fe3o4.m`，blob `e9894aea3350cd95f28e5ae82d8c3702a773c6e5`；保留的真实均匀Galerkin驱动。
- S10 `tables/m2r_fe3o4_60nm_results.csv`，blob `1938c4959e731c93e05c18d2738491027afca771`。
- H01 已上传`progress(2).md`，用途为历史合同和目标；旧v059执行状态不覆盖本轮。
- H02 已上传`codex-progress.md`，用于冻结约束和协作方式，不作v065运行证据。

本轮额外核对的官方数学/API资料，不是项目执行证据：

- E01 MathWorks norm：`https://www.mathworks.com/help/matlab/ref/norm.html`。矩阵默认2范数为最大奇异值；Frobenius等于展平向量Euclidean norm。
- E02 NIST DLMF §10.47、§10.51：`https://dlmf.nist.gov/10.47`、`https://dlmf.nist.gov/10.51`。球函数半整数定义和导数递推。
- E03 SciPy spherical_jn官方接口：`https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.spherical_jn.html`。本地计算环境实际为NumPy2.3.5、SciPy1.17.0；网页版本不能被写成工作站已安装版本。

## 附录A：审查端本地检查结果（不是工作站执行证明）

- 三份重建小文本Git blob全部匹配。
- 正确半整数参考与直接球函数/导数参考三尺寸各截面相对差最大6.5765e-15；8→12和12→16在此次双精度计算中差为0，不推广为所有材料/尺寸的一般收敛定理。
- 三尺寸参考与v065日志相同打印精度相容；没有从8位日志推导1e-10原生门槛。
- 60 nm旧表截面误差复算：sca=0.007924569518625435、abs=0.0042015447615617795、ext=0.005357160042373112，均小于0.02。
- 六行前向只核对文本/换算，未取得原C阵列，未重算真实Frobenius。
- 数学反例：谱范数0.006、Frobenius0.03841874542459709；不属于真实iSCAT数据。
- 日志计数9/9/0，只反映发布文本，不足以最终确证独立新求解数。

以下代码已在审查端运行；不修改用户工程，可单独用于数学/文本核对。它不下载文件、不求BEM、不替代原生MATLAB验收。

```python
"""Local mathematical and small-table audit. No MATLAB/BEM is executed.
Source strings are transcribed from connector-returned UTF-8 and Git-blob checked.
"""
from __future__ import annotations
import csv, hashlib, io, json, math, re
from pathlib import Path
import numpy as np
import scipy
from scipy.special import jv, yv, spherical_jn, spherical_yn

ROOT = Path(__file__).resolve().parent
FORWARD = '''D,zf,relL2_prod_vs_fine,gate2pct
30,450,0.00561928518215751,1
30,550,0.00564036674802079,1
60,450,0.00527492053848303,1
60,550,0.00533721440382991,1
100,450,0.00667965525638135,1
100,550,0.00566611849688412,1
'''
M2_60 = '''mesh_request,lambda_nm,material,raw_complex_relative_L2,BEM_sca,Mie_sca,sca_error,BEM_abs,Mie_abs,abs_error,BEM_ext,Mie_ext,ext_error,passed
1444,520,Fe3O4_complex_2.349+0.083i,0.00391740599200391,73.2813697032347,73.866731754134,0.00792456951862543,163.41886737311,164.108376060877,0.00420154476156196,236.700237076345,237.975107815011,0.00535716004237431,1
'''
LOG = '''[065:mie] D=30 Csca=1.1141977 Cext=19.141176 Cabs=18.026978
[065:mie] D=60 Csca=73.866732 Cext=237.97511 Cabs=164.10838
[065:mie] D=100 Csca=1624.8257 Cext=2592.4202 Cabs=967.59452
[065] D30 homog mesh=1444 BEM start
[065] D30 homog mesh=1444 solve 243.8s
[065] D30 layered mesh=576 BEM start
[065] D30 layered mesh=576 solve 34.9s
[065] D30 layered mesh=1444 BEM start
[065] D30 layered mesh=1444 solve 232.6s
[065] D60 homog mesh=1444 BEM start
[065] D60 homog mesh=1444 solve 227.4s
[065] D60 layered mesh=576 BEM start
[065] D60 layered mesh=576 solve 35.8s
[065] D60 layered mesh=1444 BEM start
[065] D60 layered mesh=1444 solve 228.9s
[065] D100 homog mesh=1444 BEM start
[065] D100 homog mesh=1444 solve 235.1s
[065] D100 layered mesh=576 BEM start
[065] D100 layered mesh=576 solve 35.4s
[065] D100 layered mesh=1444 BEM start
[065] D100 layered mesh=1444 solve 230.4s
[065:fwd] D=30 zf=450 prod-vs-fine relL2=0.0056 gate=1
[065:fwd] D=30 zf=550 prod-vs-fine relL2=0.0056 gate=1
[065:fwd] D=60 zf=450 prod-vs-fine relL2=0.0053 gate=1
[065:fwd] D=60 zf=550 prod-vs-fine relL2=0.0053 gate=1
[065:fwd] D=100 zf=450 prod-vs-fine relL2=0.0067 gate=1
[065:fwd] D=100 zf=550 prod-vs-fine relL2=0.0057 gate=1
[065] all forward comparisons done
'''

def git_blob(text: str) -> str:
    b = text.encode('utf-8')
    return hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()


def save_checked(name: str, text: str, sha: str) -> dict:
    actual = git_blob(text)
    if actual != sha:
        raise ValueError(f'{name}: connector text mismatch {actual} != {sha}')
    (ROOT / name).write_bytes(text.encode('utf-8'))
    return {'name': name, 'git_blob': actual, 'expected_git_blob': sha,
            'verified': True, 'bytes': len(text.encode('utf-8'))}


def mie_coeff(n_particle: complex, diameter: float, lmax: int, method: str):
    """Nonmagnetic sphere in lossless n=1.33 host, wavelength=520 nm.
    Same impedance/coefficient convention as inspected project mie_ref.
    Two implementations differ in spherical-function construction/derivative.
    """
    k0 = 2*np.pi/520.0
    k1, k2 = k0*n_particle, k0*1.33
    z1, z2 = k1*diameter/2, k2*diameter/2
    Z1, Z2 = 1/n_particle, 1/1.33
    ell = np.arange(1, lmax+1)
    if method == 'half_integer':
        sj = lambda l,z: np.sqrt(np.pi/(2*z))*jv(l+0.5,z)
        sy = lambda l,z: np.sqrt(np.pi/(2*z))*yv(l+0.5,z)
        j1,j2 = sj(ell,z1),sj(ell,z2)
        h2 = j2+1j*sy(ell,z2)
        d1=z1*sj(ell-1,z1)-ell*j1
        d2=z2*sj(ell-1,z2)-ell*j2
        dh2=z2*(sj(ell-1,z2)+1j*sy(ell-1,z2))-ell*h2
    elif method == 'scipy_spherical':
        j1,j2=spherical_jn(ell,z1),spherical_jn(ell,z2)
        h2=j2+1j*spherical_yn(ell,z2)
        d1=j1+z1*spherical_jn(ell,z1,derivative=True)
        d2=j2+z2*spherical_jn(ell,z2,derivative=True)
        dh2=h2+z2*(spherical_jn(ell,z2,derivative=True)+1j*spherical_yn(ell,z2,derivative=True))
    else:
        raise ValueError(method)
    a=(Z2*z1*j1*d2-Z1*z2*j2*d1)/(Z2*z1*j1*dh2-Z1*z2*h2*d1)
    b=(Z2*z2*j2*d1-Z1*z1*j1*d2)/(Z2*z2*h2*d1-Z1*z1*j1*dh2)
    Csca=2*np.pi/k2**2*np.sum((2*ell+1)*(np.abs(a)**2+np.abs(b)**2))
    Cext=2*np.pi/k2**2*np.sum((2*ell+1)*np.real(a+b))
    return np.array([Csca,Cext,Cext-Csca],dtype=float)


def main():
    checked=[save_checked('three_size_forward.csv', FORWARD,'e8478ba803fd81e255768f8ffbe0a6700bec6429'),
             save_checked('m2r_fe3o4_60nm_results.csv',M2_60,'1938c4959e731c93e05c18d2738491027afca771'),
             save_checked('matlab_run.log',LOG,'773f4bbc6d0b5726773c1c0348a5521cb693b322')]
    fwd=list(csv.DictReader(io.StringIO(FORWARD)))
    assert len(fwd)==6 and len({(x['D'],x['zf']) for x in fwd})==6
    source_values=[float(x['relL2_prod_vs_fine']) for x in fwd]
    assert all(np.isfinite(source_values))
    table_percent=[{'D_nm':int(x['D']),'zf_nm':int(x['zf']),
                    'reported_matrix_spectral_ratio':float(x['relL2_prod_vs_fine']),
                    'percent':100*float(x['relL2_prod_vs_fine'])} for x in fwd]
    m2row=list(csv.DictReader(io.StringIO(M2_60)))[0]
    m2audit={}
    for s in ['sca','abs','ext']:
        B,R=float(m2row['BEM_'+s]),float(m2row['Mie_'+s])
        r=abs(B-R)/abs(R)
        m2audit[s]={'ratio_recomputed':r,'delta_from_csv':r-float(m2row[s+'_error'])}
        assert r<0.02
    math_results=[]
    for D in [30.,60.,100.]:
        half=mie_coeff(2.349+0.083j,D,12,'half_integer')
        sph=mie_coeff(2.349+0.083j,D,12,'scipy_spherical')
        diff=np.abs(half-sph)/np.abs(sph)
        assert np.all(diff<=1e-10)
        conv={}
        for L0,L1 in [(8,12),(12,16)]:
            v0=mie_coeff(2.349+0.083j,D,L0,'half_integer')
            v1=mie_coeff(2.349+0.083j,D,L1,'half_integer')
            conv[f'{L0}_to_{L1}']=(np.abs(v0-v1)/np.abs(v1)).tolist()
            assert np.all(np.abs(v0-v1)/np.abs(v1)<=1e-10)
        match = re.search(rf'D={int(D)} Csca=(\S+) Cext=(\S+) Cabs=(\S+)',LOG)
        printed=[float(x) for x in match.groups()]
        # Log is %.8g. Compare decimal representation, not an alleged full precision match.
        assert [float(f'{x:.8g}') for x in half]==printed
        math_results.append({'D_nm':D,'Csca_nm2':float(half[0]),'Cext_nm2':float(half[1]),
            'Cabs_nm2':float(half[2]),'relative_difference_methods':diff.tolist(),
            'order_convergence_relative':conv,'matches_log_print_precision':True})
    # Purely algebraic sentinel: matrix spectral <2% while pixel L2 >2%.
    R=np.zeros((41,41));R[0,0]=1.0
    E=0.006*np.eye(41)
    spectral=float(np.linalg.norm(E,2)/np.linalg.norm(R,2))
    fro=float(np.linalg.norm(E,'fro')/np.linalg.norm(R,'fro'))
    assert spectral<0.02 and fro>0.02
    report={'scope':'LOCAL_MATH_AND_TEXT_AUDIT_NO_MATLAB_NO_BEM_NO_FIELD_ARRAYS',
        'repository_commit':'acbd2e771b5c5c741f4ea070d99afd6638bc2fe2',
        'numpy_version':np.__version__,'scipy_version':scipy.__version__,
        'source_text_blob_checks':checked,'forward_values_not_recomputed_from_arrays':table_percent,
        'M2_D60_cross_section_arithmetic':m2audit,'Mie_local_mathematical_check':math_results,
        'matrix_norm_counterexample':{'spectral_ratio':spectral,'Frobenius_ratio':fro,'physical_data':False},
        'published_log_counts':{'BEM_start_lines':LOG.count('BEM start'),
                               'solve_lines':len(re.findall(r'\bsolve [\d.]+s',LOG)),
                               'cache_hit_lines':LOG.count('cache hit'),
                               'proven_unique_runtime_solves':None}}
    (ROOT/'audit_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))

if __name__=='__main__':
    main()

```

**接续结论：先查清算的是什么，再用原指标验收；只有真实缺失的端点均匀基准使用本轮有限纠错额度。已有分层场用于有符号静态响应研究，不重建金球，不跳过吸收，不用谱范数或摘要PASS替代合同。**
