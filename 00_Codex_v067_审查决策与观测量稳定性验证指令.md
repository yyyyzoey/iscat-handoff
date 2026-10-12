# iSCAT v067：v066审查裁决、真均匀基准与观测量稳定性验证

> 执行者：Codex；结果审查与下一轮决策：ChatGPT。
> 审查固定提交：`yyyyzoey/iscat-handoff@c6b4062851d40dbb53db6e7cadfc2a9c83cb7abe`（分支v066）。
> 本文件是唯一的下一轮执行合同。新方案、审查端CSV计算、工作站原执行结果必须分开记录。
> 最终目标仍是磁纳米颗粒在真实反射式iSCAT和同一实验提取程序下的观测量—尺寸关系。当前为`LITERATURE_MATERIAL_EXPLORATION`，不签实验标定、绝对粒径或连续域认证。

## 0. 执行总令与本轮优先级

完整阅读后连续执行所有前置满足、输入齐全、资源允许且在预算内的任务。不必每一步返回等GPT，也不因一个独立分支受阻而停止全部任务。失败保留并仅暂停依赖该失败的分支；不改门槛、删样本、改材料或擅自追加BEM。

本轮顺序：

```text
A  最小输入/场景/缓存身份与共享验收入口闭合；修正当前状态（零BEM）
B  原已授权但未使用的30、100 nm真均匀基准（各最多1笔；不新增额度）
C  从已有27条件图/解统一计算Frobenius、公共复场与真实响应（零新BEM）
D  在同一物理模型中诊断积分抵消、孔径依赖和两处过零区（有限后处理）
E  真实提取器/解析测试、旧恢复/B2/P0按原余额继续；统一生成可审计返回包
```

A/B放行后，B优先于新增焦面后处理。C已有数组审计可以提前独立进行；B某端点失败不阻止另一个端点，也不阻止有明确诊断标签的缓存分析。不得再将已授权的B写成“等待GPT决定是否放行”，但真实守卫失败必须停止相关求解并交证据。

本轮不新建Fe3O4全密库、不新增D/波长/间隙扫描、不启动金球、相机或噪声批次。静态中心值、静态积分和约400 Hz复解调仍是不同观测量。

## 1. v066审查裁决：采用事实，不继承过度结论

### 1.1 确认可保留的工作

1. `tables/c1_frobenius_recomputed.csv`含6个完整、不重复的D/zf键及分子、分母。审查端按工具返回文本重建该表，Git blob与提交一致；复算`numerator/denominator`与表列值的最大绝对差为`1.8214596497756474e-17`。6个**表报Frobenius值**为0.00521627715097193—0.00594259663281661，均<0.02。[S03]
2. `tables/e27_static_focus_sweep.csv`真实包含3尺寸×9焦面共27行，每行有生产/精细中心对比度、面积积分和最大绝对对比度。这些响应字段比上一轮口头描述更完整，保留为可继续分析的已报告数据。[S04]
3. v066明确承认先前`homog`标签对应分层配置，30/100 nm真均匀基准尚未执行，原两笔预算未使用。这一状态不再按旧摘要误写为三尺寸均匀全部通过。[S01,S02]
4. 原v064正确60 nm均匀基准继续保留，不因端点缺项重跑60 nm；其原始数组证据不足时继续分开记录摘要与数组可核验性。

审查端未运行工作站MATLAB/BEM，未取得27组原始图像或边界解。因此以上CSV复算不是再次独立验证Frobenius图像范数或实际材料对象。

### 1.2 必须纠正的结果状态

**E27的总通过不能接受为“27个Frobenius检查全部通过”。**六个重叠条件的`fwd_relL2_41x41`，逐个精确等于C1表的`spectral_diagnostic`，六个均不等于C1的`frobenius_relL2`。例如D100/z450：E27为0.00667965525638135，C1正式Frobenius为0.00594259663281661。[S03,S04]

这证明两表存在指标语义冲突，不证明另外21个真正的Frobenius必然失败；也不依据未发布代码断言全部27行都由哪一段旧脚本生成。正式状态：

- C1：`reported_numeric_gate=PASS`；分子分母算术复核PASS；原数组和真实生成脚本证据按实标记。
- E27：`execution=COMPLETED_REPORTED`，`response_table=AVAILABLE`，`frobenius_validation=INDETERMINATE`，`metric_evidence=CONFLICTING`，直到同一数组、同一函数重新生成27行。
- C2：`identity=PASS_REPORTED`；没有随包对象读回和公共复场比较时，审查证据为PARTIAL，不以状态中的一句话替代完整验收。
- M2H_D030/M2H_D100：NOT_STARTED，不是物理FAIL；依赖项不得升级为已完成全部目标材料验证。

### 1.3 正文的排序与过零解释须订正

依据27行**已报告表值**：

