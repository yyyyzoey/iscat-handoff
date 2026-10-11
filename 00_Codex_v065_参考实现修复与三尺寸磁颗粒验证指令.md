# iSCAT v065：v064审查裁决、参考实现修复与三尺寸磁颗粒验证

**用途：本轮交给Codex的唯一执行指令。全文读完后连续执行，不逐步停下等待GPT。**

审查基线：`yyyyzoey/iscat-handoff`，分支`v064`，提交`188e2718a54c1f3812b17379917d947c686d6cd9`。
上一轮合同：`00_Codex_v064_材料输入纠错与磁颗粒验证指令.md`，Git blob `ef870d518362976cd984eac4d1d48d00c9aa767a`。本轮已读取的挂载文件与该blob一致。

本文件区分：项目返回事实、GPT本地算术/数学检查、外部API核对、下一轮授权。未运行的新任务不得写为完成。
研究目标始终是磁纳米颗粒在实际反射式iSCAT装置和同一提取程序下的尺寸关系；当前Fe3O4仍是文献均匀球、演示光路下的前向数值验证，不是实验标定。

## 0. 本轮裁决与调度

### 0.1 不能一概推翻，也不能整轮无条件通过

1. v063错误实数材料结果继续隔离；本轮材料源节点与v064 M2R的复数构造已与目标`2.349+0.083i`一致。不要再次按旧输入错误重算所有数据。[S02,S03,S05]
2. v064 60 nm均匀BEM表的三项截面相对误差算术通过，表报复远场指标也小于2%；保留其结果，不自动重求解。但是发布驱动仅显式保存T，原始复场/解的完整保存证据不足，不能宣称GPT已独立验算复场。[S03,S04]
3. M2P所发布的`local_mie_sections`不是有效球Mie独立参考：用了整数阶柱Bessel函数，还将MATLAB第三参数`scale`当作导数。**该参考实现不能用来签PASS。**实际运行如使用了另一份正确程序，须提供那份执行文件和日志，不能以摘要替代。[S02,E01–E03]
4. 材料守卫的负向夹具未穿过生产检查入口；哈希比较与参考比较有打印而无强制断言；常数/读回工程容差被改为1e-5或1e-9，未继承v064的1e-12。恢复合同并用真正的异常测试验证。不据此臆断当前材料数值已经错误。[S02,S03,S08]
5. 60 nm分层两焦面表报通过，保留为`REPORTED_PASS`。当前提交未发布其实际M3驱动、运行日志和必要材料/成像读回，不能据两行数字签完整证据。先复用已有576/1444系统补证和后处理，**不重跑BEM**。[S01,S06,S07]
6. 原v064授权9笔、报告消耗3笔，故剩余应是**2笔端点均匀＋4笔端点分层＝6笔**，不是笼统4笔。以工作站当前完成清单核对后扣除，不增加总体额度。[S01,S08]

### 0.2 连续执行顺序

```text
A：一次性核对身份/缓存/预算，修正材料与守卫
→ B：修复或恢复真正独立的Mie参考，零BEM验证
→ C：复用60 nm缓存补齐M2R/M3证据
→ D：30、100 nm均匀基准（各一笔，按各自门槛继续）
→ E：合格端点的生产/精细分层（每尺寸两笔）
→ F：三尺寸双焦面有符号响应表（零新BEM）
```

解析提取器补项、匿名续跑封装、发布检查及有余额的B2/P0无依赖任务可穿插执行。高内存BEM/完整矩阵任务始终串行。P0独立开放不自动阻塞未受影响的磁材料rule3路径。

前置满足、输入齐全、预算未耗尽时自动继续；失败只暂停其依赖分支。不要只修一条摘要就结束，也不要把“每步等GPT核查”当作停止理由。无法完成的项写实际阻断原因和可恢复检查点，不能默认PASS。

### 0.3 禁止改变的内容

- IDENTITY不变；不按例转置/翻转、共轭或自由幅相缩放择优。
- 不重建金球密模型，不重跑已通过B1十例或R2–R6批次；不新增金球统计样本。
- 金球1506e/1ms及其阈值、搜索域保持历史冻结状态；本轮无新相机批次，不将该配方移植为5000 fps实验曝光。
- 磁材料仍为520 nm、文献Fe3O4均匀球、μr=1的光学假设；不得改材料、壳层、间隙或照明去提高通过率。
- 均匀基准四项原门槛均`<0.02`；分层正式前向及原合同规定复场检查不放宽。
- blocked/unblocked完整三矩阵Frobenius各`<1e-10`，原rule7参考增量`<0.005`；不同门槛互不替代。
- 旧错误、失败与中断保留，修改后使用新完成键；不能只改报告把旧失败变PASS。

## 1. 本轮审查事实与证明范围

### 1.1 材料纠正与60 nm均匀表

