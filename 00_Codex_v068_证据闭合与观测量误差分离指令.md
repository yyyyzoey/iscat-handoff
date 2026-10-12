# iSCAT v068：v067审查裁决、证据闭合与观测量误差分离

> 执行：Codex；审查与后续决策：ChatGPT。
> 本轮审查固定提交：`yyyyzoey/iscat-handoff@9a533f637318eb6c210bb7f428cff70d1397593a`（v067）。
> 本文件是下一轮执行授权，不是新MATLAB/BEM结果。审查端只完成文本、Git blob、CSV结构与D3标量算术核查；未运行工作站求解器。
> 最终目标仍是实际反射式iSCAT中磁纳米颗粒的观测量—粒径关系。当前文献Fe3O4、均匀球、演示光路只是 `LITERATURE_MATERIAL_EXPLORATION`，不签实验标定、绝对粒径、连续域或检出率认证。

## 0. 总令：保留已完成求解，不再让导出错误导致反复计算

完整阅读后，连续完成所有前置满足、输入齐全、资源允许且在预算内的任务，不必每一步停下等GPT。失败只暂停有真实依赖的分支，保留原证据，继续其余任务。不得修改冻结门槛、选择更有利的方向/样本/孔径/相位来取得通过。

本轮磁材料新增BEM授权为 **0笔**。v067已报告完成的30/100 nm均匀解与旧60 nm正确均匀解优先恢复。没有新D、材料、波长、间隙或全密库扫描；不启动新相机/噪声批次。

```text
A  先用小型数据通过保存—导出—读回—断点测试；核实运行/缓存身份
B  从已保存端点均匀解导出原四项全精度验收，禁止重求BEM
C  修复27条件、孔径长表、D3的结构化归档，恢复原数组与同一评分入口
D  六个预先确定的关键条件：公共后处理对照＋三个单因素精细侧增量
E  形成按观测量区分的误差解释与下一阶段入口；其余旧支线有限继续
→ 单一结果ZIP，完整可读文本、必要数值及真实发布清单，统一交GPT
```

C可与B独立恢复；B某个原始数组缺失不等于物理失败。共享材料/场景身份冲突则暂停相关使用。D需要C中的源对象与基准指标可追溯，不得建立在损坏CSV之上。

## 1. 必须采用的v067审查裁决

### 1.1 保留真实进展与正确改动

1. `run_v067_comprehensive.m`的B段明确使用 `galerkin.bemsolver`、原点球、`BoundaryEdge([mw,mp],p,[2,1])`、均匀水n=1.33，无玻璃层对象；不再是v065仅把同一分层配置命名为homog。[S03]
2. 原生日志报告D30、D100两项完成，复远场/散射/吸收/消光四指标均低于0.02；当前可读值只有四位小数，不伪造未提供的有效数字。该驱动保存了 `sol, fm, bs,as,ba,aa,bx,ax,es,ea,ex,passed`，因此先读取已存MAT做全精度导出，不重新求解。[S03,S05]
3. C段已经使用展平像元L2：`norm(P(:)-R(:),2)/norm(R(:),2)`。保留这一正确修复。日志有27个D/zf条件的rF和闭合检查，报告rF约0.0051—0.0069，全小于0.02。[S03,S05]
4. 场分解在代码层面先计算子像元强度/干涉项，再调用pixel_mean；这是正确方向。但pixel_mean/实际输出场布局和真实权重仍需随包解释；闭合只检验同一数据的代数一致性，不是独立Maxwell准确度证明。[S03]
5. D3 JSON提供了可解析的细分采样表。保留其已报告符号与采样区间；表值已舍入，不把由其插出的多位小数当作高精度物理零点。[S06]

### 1.2 27条件主CSV在仓库中确实损坏，不是显示问题

审查端从连接器原文重建UTF-8文件并验证：

- 文件：`tables/v067_27condition_full.csv`。
- 字节数：6332。
- Git blob：`3b50bc8e2c7dbbe4b09eb9fcd97735f1c1e2aef4`，与固定提交完全相同。
- SHA-256：`0b5e2f45d554036d5ec029ee53056eea5038f56f0256dcfa8b2d9ed15611eed3`。
- 用标准CSV解析器（不是splitlines猜测）得到表头21字段，但数据仅21条记录，不是27条；20条有21字段，最后1条只有6字段。
- 含2个U+001E、7个U+0001控制字符；多条记录开头已是上一个条件的数值。仅7条记录的前两个字段符合原D/zf键集合；这不代表这7条整行都合格。
- `apertures_1…6`不是可用的孔径记录。[S04]