- 九个焦面，`abs(C_center_fine)`最大尺寸全部为D100；`max_abs_fine`最大尺寸也全部为D100。
- 九个焦面，`abs(S_area_fine_nm2)`最大尺寸全部为D60。
- 因此“近焦面D100最强、远焦面D60最强”没有一个前后一致的已列观测定义支持。必须先指定有符号值/绝对值、中心/积分/峰值，不能换指标解释“最强”。[S02,S04]
- D60中心在500与525 nm之间变号，精细侧端点为-0.0132810748191473和+0.00826683682585413。表中没有512 nm的直接样本；“约512 nm”不能登记为已求得零点。
- 审查端相邻两点**线性插值诊断**给D60精细侧约515.4087726 nm、生产侧约515.6411898 nm。它们不是直接render得到的零点，也不是不确定度。
- D100积分在425与450 nm之间变号。相邻两点线性插值诊断为生产约425.8439254 nm、精细约436.2958725 nm；差约10.4519471 nm，仅提示需诊断，不是已验证的零点漂移或粒径误差。
- 图像积分变号不能直接归因“散射与吸收竞争”。本轮可验证的是参考/散射干涉项、纯散射项、有限孔径和数值残差；不得把干涉项改名为吸收项。要隔离吸收物理效应需另有控制实验，本轮未授权改κ的BEM。

### 1.4 对课题最有用的新观察：整图误差小，不等于提取量稳定

从源表直接复算：

| 条件/量 | 生产 | 精细 | 绝对差 | 对精细侧相对差 |
|---|---:|---:|---:|---:|
| D100/z425，S_area/nm² | 61.0130255827062 | 821.857433987341 | 760.8444084046348 | 0.9257620323677136 |
| D100/z450，S_area/nm² | -1746.40461664006 | -997.075617325688 | 749.3289993143721 | 0.7515267511246431 |
| D60/z525，C_center | 0.00803507429172931 | 0.00826683682585413 | 0.00023176253412481897 | 0.02803521334786637 |

D100/z450的表报整图Frobenius为0.00594259663281661，但积分相对差约75.15%。这不矛盾，也不自动推翻原整图2%门槛；原先没有冻结“每个标量都须<2%”这一新门槛，不许事后增加后将全部旧结果改FAIL。它明确说明当前积分量不能仅凭图像门槛被宣布数值稳定或已可反演。

对线性描述量`S=w^T c`有Cauchy–Schwarz界：

\[
 |\Delta S|\le\|w\|_2\|\Delta c\|_2,
\qquad
\frac{|\Delta S|}{|S_R|}\le
\underbrace{\frac{\|w\|_2\|c_R\|_2}{|w^Tc_R|}}_{K_S}
\frac{\|\Delta c\|_2}{\|c_R\|_2}.
\]

对于面积积分，`w_j=65^2`。小的有符号总和可能导致大的`K_S`。这只是P/R差异传播的代数说明，不是精细参考绝对正确、实验噪声置信界或某个根因已确认的证明。没有D方向的局部可靠斜率，不能将δS直接换算成“±几nm”。

## 2. A：最小可复验入口与状态修正（必须实际执行，不再仅写future fix）

### [放行条件]

核对真实工程、当前MATLAB进程和缓存；不按历史PID停止进程，不并发高内存BEM。先读取本轮已存在的更新产物，任何在本文件之后已完成且身份匹配的任务直接复用。

### [必查项]

1. 恢复v066实际C1/E27生成脚本或原命令、日志、源图/sol身份；若实际脚本丢失，以v067新后处理脚本明确记录，不伪造“原v066脚本”。旧v065脚本只作历史，不能作为v066Frobenius已正确调用的证据。
2. 对三尺寸×生产/精细6个分层系统保存实际对象读回：D、真实材料n/κ/ε、层结构玻璃1.50/水1.33、gap=5、中心高度h=5+D/2、λ0=520、法向x偏振、玻璃侧NA1.3、实际物方像元65 nm、q5、坐标IDENTITY、实际角度和Bessel设置。读取光学对象及底层材料，不能只读cfg字符串。
3. 将物理身份和命名槽位分开。原错误homog缓存可按其真实分层身份复用，但禁止作为无界水Mie验证数据。均匀基准必须无玻璃界面，并走原经过验证的均匀Galerkin路径。
4. `material_contract.json`、实验合同、numeric inventory、task_status和manifest以实际当前产物更新；旧合同保留历史目录。v066的`numeric_inventory.csv`将32系统/352切片写到v065目录，不能据此认定已存在磁材料全库。按真实路径与参数重建，不直接挪用金球清单。
5. 继续完成v065求解计数冲突核对：计划槽位、实际调用、唯一物理问题、缓存复用分别计数；缺证据记UNKNOWN，不猜总数。错误、重复或失败求解不抹掉成本。
6. 单一验证函数被生产入口调用：材料来自已验Querry节点`complex(2.349,0.083)`、520 nm↔0.5200 μm、D为直径、光学μr=1；沿用常数/对象读回`<=1e-12`，不沿用未批准的1e-5/1e-9。
7. 负向夹具真正调用同一入口，测试实数相加/丢虚部、单位错误、半径误传、源哈希错误、分层配置送入均匀任务、分层缓存改名为均匀任务均被拒绝，且求解回调次数为0。只打印“bad!=expected”不算测试。
8. 缓存键含物理场景、D、材料和源文件hash、λ、层结构/几何、规则、实际求解代码；后处理键另含zf、像元/ROI、成像代码和源sol。zf不触发新BEM。同一任务多次启动不重复求解；结束先原子保存再导出。