当前分支已包含`Fe3O4_Querry.yml`，blob `37cd83a1ad859b18ddb8c6a515c29df78b2d95cb`；读取的源文件节点为0.5200 μm、n=2.349、κ=0.083，源引用年份1985。[S05]
M2R源码为`complex(nr,kap)`，不再是v063的实数相加。[S03]

完整M2R CSV经工具文本重建并核对Git blob一致后，本地复算结果如下：

| 指标 | 表报相对值 | 百分比 | 本轮实际复核范围 |
|---|---:|---:|---|
| raw complex L2 | 0.00391740599200391 | 0.3917405992% | 表值低于2%；未取得原复场重算 |
| 散射截面 | 0.00792456951862543 | 0.7924569519% | 由两侧截面原值复算一致 |
| 吸收截面 | 0.00420154476156196 | 0.4201544762% | 同上 |
| 消光截面 | 0.00535716004237431 | 0.5357160042% | 同上 |

原值（单位按原算法nm²，工作站仍须保存单位证据）：

| 截面 | BEM | 固定Mie |
|---|---:|---:|
| Csca | 73.2813697032347 | 73.866731754134 |
| Cabs | 163.41886737311 | 164.108376060877 |
| Cext | 236.700237076345 | 237.975107815011 |

三项误差的复算与原表差不超过1.2e-15，远小于判定余量。BEM截面代数恒等式残差约2.84e-13 nm²，只是代数检查，不新增独立物理证明。[S04]

### 1.2 M2P独立参考的确定问题

所发函数写的是：

```matlab
j1 = arrayfun(@(l)besselj(l,z1),ell);
d1 = arrayfun(@(l)z1*besselj(l,z1,true)+besselj(l,z1),ell);
```

按MathWorks官方API：`besselj(nu,z,1)`为指数缩放，不是求导；`bessely`同理。球Bessel为

\[
j_\ell(z)=\sqrt{\pi/(2z)}J_{\ell+1/2}(z),
\qquad [zj_\ell(z)]'=zj_{\ell-1}(z)-\ell j_\ell(z).
\]

因此不能把SciPy `spherical_jn(...,derivative=True)`的用法按名称直接移植到MATLAB `besselj(...,true)`。[E01–E04]

GPT本地按官方API语义模拟所发helper，在同一60 nm目标输入下得到约：
`Csca=3398.5963996379164`、`Cext=3398.596399637918`、`Cabs≈1.36e-12 nm²`。
正确球函数实现则给出：`73.86673175413364 / 237.97510781501106 / 164.10837606087742 nm²`。

这些是本地Python数学检查，**不是工作站MATLAB执行日志**。若工作站存在同名自定义Bessel函数，必须给出`which -all`和代码证据；不能假定有这种覆盖来解释摘要。所发M2R调用的是固定`miesolver`，不调用该local helper，所以helper错误本身不证明M2R边界解错误。[S02,S03]

M2P还存在：阶数6/8/12/16只打印10位有效数字，没有保存每阶全精度表或执行逐项收敛断言；独立参考差只打印，末尾无条件打印PASS。打印一致不是合同要求的数值断言。需修测试包装，不改作者Mie物理公式。[S02]

### 1.3 M3、发布与预算的真实缺项

- 两焦面表报分别为0.00527492053848303与0.00533721440382991，即0.5274921%与0.5337214%。两值不完全相同，不把摘要0.0053视作共同原值。[S06]
- 当前提交没有M3实际驱动和新运行日志；`numeric_inventory.csv`只说系统在工作站。该清单还存在2列表头与3字段数据行不一致。缺发布不等于缺工作站数据，更不等于计算失败，先恢复实际产物。[S01,S07]
- status的`prod_576_solve_s=576.0`和`fine_1444_solve_s=1444.0`恰为网格请求值。没有原计时证据不得采信为运行时间；不能反过来断言实际耗时绝不可能相同。[S01]
- 根`material_contract.json`仍是旧版本，保留1987、`2.349+0.0831i`及旧时间约定；不能与新读回共同当“已更新的同一合同”。旧件改标历史，新件正确引用。[S09]
- 目录树中的manifest仍为v063 blob，新YAML、新驱动/表没有由它完成v064覆盖；不得将旧清单称当前逐项核验完成。[S01]
- 摘要的`sha256="c91a8cde..."`是缩写，不可用于机器身份校验。完整哈希应从实际原始字节获得。[S01]

## 2. A：材料守卫、身份与缓存检查（零BEM）

### [放行条件]

实际工程根、来源YAML、固定上游和现有磁材料产物可定位。仅恢复当前缺失证据，不重复已确认的全工程检查，不干扰活跃计算。

### [必须实现]

**A1. 一个真正调用的入口。**建立经测试的`load_and_validate_material`或等价现有模块，由Mie、均匀BEM、分层BEM共同调用。不是三个脚本各抄一份正确常数。每次读回都与已核验源节点/不可变计划比较，不能只把对象与同一个潜在错误局部变量比较。