**裁决：**主CSV发布/结构验收FAIL；不能从该文件签“27条完整原数据已复验”。保留源码改动和日志中的PASS_REPORTED，物理验收与归档验收分开。不得按数值猜测跨行拼接并将“修复后表”当原生数据。必须从MAT、原图、原场或原sol重新导出。

原代码把6元素结构数组`aps`嵌入每条主记录后直接writetable；这是需要在I/O最小实验中隔离的风险。尚未执行原生最小实验前，不能把损坏的全部原因绝对归给某一MATLAB函数或编码环节。[S03,S04]

### 1.3 D3导出实现仍有确定的问题

两个发布驱动均将D60记录的 `C_center_prod/C_center_fine` 与D100记录的 `S_area_prod/S_area_fine` 放进同一个cell，然后使用 `[refine{:}]` 拼结构数组。两类结构字段集合不同。MATLAB官方要求结构拼接具有相同字段集合；因此发布代码不能作为该混合CSV成功导出的依据。[S03,S07,E01]

提供的JSON由哪份实际脚本导出尚未说明。日志止于 `未找到变量 '; s'` 的警告，而发布源文件相应load用的是 `'s'`；只说明运行/发布源码身份需核对，不推断具体操作或伪造历史。实际存在的JSON并不因此自动无效，其来源和舍入精度单独恢复。[S05,S06,S07]

D3 JSON的D60 `linear_interpolation_zf=514.7316784869977`，旁边note却写约514.2 nm；订正文案应由相同数值自动生成，不手填。

### 1.4 当前能够核对的D3结果及其边界

JSON文本重建为6239字节，Git blob `41fbea783e1f66e7b787a956330925f85b92965a` 完全匹配。包含D60 11条、D100 18条（后者混有旧九焦面及局部细分点，不是18笔新BEM）。从已舍入数字复算：

| 量/侧 | 直接表报变号括区/nm | 线性插值诊断/nm |
|---|---|---:|
| D60中心，生产 | 512.5—515 | 约514.73 |
| D60中心，精细 | 512.5—515 | 约514.49 |
| D100的41×41积分，生产 | 425—427.5 | 约425.94 |
| D100的41×41积分，精细 | 435—437.5 | 约436.99 |

这些是对源表数字的算术，不是新增render、真实零点求解、置信区间或D误差。[S06]

更重要的直接数值：

- D100/z435：S_P=-613.07、S_R=+143.38 nm²，差的绝对值756.45 nm²，符号已不同。
- D60/z515：C_P=0.000227、C_R=0.000429，绝对差0.000202，对精细侧的相对差约47.09%。

这不增加“所有标量相对误差必须<2%”的事后门槛，也不自动否定整图PASS。它说明不能仅凭整图<2%宣称零附近标量稳定。P/R零点不同不能单独证明孔径依赖、吸收因果或某一积分算法错误；必须读取真正的多孔径和受控增量数据。

### 1.5 D1/D2不能仅凭闭合和主表均值宣布完整通过

- 代码的 `Cs_*_mean/Cint_*_mean` 是整张图的均值，而 `S_area_*` 是41×41积分。两个区域不能混用来解释该孔径的零点。
- 代码仅计算了生产侧S_plus/S_minus，未完整输出精细侧的正负项、抵消因子和原规定逐孔径分解；当前坏表中也没有有效孔径数值。因此“孔径数据全捕获”只能保留为运行报告，不能作为已审查162组孔径结果。
- 代码的closure是归一化最大绝对差，分母带max(1,…)；原v067合同是范数和归一化。两者都可保留，但不能改名当同一门槛。应从已有数组补算原指标 `||C-Cs-Cint||_2/(||C||_2+||Cs||_2+||Cint||_2)`，零总范数单独处理。只补计算，不重求BEM。[S03,S08]
- 当前仓库没有numeric目录中的原图/复场包。numeric_inventory只是工作站目录说明；源码没有显示每个render的落盘。先查实际缓存，不预判工作站必定丢失，也不能将工作站“有目录”说成原数组已经随包。[S02,S09]

### 1.6 运行有效性和旧缺项不能被新版本抹去

源代码只根据isfile跳过均匀任务，没有重新核验缓存身份/原passed；计算passed后也没有有效阻止不合格数据进入后续“通过汇总”的公共机制。材料读回仍使用1e-9，而前轮工程合同为1e-12。正确材料的当前日志不因此改判物理FAIL，但工程守卫不能写COMPLETE。[S03,S08]