根目录当前缺少对象表/脚本不表示工作站一定没有。先恢复；能够从既有sol重算远场或图像时是后处理，不增加求解。

### [失败处置]

输入/对象不符时隔离受影响产物；不可追溯时标证据PARTIAL，不编造读回。无关的小表复算、解析测试继续；只要B前置已满足，不以其他历史账本尚有歧义为由无限推迟B。

## 3. B：30/100 nm真均匀基准——本轮优先兑现原两笔授权

### [放行条件]

对应尺寸通过A的输入、场景和运行路径守卫，以及B0零BEM预检；真正均匀缓存搜索已完成。原v064正确60 nm均匀摘要保留，原数组缺失不自动阻断新端点，也不授权重算60 nm。

### [B0：数学预检]

复用v065已修正的半整数Mie参考及固定作者库`ce49f77f096337db8be54c46d83696d37b0b23d5`，不再写第三套新理论核。

- D=[30,60,100]，n=2.349+0.083i，外部无损水n=1.33，λ0=520 nm，μr=1；作者与独立实现逐截面差`<=1e-10`。
- 保存阶数6/8/12/16的全精度输出；8→12与12→16逐非零截面相对变化`<=1e-10`；无损控制按原`|Cabs|/Cext<=1e-10`。
- 独立参考不能调用被验作者Mie系数作为独立核；不得硬编码审查端参考数值为输出。
- 注入错误参考/NaN必须使阶段gate失败、求解回调为0。各项进入机器断言，不只打印。

### [B1：本轮可执行计划]

| plan_id | D/nm | 物理问题 | 网格 | BEM上限 | 授权性质 |
|---|---:|---|---:|---:|---|
| M2H_D030_CORRECTED_V066 | 30 | 无界均匀水中原点球 | 1444 | 1 | v066未用余额 |
| M2H_D100_CORRECTED_V066 | 100 | 同上 | 1444 | 1 | v066未用余额 |

名称可保留以维持账本连续性，执行run_id写本轮v067。已存在真正合格均匀解时为0笔；相应额度不可转作其他网格/尺寸。v066已明确尚未消耗，不再额外“批准两笔新额度”。若实际发现之后已求解，按实际扣除。

复用参数化的原均匀Galerkin基准：`BoundaryEdge([mw,mp],sphere,[2,1])`、原点球、普通triquad3、近邻triquad11、nduffy3、relcutoff2、order3、x偏振/+z传播、公共球面方向/权重原`sphere_rule(48,97)`。具体调用按真实固定源码，不把演示`build_system(camera)`仅改标签当均匀模型。

保存实际网格与输入、tau/材料、sol、eB/eM、dirRef/wRef、各截面原值、比较函数hash。先落盘已有解，再做可能失败的输出。

### [B2：原四门槛]

原始加权复远场相对L2、散射、吸收、消光截面相对误差**分别<0.02，必须四项都通过**。不做幅值/相位自由拟合，不对近零参考加realmin改PASS。目标吸收参考非零时按原相对误差；无损控制另按既定专属绝对/归一化判据。

一端点失败只停其依赖扩展；另一端点按前置继续。每笔求解发生即扣预算，物理FAIL不能自动加密网格或重求。保存失败后从仍在内存/磁盘的sol恢复，不再次求解。

## 4. C：一套共享指标函数生成六条件和27条件结果

### [放行条件]

存在可用的原图、复场或sol，实际轴/材料/场景能核验。B未闭合的尺寸可计算诊断，但不得纳入“目标材料完整验证PASS”。

### [C1：统一像元L2；本轮不再开第二套手写评分]

只使用一个共享评分入口。拟定新函数名和文件名由Codex实现并记录，不能假定工程已经存在。

```matlab
% 待接入实际数组的评分片段，不是审查端已执行的MATLAB仿真。
P = Cp(ix,ix); R = Cr(ix,ix);
assert(isequal(size(P),[41,41]) && isequal(size(R),[41,41]), 'ROI_SHAPE');
assert(all(isfinite(P(:))) && all(isfinite(R(:))), 'NONFINITE_IMAGE');
Delta = P-R;
numF = norm(Delta(:),2);
denF = norm(R(:),2);
assert(isfinite(denF) && denF>0, 'INVALID_REFERENCE_NORM');
rF = numF/denF;
passF = isfinite(rF) && rF<0.02;
rSpectral = norm(Delta,2)/norm(R,2); % 仅诊断，不进入gate
```