严格继承常数构造/读回工程容差`<=1e-12`。v064中的ε比较1e-5、n读回1e-9恢复为原值；这是恢复旧合同，不是新增更严物理指标。若原生读回达不到，保存全精度值和访问路径，先诊断，不再擅改容差。

输入与读回均至少保存：源文件完整SHA-256与blob、λ0_nm、λ_um、exact_node、n_real、kappa、eps_real、eps_imag、mu_r、host_n、D_nm、求解器/材料类路径与哈希、规则、计划ID。520 nm精确节点应优先匹配；不将恰好端点插值影响扩大为物理错误，但标记须与算法相符。

源blob不匹配必须抛出可识别异常，而不是只打印`match=0`。哈希工具用已知字节测试向量和另一可用原生工具交叉核对；不依赖未经验证的可变Java缓冲行为。旧散列实现只有风险待验，不据源码猜测就宣布其哈希一定错。

**A2. 真正的负向测试。**以下输入必须穿过与生产相同的验证入口，捕获预期异常ID，并断言BEM构造/求解回调调用次数为0：

| 夹具 | 注入方式 | 期望拒绝依据 |
|---|---|---|
| 旧实数相加 | `2.349+0.0831`作为对象输入 | n/κ与目标节点不符 |
| 丢虚部 | `complex(2.349,0)` | 吸收目标被变成无损 |
| 源身份不符 | 改一字节副本，原件不动 | blob/完整哈希不符 |
| 单位错 | `wavelength_um=520`与冻结`lambda0_nm=520`同现 | 显式单位换算或支持域检查失败 |
| 半径/直径错 | 不可变计划D=60，几何入口误传D/2作直径 | 计划、几何语义与实际构造参数不一致 |

最后两项必须依靠不可变计划/单位字段，不声称仅凭一个孤立数值就能推断用户真正意图。禁止用`assert(abs(imag(bad)-0.083)>tol)`代替捕获生产守卫异常。

**A3. 同时做发布一致性准备。**用正确新合同指向源YAML；历史合同保留并标记superseded。在实际检查成功之前，新任务validation保持NOT_EVALUATED。用数组和值生成状态，不另手填一个乐观版本。

### [失败处置与自动继续]

拒绝错误输入是测试预期，不扣BEM预算。验证器未拦截时不放行新BEM。允许本轮明确新增的最多2轮合并的“参考/材料守卫/驱动薄包装”定向修复，均记录diff和失败；旧修复计数不清零，不修改基线物理算法。
A通过直接B；M2R现有结果不因包装修复自动作废，但其新验收状态须引用实际材料来源证据。

## 3. B：独立Mie预检修复（零BEM）

### [放行条件]

A通过；固定上游`ce49f77f096337db8be54c46d83696d37b0b23d5`及实际运行路径确认。先恢复真正执行文件；若仅发布版本错误且运行版本可证，保留原历史执行结果并说明发布差异。

### [参考实现要求]

可直接使用上一轮附录中已给出的Python球函数参考；或在MATLAB中按半整数转换及递推求导。下列只是修复公式示意，不是已运行MATLAB测试的声明：

```matlab
sj = @(l,z) sqrt(pi./(2*z)).*besselj(l+0.5,z);
sy = @(l,z) sqrt(pi./(2*z)).*bessely(l+0.5,z);
ell = 1:lmax;
j1 = sj(ell,z1); j2 = sj(ell,z2);
h2 = j2 + 1i*sy(ell,z2);
d1 = z1*sj(ell-1,z1) - ell.*j1;
d2 = z2*sj(ell-1,z2) - ell.*j2;
dh2 = z2*(sj(ell-1,z2)+1i*sy(ell-1,z2)) - ell.*h2;
```

本范围z不为零；外向函数、时间约定、阻抗、直径和外介质归一化与已固定公式一致，不逐例选择共轭/符号。参考核不得调用正在验证的作者Mie系数函数，否则只算同路径重算。

### [必须执行的低成本检查]

1. 60 nm目标`complex(2.349,0.083)`、无损控制`complex(2.349,0)`、旧错误实数2.4321：固定Mie与正确参考分别运行。旧错误仅诊断，不重新生成BEM。
2. 目标Csca/Cext/Cabs均有限且相应非零项可分辨；独立实现逐截面相对差`<=1e-10`，作为本轮明确的数学参考交叉检查，不代替BEM的2%。
3. 阶数6/8/12/16全部保存17位有效数字。8→12、12→16每一非零截面相对变化`<=1e-10`；不以四行显示相同就判通过。
4. 無损控制用`abs(Cabs)/Cext<=1e-10`，Cext须有限非零；原Cabs不裁零。零参考的普通相对误差记null并说明专属判据，不能用realmin。
5. 30、100 nm目标在各自BEM前同样完成参考、阶数检查，不只检查60 nm就默认所有尺寸参考正确。
6. 故意注入旧helper输出或打乱返回截面，预检必须FAIL，且重计算队列不启动。每个对比有断言和机器汇总；禁末尾无条件打印PASS。