日志含D30四条start、D100一条start，但只有两条完成记录。不得把5条start全当5笔成功求解，也不得忽略可能的失败成本。恢复真实run、错误、sol与计时范围；当前39秒计时从`bem\exc`开始，不包含其前面的构建，不能直接与早期整段计时比较后推断性能异常。[S03,S05]

## 2. A：先修保存与表结构，用小型夹具实际证明

### [放行条件]
核对工程根和当前进程；只调用明确路径，不对全部历史包做genpath。高内存任务串行，不按旧PID盲杀。保存父源码与完整差分。

### [必查项与实现要求]

1. 先在独立新目录用合成小数组测试I/O，不运行BEM，也不先重做45个render来测试导出。
2. 采用三张平表，全部列是标量数值、逻辑或简单字符串：
   - `primary27.csv`：27行，D/zf键唯一，P/R数值列分开；六条件摘要从这张表筛选。
   - `aperture162.csv`：27条件×6孔径=162行；每行有D,zf,ap和两侧量。不要把6元素struct写进一个CSV单元；支持不足的孔径也保留记录和reason。
   - `refinement18.csv`：原授权18个新焦面点；通用观测字段或分别两张各9行表。原端点从primary27引用，不再次计算。直接采样与插值根采用不同表。
   - 需要对全部45个条件导出孔径时为270行，不与162行累计成新样本。
3. 结构数组在MAT中保存可以保留嵌套；CSV只写明确扁平表；JSON可使用对象数组保存异构数据。JSON生成器和源字段必须随包，不从格式化打印日志恢复正式精度。
4. 每个条件得到数组后立刻保存临时MAT/NPZ及身份；可读回后原子提交。数组保存先于可失败的CSV/绘图。只在同目录使用原子替换，失败保留临时文件，不覆盖旧成功结果。
5. 断点入口加载已有数组并重新评分/归约，不能遇到记录就continue而漏进总表；也不能因导出失败重新BEM或重新render已有条件。
6. 守卫是生产真的调用的入口：材料源、n/κ/ε、D直径/单位、场景、轴、配置hash、实际对象readback。沿用1e-12常数构造与读回；失败记录真实差值，不静默放宽。
7. 验收三元组分开：execution、validation、evidence。汇总PASS必须依赖所有指定数值及有效前置；结果文件存在不是PASS。

### [必做负向测试]

- 原始v067损坏CSV：必须被拒绝；行数、键集合、类型、控制字符分别有检查，不只看21列。
- 布尔字符串False必须按False解析；不能用字符串非空性。
- 数值NaN/Inf、零参考范数、缺键、重复键、源hash错，必须阻止正式PASS。
- 谱范数反例仍用旧固定夹具，正式Frobenius门槛必须拒绝。
- 两类不同字段的D3记录在新格式下可无损写入读回。
- 模拟“已有数组保存成功、导出失败、重启”：只补导出，BEM/render计数均不得再次增加。
- 模拟“缓存存在但passed=false或物理身份不符”：不可被当成功缓存继续。
- 以合成标量模拟nm/μm及半径误传，证明实际入口拒绝，不用真实求解测异常。

给出真正测试脚本、预期异常、调用计数与运行结果，不能只有README里的future fix。包装/I/O本轮明确授权最多2轮有记录修复；额度是新增有限授权，旧账不清零。超出则保存最小失败复现，暂停依赖导出的扩展。

## 3. B：已完成均匀基准的零BEM验收闭合

### [放行条件]
找到v067 D30/D100保存的真均匀MAT及v064正确D60结果；实际路径/父源码可核查。没有某个字段不自动宣布整个求解失败。

### [必查项]

- 从sol/tau和已保存标量确认真实无界水n=1.33、D=30/100、粒子n=2.349+0.083i、λ0=520、μr=1、均匀Galerkin、实际网格、原规则与照明。不能只使用文件名或现在新建的独立材料对象给旧解签证。
- 读取已保存 `bs/as/ba/aa/bx/ax/fm` 全精度重算三个截面误差；四项均保持<0.02。报原值、单位、分子、分母和门槛，不把日志0.0039伪装成未舍入数。
- 原eB/eM未保存但sol存在时，在原`sphere_rule(48,97)`上重算远场是后处理，允许各一次；明确无新求解。保存eB/eM、方向、权重、各自场规范和未经自由对齐的复远场指标。
- 验收作者固定Mie与此前正确独立Mie：已有可追溯零BEM全精度结果就导出；确实缺失才运行原三尺寸×6/8/12/16预检，不写第三套Mie。
- 无损控制另用旧零吸收判据；可分辨的非零目标参考不允许realmin替换分母；无效参考应该触发数据异常。
- BEM守卫/四项判定/证据完整性分别聚合。
- 原日志D30重复start逐个说明：attempt/run/source/阶段、是否求解实际发生、输出、失败原因。未知记UNKNOWN，不能虚报成功数或抹去失败成本。