- ix必须由实际坐标确定；确认65×65、中心33才用13:53。行camera_x、列camera_y，禁止transpose/flip择优。
- 原27个D/zf完整且不重复；每行保存分子、分母、rF、百分比、谱范数诊断、原门槛结果、源数组/系统hash、ROI、函数版本。
- 六条件摘要从27行按D/zf**筛选生成**，不另写另一套循环。相同源数据的重叠行应相同；导出读回差仅允许规定全精度序列化容差，不能宽到2%。
- 旧C1记录可引用；若新统一后处理与它不符，先查源图/ROI/函数，不直接用本轮新数覆盖历史。
- 使用原谱范数反例夹具：R(1,1)=1，其余0；Δ=0.006*eye(41)。谱范数比0.006，Frobenius比约0.0384187454；正式gate必须拒绝。测试一并验证所有汇总调用同一函数。

已有Cp/Cr只需重新评分，不render；只有sol没有图时才后处理。把C1六组已经正确的指标重新命名不能修复E27的其余21组。

### [C2：公共复场与物理身份]

恢复同D生产/精细散射复场在相同公共方向和权重的原比较；不同角度原数组不能直接相减。必要时由现存sol补远场，零新BEM。保持原未对齐的raw_complex_relative_L2及原<0.02门槛。标明这是与较细参考的一致性，不是参考绝对误差或整个参数域的认证。

没有随包字段不许默认通过；保存source/readback/hash。完整`|Eref+Esca|²`和物理像元积分保持不变。

### [C3：所有响应直接从同一原图计算]

以精细R为参考、生产P为待比较侧，固定x=y=0物理像元和原41×41ROI：

- C_center：有符号、无量纲，不移动到最亮峰。
- S_area_nm2=65²×sum(C_ROI)：面积积分；不能用abs先行、最大值或显示归一化替代。
- max_abs_C仅作为独立描述列，不能代替前两者。
- 每量同时保存P/R、差、绝对差、分母及相对差的定义状态。

精确零参考时普通相对差为null；非零但接近零必须保留原值和绝对差并标注病态，不伪造一个更大分母。浮点近零识别可采用本轮新定义：`64*eps(1.0)*sum(abs(w.*C_R))`；这仅是算术标记，不是物理、噪声或粒径准确度门槛。可分辨的非零值（如D100/z425的821.857）仍报告其92.576%的比值，不能用“近零”删掉不利数值。

同一函数写出原27行及原双焦面6行真实响应表，旧表保留为历史。各量按原定义分别排序，输出所有离散D排序，不用含糊的“强/弱”替代。

### [失败处置]

任何新Frobenius或复场原门槛失败都保留；不改ROI、光强或阈值求通过。只限相应尺寸/焦面场景。单个标量相对差大不是原全图门槛的新FAIL，但必须阻止“该标量已稳定、已可标定”的过度结论。

## 5. D：本轮新增的有限观测量稳定性研究（零新BEM）

### [研究目的与放行条件]

回答目前最紧迫的问题：为何已有有符号积分对P/R差异远比全图敏感？这种差异是否与正负空间抵消、参考/散射干涉、孔径或输入/归一化不一致有关？本轮不是为了找一个更容易PASS的指标。

相应缓存身份明确且C模块完成后可做。未完成B或原场验收的结果标DIAGNOSTIC；B前置全部闭合后才纳入已验文献模型结论。即使中心/积分在某处不稳定，也保留对完整图像模型的有限通过，不混为一谈。

### D1. 先分解现有完整场强，而不是凭变号猜吸收

对每个物理像元j，设P_j为原强度像元积分算子、E_r与E_s为同一处理阶段的矢量场：

\[
 I_{0,j}=P_j(\|E_r\|^2),\quad
 C_{s,j}=\frac{P_j(\|E_s\|^2)}{I_{0,j}},\quad
 C_{\mathrm{int},j}=\frac{P_j(2\mathrm{Re}(E_r^*\cdot E_s))}{I_{0,j}},
\]
\[
 C_j=C_{s,j}+C_{\mathrm{int},j}.
\]

真实归一化若有额外因子，按已经固定的实际代码明确写出相应公式并验证，而不是以该示意覆盖原协议。

- 在q5子像元上先形成强度项并按原权重积分；不能用`|mean(E)|²`替代`mean(|E|²)`。
- 矢量内积、复共轭、轴与权重应取真实布局；不同偏振/激励维度不盲目squeeze。
- I0必须有限且>0，分母不加人工epsilon；P/R参考场身份分别保存。
- 两项和对原C的代数闭合残差，归一到`||C||+||Cs||+||Cint||`后`<=1e-12`；该新阈值是**同一数值数据的代数工程检查**，不替代2%物理误差。全零情形单独处理并记录，不能除零。
- 同样核对对应的中心量与积分量可加性，保留正负贡献。
- 干涉项不是吸收项；本轮不修改κ、不做无吸收分层控制BEM，不能宣称吸收效应已被独立分离。