本轮本地球函数数学计算的对照量如下，仅用于调试定位，不可硬编码成结果或用来“校正”BEM：

| D/nm | Csca/nm² | Cext/nm² | Cabs/nm² |
|---|---:|---:|---:|
| 30 | 1.1141977267924494 | 19.141176078763127 | 18.026978351970676 |
| 60 | 73.86673175413364 | 237.97510781501106 | 164.10837606087742 |
| 100 | 1624.825729025211 | 2592.4202464128375 | 967.5945173876264 |

这些不是新BEM结果，也不是实验数据；独立实现仅在本任务的小尺寸、固定波长、无损外介质上使用，不宣称一般参数稳定性。

### [失败处置与自动继续]

参考失败时不新增目标BEM、不删吸收门槛，查API、路径和公式；与A共用最多2轮定向修复额度。B通过后，不要求重求已存在的60 nmBEM，直接C及D的合格任务。

## 4. C：60 nm已有成果补证，不重跑求解

### [C1：均匀结果]

先定位`v064_return/m2r_fe3o4_60nm/`实际文件与旁路缓存。所发驱动只显式保存T，不足以断言工作站肯定没有sol或farfield；实际查找并记录。

- 有原复场/权重：直接用同脚本独立重算raw复场相对L2，保存分子、分母、权重和shape。
- 只有已有边界解：重新计算远场属于后处理，允许；不重求解。
- 只有T且解/场全部无法恢复：保留`numerical_summary=PASS`和`evidence=PARTIAL`，写清不可独立复核的项。**本轮不授权重跑60 nm均匀BEM来补丢失证据。**B已正确通过后，30/100 nm均匀基准可按原计划执行，不把60 nm归档缺项当物理失败。

恢复读回与原执行源码的联系；若发现当轮材料/源码实际不符，升级为具体冲突并暂停受影响数据使用，不能仅凭现在正确的材料读回替历史签证。

### [C2：分层首例，扩批的必需前置]

取得真实执行的60 nm分层脚本/命令、原`prod576/fine1444`系统、材料和光路配置。恢复源文件，不为补发布编一份仿佛以前执行过的脚本。需要新后处理驱动时以v065新文件记录，输入仍是原系统。

以下字段均须直接来自实际对象/配置而非文件名：D=60、n/κ/ε、glass1.50/water1.33、gap5 nm、中心高度35 nm、λ0=520 nm、法向x偏振、玻璃侧NA1.3、物理像元65 nm、q5、IDENTITY；生产/精细角度/Bessel配置继承冻结预设。

两个焦面zf450/550、xy0的已有结果分别验收：

\[
r_C=\|C_P-C_R\|_F/\|C_R\|_F < 0.02
\]

中央41×41同ROI、同像元、同符号；保存分子/分母。按原合同在同方向/权重上比较散射复场，不能只给图像范数。原始场强保留`|Eref+Esca|²`，不能删除纯散射项或任意归一化。由同一数据导出的恒等式仅作代数检查。

先复用已有图或sol；补一次保存所需后处理，不重复同样BEM。没有原始计时则`solve_seconds=null`，不得用576/1444占位；不据两数恰相同就编造实际时间。

### [失败处置与自动继续]

C2完整性与原数值门槛通过，才允许端点分层扩批。若资料缺失，可继续D的均匀基准及其他独立工作；若C2实际数值失败，保留失败，停止分层扩批，不扩大网格或改光路。已有系统全部丢失时不得以此新增60 nm重求额度。

## 5. D/E：完成30与100 nm磁颗粒数值链（最多6笔）

### [正式计划，执行前冻结]

| plan_id | D/nm | 类型 | 网格请求 | 新BEM上限 | 直接前置 |
|---|---:|---|---:|---:|---|
| M2_D030_R1444 | 30 | 均匀水介质 | 1444 | 1 | A及该D的B通过 |
| M3_D030_P0576 | 30 | 玻璃/水分层 | 576 | 1 | C2与M2_D030通过 |
| M3_D030_R1444 | 30 | 玻璃/水分层 | 1444 | 1 | 同上，资源串行 |
| M2_D100_R1444 | 100 | 均匀水介质 | 1444 | 1 | A及该D的B通过 |
| M3_D100_P0576 | 100 | 玻璃/水分层 | 576 | 1 | C2与M2_D100通过 |
| M3_D100_R1444 | 100 | 玻璃/水分层 | 1444 | 1 | 同上，资源串行 |

先恢复当前完整且身份匹配的产物，匹配缓存不重算。待执行计划与本次分批大小无关。某尺寸均匀失败只停其分层，不取消另一个独立端点。60 nm分层前置未闭合时，两端点均匀可先完成。

### [D：均匀介质要求]