输出 `true_homogeneous_four_gates.csv`、端点公共远场数值证据、`solve_ledger.csv`。若原sol确实无法恢复，本轮不追加BEM，保留摘要PASS_REPORTED、证据PARTIAL，说明确切缺项；允许其他独立零BEM任务继续。

## 4. C：恢复45条件归档，代数与孔径必须同区域同源

### [计划与放行条件]
先恢复已有图/场/sol。原主条件27个：D=30/60/100，zf=375:25:575。原局部补点18个：
- D60：502.5,505,507.5,510,512.5,515,517.5,520,522.5；
- D100：427.5,430,432.5,435,437.5,440,442.5,445,447.5。
共45个唯一D/zf，不增加新的焦面点。旧D3脚本的500/525端点从27表复用；不要以“11+9”重新计算已存在端点。

### [C1 数值评分]

所有表来自同一个已测试评分函数。展平L2与Frobenius一致，谱范数为独立诊断列，不参与原门槛。每行保存差范数、参考范数、原门槛结果、图hash、函数hash、ROI和参考侧。六条件摘要严格筛选自27行，禁止单独手写另一循环。

从现有sol重做公共方向的散射复场比较，补原<0.02门槛；不得将不同方向数组直接相减、逐例共轭、旋转、相位对齐或幅值拟合。

源图有限性、I0>0、物理像元65 nm、q5、行camera_x/列camera_y、IDENTITY和玻璃侧收集配置均要实际核验。读回存储轴不等于允许物理方向择优；不重新做旧哨兵BEM。

### [C2 同源场强分解]

沿用原积分算子P_j：

I0_j = P_j(||Er||²)
Cs_j = P_j(||Es||²)/I0_j
Cint_j = P_j(2 Re(Er*·Es))/I0_j
C_j = Cs_j + Cint_j

保存原C、Cs、Cint、I0和坐标。先对子像元形成强度，再按实际权重积分；不能平均场后平方。检查原pixel_mean与render_system的权重、shape、复共轭和向量轴一致，所需helper必须随包。

原工程闭合量为：
`closure_F = norm(C-Cs-Cint)/[norm(C)+norm(Cs)+norm(Cint)] <= 1e-12`（均展平向量2范数）。全零情形单列绝对残差。旧最大值闭合公式单列 `closure_Linf_diagnostic`，不能改名代替。

对相同孔径和相同中心还要验证 `C_center=Cs_center+Cint_center`、`S=S_s+S_int`。不能用65×65全图均值解释41×41积分；输出每个空间支持范围。

### [C3 孔径与条件性]

固定边长[21,31,41,51,61,65]，原41×41门槛不变。对P/R分别保存：
- S_plus、S_minus、S_total、S_scattering、S_interference；
- sum_abs_C、sum_C、像元面积与像元数；
- chi=sum_abs_C/abs(sum_C)；K2=sqrt(N)*norm(C)/abs(sum_C)；
- 两侧差与邻孔径变化。

0或算术不可分辨的分母给null和reason，不用epsilon/realmin掩盖。原v067约定的64*eps*sum_abs只作算术标记，不是实验噪声或粒径门槛。非零但相对不稳定的数值照实保留。

代数闭合不等于物理准确。不同孔径确有变化才报告孔径依赖；两种网格有不同根不能单独证明孔径敏感。干涉项不能叫吸收项，本轮不做改κ的因果控制求解。

### [C4 D3与精度]

恢复实际生成JSON的脚本及未舍入采样值。没有未舍入值则标精度来源；不从6位小数推导14位可信根。直接样本标DIRECT_RENDER_REPORTED/VERIFIED_SOURCE，插值结果独立标INTERPOLATED_NOT_DIRECT_ROOT。根表记录来自哪两个直接点、哪一侧、哪个孔径、原值与括区。正文根值从表自动格式化到合理位数，纠正514.2与514.731的矛盾。

不继续二分、不新增过零密扫。研究结论以括区与原数值差为主，不把2.5 nm采样间隔、P/R根差或插值变化当D误差或置信区间。

### [恢复次数与失败处置]

有图或分解数组则只评分/归约；没有它们但原sol完整，允许本轮一次性证据恢复后处理，最多45条件×2侧=90个侧render。**这是本轮明确的新恢复上限，不是把之前消耗归零。**无新增D/zf，成功后不得为导出或画图重复render。没有原sol不重求BEM。