优先对已有27条件一并导出Cs、Cint、I0与C；若字段已有就复用。否则在一次统一render中同时输出，不能为每个分解量重复render。

### D2. 固定嵌套孔径与抵消指标，不改变正式评分ROI

在同一完整有符号图上提取同中心正方形边长 `[21,31,41,51,61,65]` 个物理像元。原图/坐标支持不足的边长记NOT_AVAILABLE，不外推、补零或扩视野生成新数据。41×41仍是原唯一正式前向评分区，其余仅诊断。

每个孔径对P/R各计算：

\[
 S_+=A_{pix}\sum\max(C_j,0),\qquad
 S_-=A_{pix}\sum\min(C_j,0),\qquad S=S_++S_-,
\]
\[
 \chi_1=\frac{\sum|C_j|}{|\sum C_j|},\qquad
 K_{S,2}=\frac{\sqrt{N}\|C\|_2}{|\sum C_j|}.
\]

同时报告原始分子分母。分母为零/不可分辨时null并标记，不能裁剪负值、取绝对值求和后仍称原有符号积分。

输出各孔径的P/R差、Cs/Cint贡献、正负抵消指标及邻孔径变化；只能报告“在实际可用孔径上的变化”，不能将最大65×65当无限孔径已收敛。

这些新指标用于解释数值敏感性，不给它们事后加2%自动PASS，不从三个相距较远的D用插值斜率宣称粒径精度。P/R差也不直接等于实验误差。

### D3. 两个过零区的有限补点（明确新增后处理授权）

不新求BEM，只用既有各自系统补以下内部焦面点：

| D/nm | 所查量 | 原直接采样括区/nm | 新增zf/nm | 新增条件上限 |
|---|---|---|---|---:|
| 60 | C_center | 500—525 | 502.5,505,507.5,510,512.5,515,517.5,520,522.5 | 9 |
| 100 | S_area(41×41) | 425—450 | 427.5,430,432.5,435,437.5,440,442.5,445,447.5 | 9 |

共最多18个新D/zf条件，P/R最多36个新增侧render；相应点若已有同身份结果则复用。不对整区间改成全2.5 nm密扫，不增加D或gap，也不迭代二分直到得到想要的根。

每点仍同一函数输出图像Frobenius、场强分解、各固定孔径与符号。对P和R各自报告直接采样变号区间；区间内有多个变号时全部保留。线性插值根只作`INTERPOLATED_NOT_DIRECT_ROOT`，不把2.5 nm间隔当作物理可信区间。

重点比较：D60中心的零点是否真的在当前约括区；D100积分的P/R过零位置是否明显不同、对孔径是否敏感。对消光/吸收的因果归因仍不由此单独成立。

### D4. 本轮研究结论应分四级

1. 直接离散计算事实：值、符号、排序、源数组身份。
2. P/R数值差异事实：图像、复场与各提取量分别列出。
3. 数学解释或机制假设：抵消、干涉、孔径依赖及支持证据，不写成已证唯一原因。
4. 反演资格：本轮仍不输出未知实验颗粒尺寸，不给连续单调/唯一反演/几何真值承诺。

只有真实同一提取器与参数约束恢复后，才另行决定D方向节点和独立留出。当前完整场/向量观测是否比单标量稳健可作为后续问题，不在本轮不经预注册就换算法或调指标。

## 6. E：其余分支的有限继续

- 真实提取器：按已知实际工程/历史test.m路径恢复，记录检索范围。没有找到就保留NOT_FOUND；不要将65 nm/q5/41×41的演示参数转成实测仪器输入。
- 解析参考：只补原未完成的400 Hz非整频点有限和/FFT、曝光中心/开始时间戳相位、近零序列化和原生成源码。Fs5000、N2001、k160、100 μs均保留TEST_ASSUMPTION/ANALYTIC_REFERENCE_ONLY的原定位。不重跑金球或将静态图冒充动态解调验收。
- 旧R5确定性重建：最多原未用4样本，只在原输入和版本可恢复时执行，记录NOT_ORIGINAL，不增加独立样本、不伪造旧帧证据。
- R6边界B2：原未用最多32份既有观测诊断、最多4份×21个zf剖面仍可继续；不改搜索域、阈值或原估计值，不删除边界样本。
- P0：优先已有SL/DL数组的相对Frobenius和完整贡献/索引审计。只有旧绝对max差时不签相对PASS。实际duffy1/eval2 Hook须报告命中数/stack/shape/资源；未命中不是环境根因证明。原direct/reflected/total各<1e-10，局部回归、覆盖与资源门槛均满足后，才执行原最多1笔rule7参考及<0.005增量检查。独立OPEN不阻塞未受影响rule3；若找到共用路径污染按实暂停。

P0高内存任务与磁材料BEM不并发。其他旧预算不能因版本号增加重新清零。