v064驱动硬编码diameter=60，不能把它直接标成“30/100脚本已就绪”。用同一参数化驱动接受冻结的D/计划对象，不用三份复制粘贴脚本。计算前检查输入、几何直径、缓存键和输出目录的计划ID一致；显式outdir也要先建立并检查可写。

维持1444/rule3，以及原普通/近邻/Duffy、照明和远场积分配置。每笔保存输入快照、实际网格、sol、eB/eM、dirRef/wRef、各截面和物理单位、原比较代码版本。

四项继续分别`<0.02`：raw complex L2、sca、abs、ext。参考分母必须有限、非零且可分辨后才做相除，不用realmin/epsilon补分母。四项都进布尔断言；任一FAIL不得在总状态变成PASS_WITH_TOOL_LIMITATION。

### [E：分层要求]

沿用C2的演示物理与数值设置：

- D30中心高度=5+30/2=20 nm；D100中心高度=5+100/2=55 nm，不能把它们当zf。
- 生产576/rule3；精细1444/rule3。生产角度50/51、Bessel2001；精细100/151、Bessel4001；实际记录不可省略。
- 每个系统复用至zf450/550；焦面与固定横向位置后处理不新增BEM。
- 每个D/z分别保存同ROI C及复场比较；不跨D采用不同照明强度或曝光。
- 若需在公共角度上比较复远场，使用各自已有边界解重新后处理；不得把不同采样数组硬比较或任意相位对齐。

### [失败处置]

求解发生即记成本。真正的物理门槛失败先检查已有数组、索引、读回与配置；本轮没有追加更大网格、额外补点或BEM重试额度。只有保存/导出中断且原解可恢复时续作后处理，不第二次求解。

### [自动继续]

每个计划完成立即保存检查点并触发已满足的下一计划，不逐笔等GPT。若会话必须结束，交当前实际断点和运行身份；不能用无时间依据的“预计完成”代替结果。

## 6. F：把三尺寸验证组织成研究可用的前向结果（零新增BEM）

### [放行条件]

相应尺寸分层产物及原门槛已通过。全部三尺寸通过时形成6个D/z条件表；未全通过时只列实际合格与失败，不插值补齐。

### [本轮明确新增的轻量后处理定义]

在现有三尺寸双焦面图上，除了保存完整有符号C，统一导出下列探索描述量（不称真实实验提取器）：

1. `C_center`：实际坐标x=y=0所在物理像元的有符号C；没有该像元则按预先声明坐标规则处理并记录，不寻找最亮点替代。
2. `S_area_nm2 = (65 nm)^2 * sum(C over central 41x41)`：明确是有面积单位的积分对比度，不与无量纲峰值或原始强度和混用。
3. 原生产/精细误差、焦面、材料、像元、ROI、函数/系统身份。

两个描述量可能接近零；其相对误差近零时标NOT_DEFINED，另报绝对差，不临时改指标签PASS。它们不新增自动放行门槛，正式门槛仍为原全图/复场检查。

输出`magnetic_response_three_sizes.csv`与6组数组清单，说明同D不同zf下响应变化。禁止三点强拟合D³或宣称连续单调/唯一反演。三尺寸比较目的是确认目标材料前向响应及数值误差，而不是立即估计未知实验粒径。

下一轮细D建库、留出与相机噪声设计将依据这些真实响应与实际提取器定义决定；本轮不授权新密D扫描或统计批次。

## 7. 其他已授权支线：继续完成，但不得挤掉磁材料主线

### G1. 解析提取器与实验合同

v064目录保留了v063同blob的16行解析表，不能说补项已执行。先恢复真实生成脚本及其记录；未找到则明确缺失。

按v064第6节完成仍未执行的四项：400 Hz非整频点有限和/FFT；100 μs中心曝光数值积分；开始曝光时标的相位；近零指标null序列化。Fs5000/N2001/k160和100 μs是解析夹具，不是实际曝光确认。原非零相对1e-10、近零绝对1e-12保持。

在真实实验提取器尚未定位时，标ANALYTIC_REFERENCE_ONLY；65 nm/41×41/q5留在合成合同，不能写成已测仪器参数。按已有具体文件名/路径进行有界检索，不无止境扫盘；有真实源码就恢复其实际字段、编码、时标、背景与归一化，不用参考实现冒名替换。

### G2. 薄封装与旧记录恢复

用伪记录而非新相机数据测试：先5再到100不改变计划ID；相同任务重复启动不重算；已完成fit加载进汇总；临时/损坏文件不作为完成；匿名估计输入不含真值命名路径；失败分母保留。

v064继续保留旧`future fixed`说明不代表功能已实现。提供实际驱动与测试日志。旧R5最多4个seed重建只在原输入/程序可确证时执行，标`DETERMINISTIC_RECONSTRUCTION_NOT_ORIGINAL`，不能恢复成历史原帧或增加独立样本量。

### G3. B2与P0

继承v064尚未消耗额度，不因本版本重置。