C相关发布验证失败，保存已算数组并修I/O，不把坏CSV清洗成新物理结果。原图门槛实际失败，只标对应条件并暂停其后续扩展。

## 5. D：本轮新增的六条件、单因素误差分离（零BEM）

### [科学问题]

当前P/R同时改变网格、远场/镜头角度采样和Bessel表等，不能直接把S差异归为网格误差、孔径效应或物理吸收效应。本轮在已有边界解上做小范围受控后处理，判断主要差异是否由后处理分辨率贡献，或在相同后处理后仍保留在边界解侧。

### [放行条件]
A的保存/读回通过；六个条件的C基准数组可重读、物理身份已核查；作者基线不改。后处理入口必须接受既有sol，不调用build_system重求解。仅改cfg字符串但沿用旧far/lens缓存不是有效增量。

固定六条件（均来自既有45条件，无新焦面；属于根据已见异常选择的开发诊断，不是独立盲测）：

| D/nm | zf/nm | 目的 |
|---:|---|---|
| 60 | 512.5, 515 | 中心过零两侧、弱信号放大 |
| 100 | 425, 435, 437.5, 450 | 积分抵消与P/R异号区 |

### [D0 基线与对照配置]
已冻结精细后处理基线记为F_base：角度100/151、Bessel4001、q5；先确认对象实际使用值。生产基线P_base为原50/51、2001、q5，不修改历史输出。

**本轮新授权的诊断配置，不用于覆盖冻结参考：**

| 对照 | 边界解 | ntheta/nphi | Bessel点数 | q | 新侧render上限 |
|---|---|---|---:|---:|---:|
| P_common | 原576生产解 | 100/151 | 4001 | 5 | 6 |
| F_q | 原1444精细解 | 100/151 | 4001 | 7 | 6 |
| F_angle | 原1444精细解 | 200/301 | 4001 | 5 | 6 |
| F_bessel | 原1444精细解 | 100/151 | 8001 | 5 | 6 |

F_base精细基准从C复用，原P_base生产图从C复用；最多新增24个侧render。不新增BEM，不混入改变NA、收集介质、材料、物理像元、孔径、焦面或光强。

角度/Bessel修改需要从原sol正确重建相应远场和镜头数值对象；对q的改变只改变65 nm像元内部积分采样，不能把物理像元改成65/q nm。实际接口不支持某诊断配置时，写明NOT_EXECUTABLE，不偷偷重求BEM或改物理参数绕过。

### [D1 输出与推理限制]

对每次增量保存完整有符号C及Cs/Cint/I0、固定41×41指标、中心与所有固定孔径描述量，分别比较：

- 原P_base vs 原F_base：总P/R差；
- 原P_base vs P_common：生产侧后处理组合的净改变；
- P_common vs F_base：共同后处理下、不同边界解的剩余差；不能在其他配置不相同时简称纯网格误差；
- F_q / F_angle / F_bessel各自vs F_base：一个数值因素的增量。

数组上可检查 `P_base-F_base = (P_base-P_common)+(P_common-F_base)`；不把几个相对百分比或范数直接相加减。一次加密前后相近是有限增量证据，不是收敛定理或绝对误差上界。没有联合加密就不宣称所有交互项已排除。

各增量要计算对中心、积分、Cs和Cint的影响。近零量报告绝对差、分子分母、符号和病态标记。不得事后新增“全部标量<2%”使旧全图结果变FAIL，也不得因旧全图PASS把标量写稳定。本轮只给数据和来源分类：POSTPROCESS_SENSITIVE / COMMON_POSTPROCESS_RESIDUAL / MIXED / INDETERMINATE，并给支持数值，不能凭最大一项就宣称唯一根因。

精细侧基准只是较细参考；未取得更高网格/规则参考时，不签网格收敛或P_base大规则已关闭。新的诊断配置不得替代历史固定F_base去重算旧通过率。

### [失败处置]
任何配置身份、支持域或资源不满足，停该诊断；有相关数组则保留。原规则2%检查失败按真实分支处理；本轮没有新增BEM、q9、第三档角度、扩大视野或进一步补点的预算。达到24次上限后不追加。

## 6. E：输出研究结论与后续入口，而不是直接建全密库

本轮主结论分四层：

1. **数值基准**：三尺寸真均匀BEM/Mie的已报告或已复核范围；27条件固定生产/精细指标。
2. **提取量行为**：中心、固定积分、孔径正负项分别描述；不能更换指标解释“最强”。
3. **误差来源**：哪些后处理增量有证据，哪些仍为边界解/未解数值机制；代数抵消不是吸收因果。
4. **反演资格**：本轮没有D方向局部可靠斜率、实验提取器匹配与独立尺寸验证，不输出未知颗粒绝对粒径、连续单调或唯一反演。