## 7. 本轮预算及停止规则

| 工作 | 上限 | 说明 |
|---|---:|---|
| 30 nm真均匀 | 最多1笔BEM | v066未用余额，合格缓存则0 |
| 100 nm真均匀 | 最多1笔BEM | 同上 |
| 新增BEM授权 | **0笔** | 本轮只兑现上述余额 |
| 60 nm/新分层/D/λ/gap求解 | **0笔** | 不授权 |
| 原27条件统一评分/分解 | 最多54个侧render | 有图/场直接复用；已有结果不重算 |
| 两个局部过零区 | 最多18条件、36个侧render | 本轮新增零BEM后处理 |
| 上述render总上限 | **90个侧render** | 若只有sol需从头后处理；共享结果合并，不另叠54 |
| ROI诊断 | 6个固定边长，最多45条件×2侧×6 | 数组归约，0新render/0BEM |
| 新金球、噪声、全密库 | **0** | 不授权 |
| P0大rule7 | 原有≤1笔条件额度 | 所有前置满足才用，不挪磁材料额度 |

本轮明确新增最多**2轮**有记录的合并包装迭代，仅涵盖场景守卫、共享评分/导出和后处理分解接入；旧迭代账保留。原数学Mie正确部分不重写。改变作者核、提高网格、调整材料/光路/阈值或超预算不能列为包装修复。

优先保存输入身份和sol，再生成摘要。异常类型真实记录；NOT_STARTED不写0或FAIL；来源缺失不编补。一个前置FAIL只阻断真正依赖它的任务。阶段完成后自动继续，无需每一步等GPT。

## 8. 发布前必须自动检查：让下一轮不再只收到口头PASS

由结果表计算顶层状态，不手填固定文案。至少验证：

1. 27个主条件键完整；局部新增18个条件单独标记，和主条件不混计。
2. 六条件表来自同一27行筛选；相同源hash、函数hash、ROI、指标一致。
3. 每行rF由未舍入分子/分母计算；Frobenius列、谱范数列名称与调用一致；NaN/零分母绝不通过。
4. 物理gate与描述量统计不混；E_all_PASS仅聚合确实具有所需有效前置的行。`summary_PASS`不能将`evidence_PARTIAL`自动变COMPLETE。
5. “最大尺寸/最强响应/零点”文字从明确的列与排序、采样括区自动生成；没有直接点不写直接零点，没有密D验证不写连续单调。
6. M2按真实场景和四项布尔聚合；由分层图不能签均匀通过。求解账区分继承余额、调用和有效结果，不补估计耗时。
7. manifest按**最终发布字节**计算，扫描路径全部存在；发布后重新读取关键文件核对。旧错误材料合同与旧阈值只保存在历史区或明确标历史，不能让根目录陈旧文件冒充当前有效合同。
8. 附本轮实际新增/修改源码和所需helpers、真实命令日志、同一入口测试报告，不只包含旧v065驱动。未更改大作者库只给固定commit与必要差分。

唯一ZIP建议：

```text
iscat_v067_return.zip
  00_README.md
  00_全部文本汇总.md                    # 本轮摘要及关键JSON/CSV原文；不是旧v059全文
  00_Codex_v067_审查决策与观测量稳定性验证指令.md
  status.json / review.md
  active_contracts.json / material_contract.json
  axis_contract.json / recipe_identity.json
  tables/
    solve_ledger_reconciled.csv
    physical_identity_readback.csv
    guard_and_metric_tests.csv
    mie_crosscheck_full_precision.csv
    true_homogeneous_four_gates.csv
    c1_frobenius_current.csv
    static_response_primary27.csv
    raw_field_comparisons.csv
    static_response_root_refinement.csv
    signed_components_apertures.csv
    response_conditioning_summary.csv
    task_status.csv
  source/                            # 实际执行者及helpers/diff
  logs/                              # 当轮命令、失败、测试、完成记录
  numeric/
    primary27_images.mat             # 至少全27条件P/R原C、I0、坐标；不只PNG
    diagnostic_component_examples.mat # 至少D60 z500/525、D100 z425/450的分解
    homogeneous_evidence/            # 新端点解/复远场/方向权重及截面必要证据
    inventory.csv                    # 大sol可工作站保留，但变量/shape/dtype/轴/hash完整
  history/                           # 原文与旧错误记录保留
  manifest_sha256.csv
```

27组65×65的P/R对比度数组规模不大，应作为可独立重算指标的最小数值证据随包；大边界系统可只列工作站路径和真实hash。公开发布只按已有授权范围，不加入凭据、未经授权的真实实验原帧或个人路径信息。

## 9. 本文件审查来源与复算范围

以下是审查时读取的源文件，不表示工作站已执行v067。固定仓库提交统一为`c6b4062851d40dbb53db6e7cadfc2a9c83cb7abe`。