- B2：最多32份已有观测诊断；必要时最多4份、每份21个zf域内profile。保持原zf/xy域和阈值；profile不是简单slice，也不是已校准置信区间。
- P0局部：保存数组优先补SL/DL相对Frobenius。只能用正确参考和完整分子/分母签局部门槛；若无数组且原余额允许，补有限小例，不反复触发已知Npair=1失败。
- 完整direct/reflected/total各`<1e-10`仍OPEN；先贡献/索引/权重/规则审计，未建立原因不能先写“纯浮点”。
- Hook须命中实际duffy1/eval2，记录路径/次数/危险分配前shape；没命中记TARGET_PATH_NOT_REACHED。
- 局部回归、全覆盖、资源与三矩阵门槛全部通过后，才可使用原最多1笔D35.5/1444/rule7条件额度，原0.5%增量不变。不得与磁材料高内存BEM并发。

若P0发现实际污染磁材料rule3共享实现，按影响暂停；单纯P0未完成不使磁任务自动停摆。

## 8. 预算与停止规则

### [BEM账本]

v064合同授权9笔：纠正60均匀1、端点均匀2、全部分层6。v064报告已用：纠正60均匀1＋60分层2＝3。因此按该报告余额为6。

| 项目 | 本轮上限 | 是否新增授权 |
|---|---:|---|
| 30/100均匀 | 2 | 否，原余额 |
| 30/100分层生产/精细 | 4 | 否，原余额且逐尺寸有门槛 |
| 60均匀/分层重求 | 0 | 不授权 |
| 新金球/磁颗粒噪声批次 | 0 | 不授权 |
| 额外D、波长、间隙或网格扫参 | 0 | 不授权 |
| P0 rule7参考 | ≤1 | 原独立条件授权；全部专属门槛通过才执行 |

若工作站存在未在v064摘要反映的已消费求解，应扣除并解释差异；不能以旧摘要总是3为由多启动。历史v063错材料1笔不消失：若当前任务全部完成，磁材料探索累计成本仍最多10笔（含旧错误1笔）。

本轮明确新增：A/B/薄包装最多2轮定向修复；F的6条件轻量描述量导出。没有新增BEM额度。任何失败求解均扣预算，不用“无有效成果”把消耗归零。

### [停止边界]

无可追溯源、参考错误、冻结参数被改变、需要新大预算或门槛调整时暂停受影响分支。其他无依赖且已授权任务继续。不得用文件存在代替身份验收；不得用“目前无错误字符串”代替数值正确。

## 9. 最终交付与机器发布检查

只交一个`iscat_v065_return.zip`，保留一个可读汇总入口。GitHub公开发布遵守既有隐私边界，不新公开真实实验原帧、个人数据或凭据。

建议目录：

```text
00_Codex_v065_参考实现修复与三尺寸磁颗粒验证指令.md
00_本轮文本汇总.md
status.json / review.md / decisions.json / budget_ledger.csv
contracts/
  material_contract_v065.json
  synthetic_observable_contract.json
  experimental_observable_contract.json
materials/Fe3O4_Querry.yml + source_record.json
source/
  真正执行的材料加载、守卫、Mie参考、参数化均匀/分层驱动
  数值评估、聚合、薄封装、解析测试及父版本diff
logs/
  实际命令、运行路径、守卫、阶数、数值比较和失败日志
numeric/
  首例必要完整数组、端点比较数组、所有失败证据
  其他大缓存索引（path/variable/shape/dtype/axes/hash/是否随包）
tables/
  material_runtime_checks.csv
  guard_negative_tests.csv
  mie_preflight_full_precision.csv
  magnetic_homogeneous_checks.csv
  magnetic_layered_checks.csv
  magnetic_response_three_sizes.csv
  wrapper_tests.csv / task_status_current.csv
  其他实际执行的支线表
inventory.csv / manifest_sha256.csv
```

发布前强制：

1. 每个PASS指向实际值、比较符、阈值、来源和正确执行文件；错误Mie参考、缺失场数组或未运行不能被聚合成整体PASS。
2. execution/validation/evidence分开；允许数值摘要PASS但证据PARTIAL，不允许改写为GPT全数组独立验证。
3. `material_contract_v065`、运行对象和结果表的n/κ/ε/单位一致；真实负向夹具可让机器检查失败。
4. 不保留误导性旧根合同/总账作为现行入口；历史文件保留但指针明确。任一新驱动/JSON/CSV缺失就不得称该证据COMPLETE。
5. CSV每行字段数与表头相同；所有数值全精度；未定义/未执行用null及原因，不能变0；JSON不输出NaN/Infinity。
6. `solve_seconds`只能来自计时证据；没有则null。导出日期保留原时区/工作站来源，不由GPT当前日期推断或改写。
7. manifest从最终发布字节重新算。区分Git blob、SHA-256、LF与CRLF口径；发布后对关键小文件复读并核对。旧manifest未更新不是数值篡改证据，但不能用于新包通过声明。
8. 原v063错材料结果保留隔离，不能成为30/60/100目标材料缓存。