达到本轮证据闭合与单因素对照后，形成一页后续建议，明确“拟采用的实验量是否为静态/FFT/DoG、是否有真实源码、哪些n/κ/几何/倍率是实测或假设”。没有真实提取器不把演示C_center/S_area改写成实验量。静态光学前向也不等于磁驱动—运动—曝光—FFT链。

**本轮不放行Fe3O4全密库或新D方向网格。**下一步的D节点、独立留出和噪声方案应基于明确的观测量与其误差预算，不从三个离散尺寸硬拟合D³。不要为等待真实材料实测值暂停已经可做的文献模型零BEM诊断，也不要将当前文献数据冒充真实批次。

## 7. 其他既有分支与固定约束

- IDENTITY、物理像元65 nm、q5正式基准、1506e合成配方保持；D中的q7只是单独诊断。禁止多曝光、按D调光、任意幅值/相位对齐、删纯散射项。
- 修复根材料合同/manifest/当前任务状态；旧错误文本留history，不再让根目录的旧1987/0.0831i字符串被当当前有效合同。当前对象仍必须独立读回，不用新合同回填历史。
- 实际提取器只按已知工程/历史test.m线索有限恢复；没有源码保留NOT_FOUND。Fs5000/N2001/100us解析测试是夹具假设，不是实测曝光；有对应旧脚本和原始文件才回放实验小例。
- 解析参考只补原未完成的非整频点、曝光时间基准相位和近零处理，不另加新模拟批次。
- R5最多原未用4个确定性重建小例，标NOT_ORIGINAL，不计独立样本；R6最多原未用32份边界诊断、4份×21点剖面，原估计/域/阈值不改。
- P0优先已有SL/DL数组相对Frobenius、完整贡献/索引和目标路径Hook。未命中duffy1/eval2不归因环境；绝对最大差不能代相对门槛。原direct/reflected/total各<1e-10及所有专属前置满足后，原最多一笔rule7参考与<0.005增量授权才可执行；不是本轮新增额度，不挪用磁材料账。
- 独立P0开放不自动阻塞未受影响rule3；实际发现共享路径污染则按范围暂停。任何大P0任务不与高内存后处理/BEM并发。

## 8. 本轮预算与自动继续

| 工作 | 本轮上限 | 性质 |
|---|---:|---|
| 新磁材料/金球BEM | **0** | 不重新授权已完成端点 |
| 端点均匀远场证据 | 2个已有sol各最多1次公共远场后处理 | 非BEM |
| 既有45条件证据恢复 | 最多90个侧render | 本轮明确恢复上限；有原数组就不render |
| 六条件受控后处理 | 最多24个新增侧render | 本轮明确新诊断授权 |
| 新D/zf/λ/gap/材料值 | **0** | D阶段不新增物理条件 |
| 孔径归约 | 原6个边长，随已有图计算 | 不额外render |
| 导出/守卫修复 | 最多2轮 | 本轮明确新增，旧迭代账保留 |
| P0 rule7 | 原余≤1笔且专属前置全部通过 | 非新额度，与磁材料0笔区分 |

90是丢失图/场时的最坏恢复上限，不是要完成的目标数；24是诊断上限。累计本轮侧render最多114，实际所有命中缓存扣除。一次render同时保存全部所需场和描述量，不为孔径、表格或绘图重复运行。

阶段一旦通过自动进入下项，不逐步等GPT。身份冲突、物理门槛失败、资源超限、修复预算用尽只停受影响分支。运行中任务先看真实身份和活动，不因没有打印盲杀。若会话必须结束，交可核验断点与状态，不用预估“应该完成”代替结果。

## 9. 发布验收：必须校验“实际归档字节”，不能再只检查内存表

1. 原数组先持久化；关键表在一个新staging目录生成并读回。
2. 检查UTF-8、无非预期控制字符、每行字段数、dtype、有限性和精确键集合；不只检查列数。
3. primary27恰27键；aperture162恰162键；refinement18恰18个内部点。D3 JSON包含引用旧点时标明，不累计新计算数。
4. 新六条件表由primary27筛选；Frobenius、谱范数、描述量、closure的定义和函数hash明确，主表/摘要不互相矛盾。
5. 标量数字以足够精度输出，MAT/NPZ为数值主件；JSON不输出NaN/Inf，空项用null和reason。读取后还需语义检查。
6. 故意缺失孔径行、非法控制字符、错误passed和一项NaN的发布夹具必须被阻止。旧损坏CSV必须在回归集内且被拒绝。
7. manifest只对最终字节生成，上传后重新拉取关键CSV/JSON核对实际哈希和schema；Git换行规范化单独说明，不伪造字节一致。
8. numeric数组包不要只在清单里宣称存在。压缩后27组65×65 P/R C+I0并不需要上传大求解器对象，应随用户ZIP；要公开时只含已授权的合成数据，不含真实实验原帧、凭据或不必要个人路径。