| 编号 | 来源 | 支持内容 |
|---|---|---|
| S01 | status.json | C1/C2/E27报告、端点真均匀未开始及原两笔未用 |
| S02 | review.md | 变号、排序与吸收归因的原说法 |
| S03 | tables/c1_frobenius_recomputed.csv | 六行分子分母、Frobenius和谱范数；blob 454997005552629ad36cb66cd3eaa192f5e4de61 |
| S04 | tables/e27_static_focus_sweep.csv | 27行有符号响应与仍冲突的前向列；blob a2be4fdd232be35a3db2cbac697f1d40f201e401 |
| S05 | source/run_v065_three_size.m（固定提交仍保留） | 旧矩阵norm评分代码；不能据此假装已读到未提供的v066生成代码 |
| S06 | 固定提交根树、source树1e089700b72d5a9aa91aa94fa851f14c5608f536、tables树c9a06c8ae56ed4fd7a7d39a95582ff32e8fa5193 | 本轮发布证据可见范围；未提供对象读回/C2复场表和实际v066驱动 |
| S07 | numeric_inventory.csv | 当前清单字段与路径声明；不是实际文件系统证明 |
| S08 | 已上传00_Codex_v066_均匀基准纠偏与磁颗粒响应验证指令.md | 未用两笔、原门槛、前置、27条件研究及缓存规则；blob aa1ef831ac5c3562addee6f9d4ba192f10fb6175 |
| S09 | progress(2).md（历史交接） | 最终研究目标、完整干涉强度、实验/演示区分；不替代v066新状态 |
| E01 | MathWorks norm官方文档 | 矩阵默认norm为谱范数；展平向量L2与Frobenius一致 |

固定源入口（仅为来源，不是待Codex下载的唯一方法）：

```text
https://github.com/yyyyzoey/iscat-handoff/tree/c6b4062851d40dbb53db6e7cadfc2a9c83cb7abe
https://www.mathworks.com/help/matlab/ref/norm.html
```

审查端实际做了：两份CSV文本重建后Git blob和SHA-256检查、全33行字段/数值/条件键检查、6个比值复算、两表6个重叠键比较、27行排序和标量差异计算、相邻点线性根诊断。没有读到27组原数组、重新验证材料对象或运行新的Mie/BEM。下面附本轮已运行的纯CSV复核程序；严格字节校验失败时应定位不同来源或换行问题，不静默忽略。

## 附录A：审查端实际执行的CSV核对代码