## 10. 来源、外部核验与本轮工作范围

### 固定v064项目来源

- S01：`status.json` / `review.md` / 完整Git目录树（truncated=false），固定提交见页首。
- S02：`source/run_v064_m1r_m2p.m`，blob `7ac253e92a44d598e1c12950d9b7b20c01cc3351`。
- S03：`source/run_v064_m2r_fe3o4.m`，blob `e9894aea3350cd95f28e5ae82d8c3702a773c6e5`。
- S04：`tables/m2r_fe3o4_60nm_results.csv`，blob `1938c4959e731c93e05c18d2738491027afca771`。
- S05：`Fe3O4_Querry.yml`，blob `37cd83a1ad859b18ddb8c6a515c29df78b2d95cb`；本轮读取源引用与工作点段落，不宣称重新解析全612点。
- S06：`tables/m3_D60_forward.csv`，blob `2c8741a13b162691b21e522f7a659274b7f96442`。
- S07：`numeric_inventory.csv`，blob `abfd1d8ce2ac0a522b27ae86563a7daba3f4a8f6`。
- S08：上一轮v064指令，blob `ef870d518362976cd984eac4d1d48d00c9aa767a`；本轮全文读取，尤其材料1e-12、四项2%、缓存、预算与交付合同。
- S09：当前根`material_contract.json`，blob `a2998d741a84216f07f76140358e8c9441b04719`，仍为v063旧合同。

### 本轮额外核对的官方资料（不是项目执行证据）

- E01：MathWorks `besselj`：第三参数scale=1为指数缩放，非导数。
- E02：MathWorks `bessely`：同样的scale参数语义。
- E03：NIST DLMF §10.47、§10.51：球Bessel与半整数柱Bessel的关系及导数递推。
- E04：SciPy `spherical_jn`官方文档：此API的derivative=True才表示导数。

```text
https://www.mathworks.com/help/matlab/ref/besselj.html
https://www.mathworks.com/help/matlab/ref/bessely.html
https://dlmf.nist.gov/10.47
https://dlmf.nist.gov/10.51
https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.spherical_jn.html
```

本轮实际完成：固定提交阅读；M2R和M3小CSV工具文本重建并核对blob；截面误差复算；正确球函数实现与半整数/递推实现交叉检查；按官方API语义模拟错误helper；读上一轮实际合同。没有运行MATLAB/BEM、没有核验工作站进程或所有原始数组，没有完成新的磁颗粒实验。

## 附录A：本轮本地审查代码（非工作站运行结果）

下列代码是GPT本轮实际运行的审查辅助。不要把它当作BEM/实验采集执行器；MATLAB修复仍须本机实际测试。输出的端点数值只作Mie数学核对。无需为了使用此代码而升级主工程环境。