建议唯一ZIP：

```text
iscat_v068_return.zip
  00_README.md
  00_全部文本汇总.md              # 本轮内容，不是v059旧汇总
  00_Codex_v068_执行指令.md
  status.json / review.md / active_contracts.json
  material_contract.json / axis_contract.json / recipe_identity.json
  tables/
    source_and_runtime_identity.csv
    io_guard_and_resume_tests.csv
    solve_ledger.csv
    true_homogeneous_four_gates.csv
    mie_crosschecks.csv
    primary27.csv / primary6.csv / aperture162.csv
    refinement18.csv / root_brackets_and_interpolations.csv
    shared_field_comparisons.csv
    controlled_postprocess_24.csv
    observable_error_attribution.csv
    task_status.csv
  numeric/
    primary27_arrays.mat          # C/I0/Cs/Cint/坐标/P-R，普通数值，不只MATLAB类对象
    refinement18_arrays.mat
    controlled_postprocess_arrays.mat
    homogeneous_farfield_evidence.mat
    numeric_inventory.json       # 变量、shape、dtype、轴、文件hash、真实来源
  source/                        # 实际执行者、helpers、父版本、diff
  logs/                          # 原生预检、导出测试、错误与恢复日志
  history/                       # 原损坏文件与旧错误不覆盖
  manifest_sha256.csv
```

两端点原sol可以继续保留工作站，但远场和截面原值应可独立复算。未能恢复的东西标明真实缺失，不用文本“evidence=COMPLETE”覆盖它。

## 10. 审查依据与本地复核范围

固定提交均为 `9a533f637318eb6c210bb7f428cff70d1397593a`：

| 编号 | 文件/来源 | 支持内容 |
|---|---|---|
| S01 | status.json / review.md | 本轮已报告完成/开放及过零解释 |
| S02 | 递归目录树（truncated=false） | 本轮可读产物；没有原数组包/单独端点四门槛表 |
| S03 | source/run_v067_comprehensive.m | 真均匀实现、保存阶段、展平L2、分解、嵌套孔径与混合结构导出 |
| S04 | tables/v067_27condition_full.csv | 已确认损坏的原字节，6332 bytes，blob 3b50bc… |
| S05 | logs/v067_matlab_run.log | 两条PASS结果、27个条件日志、D30重复start、D3 load警告 |
| S06 | tables/d3_zero_crossing_refinement.json | 可解析但舍入的D3样本/插值/note矛盾，6239 bytes，blob 41fbea… |
| S07 | source/run_v067_d3_only.m | 两类字段不同结构直接拼接及打印精度 |
| S08 | 上一轮实际执行指令00_Codex_v067…md | 原门槛、45条件预算、字段与原数组要求 |
| S09 | numeric_inventory.csv | 仅声明工作站目录，不能等同原数组在本轮被读取 |
| S10 | progress(2).md | 研究目标、冻结合同、历史/实验区分；不覆盖v067当前结果 |
| E01 | MathWorks Concatenate Structures官方文档 | 拼结构数组要求相同字段集合；未复现某历史失败的精确时刻 |

外部仅核对MATLAB接口语义，不用新文献替换本项目事实：
```text
https://www.mathworks.com/help/matlab/matlab_prog/concatenate-structures.html
https://www.mathworks.com/help/matlab/ref/writetable.html
```

审查端实际完成：两份文本重建后Git blob匹配；CSV严格解析/控制字符/键集合检查；D3四组变号括区、相邻点线性插值与两个标量差异复算。没有修复坏CSV、恢复缺失孔径值、验证原27张物理图、原生复现MATLAB导出或运行新BEM。下面是已在审查端执行的可复用核对程序；针对新v068产物应使用新schema与身份，不能简单把固定v067 hash改掉后说旧文件通过。

## 附录：审查端实际运行的v067文本核对程序