```python
#!/usr/bin/env python3
"""Audit the two published v066 CSV tables; no MATLAB/BEM or image reconstruction.

Usage: python audit_v066_tables.py --root PATH --output report.json
PATH contains c1_frobenius_recomputed.csv and e27_static_focus_sweep.csv,
or contains a tables/ directory holding them. Exact bytes are checked against
Git blob identities from c6b4062851d40dbb53db6e7cadfc2a9c83cb7abe.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

EXPECTED = {
    'c1_frobenius_recomputed.csv': '454997005552629ad36cb66cd3eaa192f5e4de61',
    'e27_static_focus_sweep.csv': 'a2be4fdd232be35a3db2cbac697f1d40f201e401',
}

def load_table(root: Path, name: str) -> tuple[list[dict[str, float]], dict[str, Any]]:
    path = root / name
    if not path.is_file():
        path = root / 'tables' / name
    raw = path.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    if blob != EXPECTED[name]:
        raise ValueError(f'{name}: byte identity differs from the reviewed commit: {blob}')
    records = list(csv.reader(raw.decode('utf-8').splitlines()))
    if len(records) < 2 or len(set(records[0])) != len(records[0]):
        raise ValueError(f'{name}: empty table or duplicate header')
    header = records[0]
    out: list[dict[str, float]] = []
    for line_number, record in enumerate(records[1:], start=2):
        if len(record) != len(header):
            raise ValueError(f'{name}:{line_number}: inconsistent field count')
        row = {k: float(v) for k, v in zip(header, record)}
        if not all(math.isfinite(v) for v in row.values()):
            raise ValueError(f'{name}:{line_number}: non-finite value')
        out.append(row)
    keys = [(r['D'], r['zf']) for r in out]
    if len(set(keys)) != len(keys):
        raise ValueError(f'{name}: duplicate D/zf condition')
    return out, {'file': name, 'bytes': len(raw), 'git_blob': blob,
                 'sha256': hashlib.sha256(raw).hexdigest(), 'rows': len(out)}

def root_linear(rows: list[dict[str, float]], d: int, column: str) -> list[dict[str, Any]]:
    result = []
    g = sorted((r for r in rows if r['D'] == d), key=lambda r: r['zf'])
    for a, b in zip(g, g[1:]):
        if a[column] * b[column] < 0:
            z = a['zf'] - a[column] * (b['zf'] - a['zf']) / (b[column] - a[column])
            result.append({'D': d, 'column': column,
                           'sample_bracket_nm': [a['zf'], b['zf']],
                           'linear_interpolation_nm': z,
                           'scope': 'POST_HOC_LINEAR_INTERPOLATION_NOT_A_SIMULATED_ROOT'})
    return result

def audit(root: Path) -> dict[str, Any]:
    c1, id_c1 = load_table(root, 'c1_frobenius_recomputed.csv')
    sweep, id_sweep = load_table(root, 'e27_static_focus_sweep.csv')
    required = {(float(d), float(z)) for d in (30, 60, 100) for z in range(375, 576, 25)}
    if {(r['D'], r['zf']) for r in sweep} != required:
        raise ValueError('27-condition grid mismatch')
    if {(r['D'], r['zf']) for r in c1} != {(float(d), float(z)) for d in (30, 60, 100) for z in (450, 550)}:
        raise ValueError('C1 six-condition grid mismatch')
    by_key = {(r['D'], r['zf']): r for r in sweep}
    overlaps = []
    for r in c1:
        q = by_key[r['D'], r['zf']]
        if r['denominator'] <= 0:
            raise ValueError('C1 nonpositive denominator')
        ratio = r['numerator'] / r['denominator']
        if abs(ratio-r['frobenius_relL2']) > 1e-14:
            raise ValueError('C1 quotient mismatch beyond export precision')
        overlaps.append({'D': int(r['D']), 'zf': int(r['zf']),
                         'C1_ratio_recomputed': ratio,
                         'C1_reported_Frobenius': r['frobenius_relL2'],
                         'E27_reported_metric': q['fwd_relL2_41x41'],
                         'E27_equals_C1_spectral_exact': q['fwd_relL2_41x41'] == r['spectral_diagnostic'],
                         'E27_equals_C1_Frobenius_exact': q['fwd_relL2_41x41'] == r['frobenius_relL2']})
    scalar = []
    for d,z in [(100,425),(100,450),(60,525)]:
        r = by_key[float(d), float(z)]
        col = 'S_area' if d == 100 else 'C_center'
        p = r[col+'_prod_nm2'] if d == 100 else r[col+'_prod']
        f = r[col+'_fine_nm2'] if d == 100 else r[col+'_fine']
        scalar.append({'D':d,'zf':z,'observable':col,'production':p,'fine':f,
                       'absolute_difference':abs(p-f),
                       'relative_difference':None if f == 0 else abs(p-f)/abs(f),
                       'scope':'DESCRIPTIVE_NO_NEW_PASS_FAIL_THRESHOLD'})
    maxima = {}
    for col, use_abs in [('C_center_fine',True),('max_abs_fine',False),('S_area_fine_nm2',True)]:
        maxima[col] = {str(z):int(max((r for r in sweep if r['zf']==z),
                      key=lambda r:abs(r[col]) if use_abs else r[col])['D'])
                       for z in range(375,576,25)}
    roots = root_linear(sweep,60,'C_center_prod') + root_linear(sweep,60,'C_center_fine')
    roots += root_linear(sweep,100,'S_area_prod_nm2') + root_linear(sweep,100,'S_area_fine_nm2')
    r100450 = by_key[100.0,450.0]
    f100450 = next(r for r in c1 if r['D']==100 and r['zf']==450)
    # Bound applies only if the C1 norm and E27 area use exactly the same image/ROI.
    kappa = 41 * f100450['denominator'] / abs(r100450['S_area_fine_nm2']/65**2)
    return {
      'commit':'c6b4062851d40dbb53db6e7cadfc2a9c83cb7abe',
      'scope':'CSV_BYTE_AND_ARITHMETIC_AUDIT_ONLY_NO_RAW_ARRAY_VALIDATION',
      'identities':[id_c1,id_sweep],
      'C1_ratio_max_absolute_recalculation_difference':max(abs(r['numerator']/r['denominator']-r['frobenius_relL2']) for r in c1),
      'C1_reported_Frobenius_all_below_0_02':all(r['frobenius_relL2']<0.02 for r in c1),
      'C1_reported_Frobenius_range':[min(r['frobenius_relL2'] for r in c1),max(r['frobenius_relL2'] for r in c1)],
      'overlap_comparisons':overlaps,
      'E27_overlap_spectral_matches':sum(r['E27_equals_C1_spectral_exact'] for r in overlaps),
      'E27_overlap_Frobenius_matches':sum(r['E27_equals_C1_Frobenius_exact'] for r in overlaps),
      'scalar_observable_comparisons':scalar,
      'strongest_D_on_sampled_grid':maxima,
      'root_interpolation_diagnostics':roots,
      'linear_functional_bound_example':{'D':100,'zf':450,'kappa_area_if_same_array':kappa,
          'relative_difference_upper_bound':kappa*f100450['frobenius_relL2'],
          'note':'Cauchy-Schwarz bound for the reported P/R difference, NOT true error or experimental uncertainty.'}
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,default=Path('v066_table_audit.json'))
    args = parser.parse_args()
    result = audit(args.root)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
```