```python
"""Read-only local audit: published table arithmetic and two Mie formula implementations.
No MATLAB, BEM, workstation access, or acquisition is performed.
The v064 helper is emulated using the documented MATLAB besselj/bessely API.
"""
from pathlib import Path
import csv, hashlib, io, json, sys
import numpy as np
import scipy
from scipy.special import jv, yv, jve, yve, spherical_jn, spherical_yn

ROOT=Path(__file__).resolve().parent
M2='''mesh_request,lambda_nm,material,raw_complex_relative_L2,BEM_sca,Mie_sca,sca_error,BEM_abs,Mie_abs,abs_error,BEM_ext,Mie_ext,ext_error,passed
1444,520,Fe3O4_complex_2.349+0.083i,0.00391740599200391,73.2813697032347,73.866731754134,0.00792456951862543,163.41886737311,164.108376060877,0.00420154476156196,236.700237076345,237.975107815011,0.00535716004237431,1
'''
M3='''zf,relL2,gate2pct
450,0.00527492053848303,1
550,0.00533721440382991,1
'''
def blob_id(b: bytes)->str:
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\x00'+b).hexdigest()
assert blob_id(M2.encode()) == '1938c4959e731c93e05c18d2738491027afca771'
assert blob_id(M3.encode()) == '2c8741a13b162691b21e522f7a659274b7f96442'
(ROOT/'m2r_fe3o4_60nm_results_source.csv').write_text(M2,encoding='utf-8')
(ROOT/'m3_D60_forward_source.csv').write_text(M3,encoding='utf-8')

def sections(np_:complex,d:float=60.0,lam:float=520.0,nh:float=1.33,L:int=12,mode:str='spherical'):
    assert np.isfinite(np_.real) and np.isfinite(np_.imag)
    assert d>0 and lam>0 and nh>0 and L>=1
    k0=2*np.pi/lam; k1=k0*np_; k2=k0*nh
    z1=k1*d/2; z2=k2*d/2; Z1=1/np_; Z2=1/nh
    ell=np.arange(1,L+1)
    if mode=='v064_helper_api_emulation':
        j1,j2=jv(ell,z1),jv(ell,z2)
        h2=j2+1j*yv(ell,z2)
        d1=z1*jve(ell,z1)+j1
        d2=z2*jve(ell,z2)+j2
        dh2=z2*(jve(ell,z2)+1j*yve(ell,z2))+h2
    elif mode=='spherical':
        j1,j2=spherical_jn(ell,z1),spherical_jn(ell,z2)
        h2=j2+1j*spherical_yn(ell,z2)
        d1=j1+z1*spherical_jn(ell,z1,derivative=True)
        d2=j2+z2*spherical_jn(ell,z2,derivative=True)
        dh2=h2+z2*(spherical_jn(ell,z2,derivative=True)+1j*spherical_yn(ell,z2,derivative=True))
    elif mode=='half_integer_recurrence':
        sj=lambda order,z: np.sqrt(np.pi/(2*z))*jv(order+0.5,z)
        sy=lambda order,z: np.sqrt(np.pi/(2*z))*yv(order+0.5,z)
        j1,j2=sj(ell,z1),sj(ell,z2); h2=j2+1j*sy(ell,z2)
        d1=z1*sj(ell-1,z1)-ell*j1
        d2=z2*sj(ell-1,z2)-ell*j2
        dh2=z2*(sj(ell-1,z2)+1j*sy(ell-1,z2))-ell*h2
    else:
        raise ValueError(mode)
    a=(Z2*z1*j1*d2-Z1*z2*j2*d1)/(Z2*z1*j1*dh2-Z1*z2*h2*d1)
    b=(Z2*z2*j2*d1-Z1*z1*j1*d2)/(Z2*z2*h2*d1-Z1*z1*j1*dh2)
    sca=2*np.pi/k2**2*np.sum((2*ell+1)*(np.abs(a)**2+np.abs(b)**2))
    ext=2*np.pi/k2**2*np.sum((2*ell+1)*np.real(a+b))
    return {'Csca_nm2':float(sca),'Cext_nm2':float(ext),'Cabs_nm2':float(ext-sca)}

row=next(csv.DictReader(io.StringIO(M2)))
errors={}
for channel in ('sca','abs','ext'):
    calculated=abs(float(row['BEM_'+channel])-float(row['Mie_'+channel]))/abs(float(row['Mie_'+channel]))
    reported=float(row[channel+'_error'])
    assert abs(calculated-reported)<1e-12
    errors[channel]={'recalculated':calculated,'reported':reported,'difference':calculated-reported,'pass_2pct':calculated<.02}
output={
 'audit_kind':'LOCAL_ARITHMETIC_AND_SPECIAL_FUNCTION_CHECK_ONLY',
 'commit':'188e2718a54c1f3812b17379917d947c686d6cd9',
 'runtime':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__},
 'table_blobs_confirmed':{'M2':blob_id(M2.encode()),'M3':blob_id(M3.encode())},
 'M2_cross_section_error_check':errors,
 'M2_BEM_identity_residual_not_independent_validation':float(row['BEM_ext'])-float(row['BEM_sca'])-float(row['BEM_abs']),
 'M3_reported_relL2':[float(r['relL2']) for r in csv.DictReader(io.StringIO(M3))],
 'correct_mie_at_60':sections(2.349+0.083j),
 'v064_helper_under_matlab_api_emulated':sections(2.349+0.083j,mode='v064_helper_api_emulation'),
 'correct_order_checks':[],
 'planned_endpoint_mie_only_not_BEM':{},
}
for d in (30.,60.,100.):
    a=sections(2.349+.083j,d=d)
    b=sections(2.349+.083j,d=d,mode='half_integer_recurrence')
    for key in a:
        assert abs(a[key]-b[key])/abs(a[key])<1e-10
    output['planned_endpoint_mie_only_not_BEM'][str(d)]={'spherical':a,'half_integer_recurrence':b}
for L in (6,8,12,16):
    output['correct_order_checks'].append({'L':L,**sections(2.349+.083j,L=L)})
for channel,key in [('sca','Csca_nm2'),('ext','Cext_nm2'),('abs','Cabs_nm2')]:
    err=abs(output['correct_mie_at_60'][key]-float(row['Mie_'+channel]))/float(row['Mie_'+channel])
    assert err<1e-10
output['remaining_budget_arithmetic']={'v064_authorized':9,'reported_used':3,'remaining_under_reported_ledger':6,
   'remaining_homogeneous':2,'remaining_layered':4,'need_additional_experimental_or_gold_batches':False}
(ROOT/'audit_results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps(output,ensure_ascii=False,indent=2))
```

**接续结论：保留正确材料60 nm的已报数值成果，先用零BEM方式修参考/守卫并恢复分层证据，再连续完成原有六笔端点任务。三尺寸真实返回后再决定建库与实验接入，不重跑金球，不跳过吸收，不把摘要PASS等同完整可复现。**