```python
#!/usr/bin/env python3
"""Audit published v067 text artifacts, not MATLAB/BEM fields.
Usage: python audit_v067_exports.py --root PATH --output report.json
Expected failure of CSV scientific-record validation is recorded, not repaired.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, io, json, math
from pathlib import Path

PINNED = {
    'v067_27condition_full.csv': '3b50bc8e2c7dbbe4b09eb9fcd97735f1c1e2aef4',
    'd3_zero_crossing_refinement.json': '41fbea783e1f66e7b787a956330925f85b92965a',
}

def read_verified(root: Path, name: str) -> tuple[str, dict]:
    p=root/name
    if not p.is_file(): p=root/'tables'/name
    raw=p.read_bytes()
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()
    if blob != PINNED[name]:
        raise ValueError(f'{name}: input is not the reviewed Git blob: {blob}')
    return raw.decode('utf-8',errors='strict'),{
        'git_blob':blob,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}

def linear_crossings(rows: list[dict], column: str) -> list[dict]:
    out=[]
    rows=sorted(rows,key=lambda r:float(r['zf']))
    for l,r in zip(rows,rows[1:]):
        z0,z1,y0,y1=map(float,(l['zf'],r['zf'],l[column],r[column]))
        if not all(math.isfinite(v) for v in (z0,z1,y0,y1)): raise ValueError('Nonfinite input')
        if y0*y1 < 0:
            out.append({'bracket_nm':[z0,z1],
                        'linear_interpolation_nm':z0-y0*(z1-z0)/(y1-y0),
                        'origin':'arithmetic_on_published_rounded_values_not_new_render',
                        'not_a_diameter_error_or_confidence_interval':True})
    return out

def main() -> int:
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    text,csv_id=read_verified(a.root,'v067_27condition_full.csv')
    rr=list(csv.reader(io.StringIO(text,newline=''),strict=True)); head,rows=rr[0],rr[1:]
    controls=collections.Counter(ord(c) for c in text if ord(c)<32 and c not in '\t\r\n')
    allowed={(float(d),float(z)) for d in (30,60,100) for z in range(375,576,25)}
    valid_keys=[];invalid_key_records=[]
    for number,row in enumerate(rows,2):
        try:
            key=(float(row[0]),float(row[1]))
            if key in allowed: valid_keys.append(key)
            else: invalid_key_records.append(number)
        except (ValueError,IndexError): invalid_key_records.append(number)
    valid=(len(rows)==27 and not controls and all(len(r)==len(head) for r in rows)
           and len(valid_keys)==27 and set(valid_keys)==allowed)
    jt,json_id=read_verified(a.root,'d3_zero_crossing_refinement.json');j=json.loads(jt)
    r60=j['D60_center_zero_crossing']['detail'];r100=j['D100_S_area_zero_crossing']['detail']
    crossings={name:linear_crossings(rows_,col) for name,rows_,col in [
        ('D60_prod',r60,'C_center_prod'),('D60_fine',r60,'C_center_fine'),
        ('D100_prod',r100,'S_area_prod_nm2'),('D100_fine',r100,'S_area_fine_nm2')]}
    x100=next(r for r in r100 if r['zf']==435)
    x60=next(r for r in r60 if r['zf']==515)
    report={'review_commit':'9a533f637318eb6c210bb7f428cff70d1397593a',
        'scope':'text byte identity, CSV schema and scalar arithmetic only; no MATLAB/BEM',
        'csv':{'identity':csv_id,'schema_valid':valid,'header_columns':len(head),
            'parsed_data_records':len(rows),'field_count_distribution':dict(collections.Counter(map(len,rows))),
            'unexpected_controls':{f'U+{k:04X}':v for k,v in controls.items()},
            'allowed_leading_D_z_keys_count':len(valid_keys),
            'invalid_key_record_numbers':invalid_key_records,
            'no_shifted_row_salvage_or_invented_aperture_data':True},
        'json':{'identity':json_id,'D60_records':len(r60),'D100_records':len(r100),
            'crossings':crossings,
            'D60_note':j['D60_center_zero_crossing']['note'],
            'D60_declared_root':j['D60_center_zero_crossing']['linear_interpolation_zf']},
        'diagnostics_from_rounded_values':{
            'D100_z435_prod_S_nm2':x100['S_area_prod_nm2'],
            'D100_z435_fine_S_nm2':x100['S_area_fine_nm2'],
            'D100_z435_difference_nm2':abs(x100['S_area_prod_nm2']-x100['S_area_fine_nm2']),
            'D60_z515_absolute_difference':abs(x60['C_center_prod']-x60['C_center_fine']),
            'D60_z515_relative_difference':abs(x60['C_center_prod']-x60['C_center_fine'])/abs(x60['C_center_fine'])}}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
    return 0
if __name__=='__main__': raise SystemExit(main())

```
