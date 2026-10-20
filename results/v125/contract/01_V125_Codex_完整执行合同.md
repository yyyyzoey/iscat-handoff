# V125 Codex 交接与连续执行合同（唯一正式执行指令）

**任务标识**：`V125_SUSPENDED_DH_CALIBRATION_AND_BLIND_VALIDATION`  
**项目**：反射式 iSCAT，悬浮磁纳米颗粒的**单颗粒光学等效直径**条件标定、未知高度/位置反演、含噪及曝光测试。  
**固定来源**：`yyyyzoey/iscat-handoff` 的 `v124@384a52304f77490c410d395dd150e0ea82760d1f`。**本附件是执行指令，不是 V125 已完成的报告**。  
**执行人**：Codex 在已装有 MATLAB / 固定 NANOBEM / 原工程数据的 Windows 工作站运行。ChatGPT 负责读取下次交付并审查，当前没有直接在工作站执行新求解。  
**优先级**：合格的 D–h 数据和实际单颗粒反演 > 检验数值缺口 > 运动/噪声方法研究 > 图表美化和旧历史大套件复查。

> **Codex：请一次读取并执行全文。无需逐步骤回问 ChatGPT。只有资源上限、关键物理实现被阻断、真实源不可得或需要修改冻结科学协议时，才停止对应分支；其他独立任务持续做完，最后一次性交付真实 ZIP、GitHub 可读提交及外部回执。禁止把未执行的计划、伪造的标定曲线、旧字节复制品写成新实验结果。**

## 0. 三句话交接结论

1. **V124 已有真实成果，必须先复用而不是推倒**：发布报告记录60个分层BEM系统、66次 render，固定球心高度450 nm处训练 D=30:10:200（18个）和六个旧留出 D={35,55,85,115,145,185}，以及 D=100 nm、h=200:25:1000 的高度曲线；场数据在 `results/v124/library/valid_physical_fields_or_coefficients.h5`，原有 `bem_cache` 和 `renders` 亦已发布。此处是**发布证据与可核对资源**，接手工作站必须重新校验字节/配置及读回。
2. **V124 的科学边界**：六个旧留出固定 h=450 nm、材料 n=1.38、居中，按公布的估计 D 分别为34.5、54.5、85、115、145、186 nm；正确的六例 MAE=0.333333 nm、RMSE=0.5 nm、绝对误差中位数0.25 nm，不能称真实单颗粒精度。V124 原始 n匹配门 `max|C|<=1e-10` 实际为 `7.5083559564706605e-6`，保持 **FAIL**；噪声拒判和旧运动模糊有真实错误，不能继承为验证通过。
3. **本轮最终成果**：形成在用户默认条件下**有限且明确的 D–h 二维物理库**，用**六个真正新粒径、非节点高度、非零横移**的直接求解做未知 D/h/x/y 留出，再给出含噪与真实有限曝光模型的逐颗粒报告、拒判/多解、误差和限制。没有真实仪器量尺、材料批次、独立尺寸标准，继续保持 `EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false`。

固定证据入口：
- 分支/提交：`https://github.com/yyyyzoey/iscat-handoff/commit/384a52304f77490c410d395dd150e0ea82760d1f`
- 状态：`results/v124/status.json`；实际报告：`results/v124/review.md`；结果表：`results/v124/validation/holdout_per_particle.csv`、`results/v124/validation/zero_index_and_units.csv`、`results/v124/validation/noise_motion_results.csv`。
- 源码：`tools/v124_core.py`、`tools/invert_v124_particle.py`、`source/v124_physical_forward_adapter.m`、`tools/run_v124_all.py`、`tools/check_v124_return.py`。
- 原 ZIP：`results/v124/iscat_v124_return.zip`；外部回执：`results/v124_external_receipt.json`。回执报告36成员、27清单项、CRC/有限重放通过，**不是物理全部通过**。

## 1. 已有实验事实、条件假设和绝对边界

| 参数 | 本轮值 | 证据等级与说明 |
|---|---|---|
| 颗粒状态 | 水中悬浮 | 用户确认，不按固定贴壁球处理 |
| 介质温度 | 纯水26℃ | 用户确认 |
| 真空波长 | 520 nm | 用户确认 |
| 相机物理像元 | 14 μm×14 μm | 用户确认 |
| 物镜标称倍率 | 50× | 用户确认；**不是独立认证总倍率** |
| 载玻片 | 无 | 用户确认；保留盖玻片—水界面，不额外添加载玻片 |
| 玻璃折射率 | 1.5 | 用户估计 |
| 颗粒折射率 | 接近水 | 用户估计，真实复 n/k 和结构未知 |
| 水 n | 1.3353 | 520nm/26℃条件近似；不是仪器实测 |
| 颗粒 n | 1.38+0i | **主均匀球探索模型**；1.35、1.45为后续材料失配诊断，**本批不展开三材料全库** |
| NA、参考光路、焦面 | NA=0.8，玻璃侧法向线偏振，界面参考，zf=450nm | 未核实光路的条件假设 |
| 中继倍率 | 1× | 假设；推导物方像元14,000/50=280nm/pixel，并非实测量尺 |
| 原场/像元 | 17×17 detector，各像元5×5 fine sample | 既有演示光学离散；**正式评分固定中央13×13**，源17×17必须完整保存 |
| 合成曝光/帧间隔 | 25/100μs；5000fps仅为合成取样假设 | 不冒充相机记录/硬件校准 |
| 介质黏度、读噪 | 0.870 mPa s；2 e⁻ | 26℃水/合成相机探索假设 |
| 输出 D | `UNIFORM_SPHERE_OPTICAL_EQUIVALENT` | **不是磁芯直径、核壳外径或DLS水动力学直径** |

真实用户曾做过30nm与200nm追踪，其旧记录与7.29高速数据可能使用**不同相机、倍率与采样方式**；本轮只用作后续实验接口线索，**不把旧图像的标称 D 或从轨迹反推的倍率当独立标定真值**。当前不要求用户补材料才开工；后续换参数时要有依赖重算机制。

## 2. 工程目录、数据身份和开工时必须做的事（S0）

1. 以只读方式冻结 `v124@384a...`，保存 `git rev-parse HEAD`、父链、Git树、工具源码 Git blob、文件 SHA256、Python/NumPy/SciPy/h5py、MATLAB版本和实际 NANOBEM 上游固定提交 `ce49f77f096337db8be54c46d83696d37b0b23d5`、本地补丁 SHA、`which build_system -all`/`which render_system -all` 的有效调用路径。确认旧 V124 文件**存在并可读**；本合同的绝对路径只是线索，不得假设每个机器上的路径相同。
2. 新建独立输出 `results/v125/` 与新执行分支 `v125`（如仓库权限受限，先本机完整交付，再上传可读分支）。**绝不原地覆盖 V124 的 H5/MAT、状态、原失败证据或旧 `.zip`**。
3. 定向读取 `results/v124/library/valid_physical_fields_or_coefficients.h5`、对应 `renders/*.mat` 与 `bem_cache/*_solve.mat`，检查每条的真实 `D,h,n,np_im,gap,mesh,NA,pixel,focus,lambda,illumin,geometry,solver sha`，而不是单靠文件名。读取场数组和像元对比度，验证 dtype、finite、shape、行/列、17×17相机网格、每像元25子样本。若源字段无法证明身份，标 `UNVERIFIED_CACHE`，不能免费复用；可继续导出静态资料和诊断，必要时走 S3 备用。
4. 必须确认工作站调用路径修复：V124 MATLAB 适配器 `repoRootFull=cd(repoRootFull)` 会返回**先前工作目录**而非当前目录，调用方恰在工作树内时可能偶然不出错。改为显式`oldDir=pwd; cd(resolvedRoot); repoRootFull=pwd; cleanup=onCleanup(@()cd(oldDir));`，并验证非默认工作目录、多级路径以及不存在路径正确失败；或者完全采用绝对路径，不隐式 `cd`。输入 `--repo --config --out` 真正影响所有调用，当前目录变更不改变结果身份。
5. 不得把 `source/`、`tools/` 下不同历史候选同时 `genpath` 注入 MATLAB；动态 `import` 必须记录 `module.__file__`/SHA。禁用旧 `tools/v123_physics.py` 人造标量 C；保留为历史红例。
6. 完整交接包请复制 `01_V125_Codex_完整执行合同.md`、`config/v125_science_config.json` 和本次独立 `tools/check_v125_bundle.py` 入执行目录。配置对象为**计划配置**，必须在本地补录真实有效模块身份和运行时间后形成 `config/effective_config.json`。
7. 建立**二级缓存身份**：系统求解键涵盖材料/界面/几何/D/h/入射/离散/solver源码/补丁；渲染键再涵盖NA、焦面、物方像元、偏振、pupil、ROI、q、偏移、成像源码。旧 V124 键不充分，不得仅靠 `D100_h450` 或预格式化六位小数作命中。每次命中核对内部元数据和源SHA，不合格时必须重新解/重成像并计预算。

输出 `validation/v124_intake.csv`、`logs/source_identity.json`、`logs/current_modules.txt`、`config/effective_config.json`、`logs/actual_commands_and_errors.txt`。**没有此阶段通过的源身份，不得把“继承的15条件”直接登记为合格物理训练库。**

## 3. 软件与物理必要修复（S1，定向最多2轮，不是永久旧测试循环）

### S1-A. 修正 Mie 基准

此前 `tools/v124_core.py::python_mie()` 将球面Neumann函数混入错误的出射场构造，导致 Mie 系数缺少相容的复出射 Hankel 组合。按固定 `exp(-iωt)` 约定：

\[
\psi_\ell(z)=zj_\ell(z),\qquad \xi_\ell(z)=z h_\ell^{(1)}(z)=z(j_\ell(z)+i y_\ell(z)),
\]
\[
a_\ell=\frac{m\psi_\ell(mx)\psi'_\ell(x)-\psi_\ell(x)\psi'_\ell(mx)}{m\psi_\ell(mx)\xi'_\ell(x)-\xi_\ell(x)\psi'_\ell(mx)},\qquad
b_\ell=\frac{\psi_\ell(mx)\psi'_\ell(x)-m\psi_\ell(x)\psi'_\ell(mx)}{\psi_\ell(mx)\xi'_\ell(x)-m\xi_\ell(x)\psi'_\ell(mx)}.
\]

用 `scipy.special.spherical_jn/yn` 的显式导数实现 Riccati 导数，并另用 `miepython`（若有）或**真正独立编写且采用同一约定的** MATLAB 对照。D=10、15、20、30、100、200nm（后三者不要求近Rayleigh），检查 `Qsca≥0`，对无吸收实材料 `Qabs=Qext−Qsca≈0`，同时核对复 `a1/b1` 和散射效率。材料匹配时 Qsca→0；Rayleigh 只用于小 x 极限。若现有 MATLAB 参考同样有错误，不能让“两个相同 bug 一致”当 PASS。**Mie 为孤立球参考，不直接变成界面 iSCAT C。**

### S1-B. 修正横向位移，必须使用相同坐标轴

`frame_C_shifted` 旧代码把 `fx−dx` 同时作为**源**和**查询**轴，返回未平移图。正确原则是：固定相机/原源网格，查询已解决散射场在 `x−dx,y−dy`，**背景参考场仍在原相机像元网格**，然后先相加总场→强度→5×5空间平均：

```python
# 已知 Es_grid, Eref_grid: (85,85,3), xs,ys: 各85个nm物理坐标
# 这里是示意代码，执行时必须与MATLAB轴/向量极化约定逐字段核对
Xs,Ys = np.meshgrid(xs, ys, indexing='ij')
query = np.stack([Xs-dx, Ys-dy], axis=-1)
Es_shift = complex_field_interpolator((xs,ys), Es_grid, bounds_error=True)(query)
# 对均匀、法向入射可检验平移不引入额外入射横向相位；其他入射需相应相位
It = pixel_mean(np.sum(np.abs(Eref_grid+Es_shift)**2, axis=-1), q=5)
I0 = pixel_mean(np.sum(np.abs(Eref_grid)**2, axis=-1), q=5)
C  = (It-I0)/I0
```

若已冻结物理链的 `render_system` 用了不同的场移位签名，应通过**真实直接偏移成像**取得同一含义的正负位移参考，不能自由选择结果较小的转置/翻转。原V124 `shift_x28/shift_y28/shift_x140/shift_y140`是移动相机采样网格，其参照光也取移动位置；它能否作为“仅颗粒平移”的独立参考，必须证明玻璃/水平面和法向照明的横向平移协变性，记录绝对/相对偏差。源轴第一维`camera_x`、第二维`camera_y`，固定 IDENTITY，显式 +x/+y 哨兵。零位移必须复现同一数组；±28、±140nm非零位移测试要逐方向保留真实差，必要时加q7或局部高阶复场插值。**禁止 `fill_value=None` 无边界外推。**

本批所有位置拟合使用 17×17 原场的**中央13×13像元**（切片 `[2:15,2:15]`）作共同评分区；原85×85 fine 网格在280nm/px、q5下，四边只有约560nm的横移缓冲。要求所有 fine-grid 查询落入原支持域；提议的横向扰动绝对值 ≤约500nm仍须逐数组支持检查，域外拒判而非裁剪/补零。场插值造成的 C 差需报告成像误差量级及其 D 偏差，不自动将此误差并入光子噪声。

### S1-C. 纠正路径、时间采样和曝光

- 坐标统一纳米、时间统一秒：`Ddiff=kB*T/(3*pi*eta*Dh_m)` 单位 m²/s，采样 `delta_nm=1e9*sqrt(2*Ddiff*dt)*rng.normal()`；原V124缺 `1e9` 必须修。
- 物方真实运动是 (x,y,h) 3D；光学直径 D 与流体力学直径 Dh 区分。合成时可设 `Dh=D`，但 `source_class=SYNTHETIC_ASSUMPTION`；主光学估计器不允许偷偷使用生成时的 Dh=D 作为尺寸先验。
- 不以相机 `DT=200μs` 的路径抽样模拟25/100μs曝光。为配对比较**先生成并存档同一条1.25μs基准细路径**，生产版本从中每隔一个点得到2.5μs粗路径，再用各自产生的曝光均值对照；这是相同随机实现上的路径积分加密检查，不能每次重抽随机轨迹。
- 每个曝光窗口在其中心附近独立设置起止时间；曝光均值是**强度**`I(T)=1/T∫|Er+Es(D,h(t),x(t),y(t))|²dt`，不先平均复场。不知道 z(t) 时不能默认全部等于 h450并宣称完整悬浮。
- **先单列无噪声25/100µs的运动模糊差，再加 Poisson/读噪声**；相同光子流下25µs期望电子数为100µs的四分之一。
- 不允许先使用模拟真值中心对齐/减去真值位移，再声称完成实验定位。可保留 `ORACLE_CENTERED_DIAGNOSTIC` 与图像实际估计中心两条不同列，正式A/B/C必须在没有真值位置输入时求解。
- 球心满足 `h≥D/2+g_min`，其中最小间隙100nm是**人为的模拟排除层假设**，不是用户确认真实水中硬边界；反射扩散或条件排除要说明物理假设。**D–h库350–550nm之外不做端点clip/外推**，保存域外帧数和拒判。

### S1-D. 统计与验收修复

- 原六个固定高度留出有符号误差依次为[-0.5,-0.5,0,0,0,+1.0]nm，MAE=1/3nm、RMSE=0.5nm、绝对误差中位数0.25nm；修正偶数样本 `median` 算法。`mean signed error`、MAE、RMSE、std、range分别输出，不把负值叫平均绝对误差。
- 原相对残差 `0.10` 是**干净图像启发式**，不能用于Poisson含噪验证然后将所有拒判当成“测径成功”。建立有统计来源的似然/加权残差与**独立空白**验证，阈值只在开发集/开发空白中冻结；真实留出绝不调阈值。
- 多解判定不能只用“局部极小值≤1.05×最佳残差”；最佳残差接近0时比值失去可靠含义。保存各D条件剖面、几何相近盆地、绝对差、噪声标准化差，域边界必须作为候选解处理。

**S1返回**：`source/v125_mie_fixed.py`、`source/v125_forward_shift.py`、`source/v125_exposure.py`、`source/v125_stats.py`、`validation/s1_regression.csv`、`validation/s1_red_green.json`、未改的旧错误来源。最多2次相关代码修订；真实修订行、失败到通过的最小夹具逐项保留。**完成S1后同轮继续S2，不能停在“单项PASS”。**

## 4. 不偷偷放宽物理门的专项资格（S2）

V124 固定 `zero_index_exact_np_eq_nwater` 原门**FAILED**，实测峰值 `7.5083559564706605e-6`，并非 `<=1e-10`。本批保留它的历史真状态，独立建设**数值底限和尺寸可用性**证据：

- **优先复用V124 D100/h450已有L0、L1、精确匹配和两侧±1e-4场**，读原 Er、Es 和像元结果。
- 新BEM资格至多 **7个系统**：①D30、D200、h450、np=nwater、L0两例；②D100/h450、np=nwater、L1一例；③D100/h450、np=nwater±1e-5、L0两例；④主材料 np=1.38、D30与D200、h450、L1两例。每个工况与源码/参数哈希绑定；失败也扣数。
- 精确匹配、两侧 detune、离散级、q5/q7、Er/Es→Ibg/Itot/C 的**完整复数相干强度**、坐标与单位分开核对。不能用对比度数组四舍五入或强行改0制造PASS。两侧±1e-5如果低于数值噪底，应报告 `INDETERMINATE_NUMERICAL_FLOOR`，而非称已证明连续收敛。
- 针对主 D30和D200的信号，将匹配残差/生产-精细差换算成同一ROI上的**C绝对RMS和相对信号比例**；之后给每一 D/h 预测附 `low_signal/numerical_floor_warning`，弱对比度病例拒判或列出模型限制。离散级差不是严格真实解上界，不能假装已证明所有条件物理精度。
- P0原 blocked/unblocked Frobenius差约 `2.58848e-7`仍开放。实际拟用调用路径若受其影响，必须标清影响范围；不允许变更 rule7 物理规则/成本，或用同源校验代替真正前向资格。V124 的q5/q7约0.318%、D100 L0/L1约0.449%仅是有限旧工况。

**资格裁决分层**：
`V124_ORIGINAL_EXACT_MATCH_GATE=FAIL`（不可更改）；`V125_MATCH_RESIDUAL_DIAG=...`；`V125_DIRECT_FORWARD_NUMERIC_SCOPE=CONDITIONAL/FAIL/INDETERMINATE`。只有与目标模型相关的确凿错误才暂停其新BEM支线；可独立的源核查、正确Mie、旧库回归和相机统计继续。**本阶段也不能给 `EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=true`。**

## 5. 主物理计算：建立真正 D–h 二维库（S3）

### S3-A. 优先主方案（合格复用15个V124条件）

固定训练尺寸：

```text
D_train_nm = [30,50,70,100,130,160,200]  (7个)
h_train_nm = [350,375,400,425,450,475,500,525,550]  (9个)
```

总 `7×9=63` 条训练物理条件。V124有效缓存已含上述7个D在h450及D100在这9个h的交叉共 `7+9-1=15` 条；必须以**完整身份匹配**后复用，否则不算。主方案新增 **63−15=48个 BEM 系统**；每项保留实际场和对应17×17 signed C、Ibg、参考/散射场、配置和源SHA。

先运行最少四个**没有旧场的矩形角点**（如 D30/D200 与 h375/h525 的组合，计入48），核实张量轴、信号尺度、强度恒等式和 h/几何一致；然后自动完成剩余44个，不能把先导检查当阶段终点。每系统改变D或h应调用正确分层求解；除非物理代码证明可复用，不许只给散射场乘 `sin(2kh)` 代替BEM。

静态成像固定主模型np=1.38+0i、nwater=1.3353、nglass=1.5、NA0.8、zf450nm、280nm/物方像元、q5、17×17相机；粒子表面间隙按 `g=h−D/2` 求得，检查≥假设100nm。磁芯、核壳和其他np尚未证实，本轮不乘出三材料全扫描。

### S3-B. **事前**确定是否使用备用小域，不能按留出结果选

若必要物理修复使全部V124缓存身份失效，则在读取本批新留出前冻结：

```text
D_train_nm = [30,50,70,100,130,160,200]
h_train_nm = [375,400,425,450,475,500,525]   (7个)
```

全新 `7×7=49` 系统，并同样使用主模型和两级缓存身份。`h∈[375,525]` 仅为缩窄的合成条件标定域，不可冒称覆盖200–1000nm整个悬浮高度。选择原因须写`plan_lock.json`与源SHA，并在读取留出真值前冻结。

### S3-C. 数据与插值定义

保存一份跨模型条件的原始场库及一份**训练专用库**：

```
fields/D{D}_h{h}_n1p38/{Eref,Esca,Ibg,Itot,C,fine_x_nm,fine_y_nm,camera_x_nm,camera_y_nm,parameters,hashes}
train_grid_index.csv (role=train only)
holdout_index.csv (role=holdout,not imported by optimizer)
```

输出 `C=(Itot−Ibg)/Ibg` 保留符号/单位，逐相机像元算复场相干干涉后的强度；不按粒径调参考场/自由乘幅值。训练插值必须同时记录 **D、h 支持域**，可采用分片双线性 C 图样插值作为明确基线，并至少额外比较一种复场或数值相位一致的插值方式；不得只根据已知留出真值挑更好者。相位跃迁、高度振荡、符号过零区域均按真实数值评价。**优化回调只能调用冻结的离线库和数值插值，不得调用新BEM/render。**

其他V124非训练旧尺寸D={35,55,85,115,145,185}已参与历史审阅，不能在新 V125 的全新盲测中重复充当“从未见过”的新直径。可用于程序回归/候选设计但不用于挑选主方法及阈值后仍称盲测。

**S3返回**：`library/v125_Dh_train_fields.h5`、`library/train_grid_index.csv`、`validation/per_case_forward_replay.csv`、`logs/case_ledger.csv`、`logs/cache_hits.csv`、关键二维C图与固定D和固定h曲线。

## 6. **真正新粒径** + 非节点高度的独立物理留出（S4）

> **重要科研修正**：上一次助手建议的六个 D={35,55,85,115,145,185} 已在 V124 作为开发/留出被打开，不能再叫“全新D盲测”。本轮换成与V124所有18个整十训练粒径、六个旧留出均不同的固定粒径列表。仅在训练模型/评分/阈值/搜索冻结后，才打开这些真正新值的直接物理响应。

本批六个新留出（D,h,x,y 全部事先固定）：

| case | D_true / nm | h_true / nm（主9高度方案） | h_true / nm（备7高度方案） | x_true / nm | y_true / nm |
|---|---:|---:|---:|---:|---:|
| H01 | 37 | 362.5 | 387.5 | +56 | -84 |
| H02 | 63 | 387.5 | 412.5 | -112 | +28 |
| H03 | 93 | 412.5 | 437.5 | +84 | +112 |
| H04 | 117 | 462.5 | 462.5 | -56 | -112 |
| H05 | 147 | 487.5 | 487.5 | +112 | -56 |
| H06 | 177 | 537.5 | 512.5 | -84 | +84 |

每个 h 位于训练高度点之间；D不等于V124任何已打开的 D 集合且不在V125的7个训练D中。留出应使用**独立直接分层BEM的精细网格**（L1/1444、固定物理和光学参数），偏移在同一次解后通过验证合格的直接成像生成，因此 **6个BEM系统＋必要render**。不要使用训练库插值生成留出！若L1物理求解不合格，保留真实原因和未验状态，不用L0伪装L1。D/h/x/y真值只有验证器可访问；反演器只读匿名有符号图及背景、仪器公共信息。

新的留出数据初次生成后即按run ID冻结；模型和阈值不根据它们修订。若发现物理实现错误必须更新模型，该批由盲测降为诊断，下一轮需要**重新预注册新的**真正留出；不能同批换个随机种子把泄漏掩盖。

所有六例必须保存：D/h/xy真值（仅外部评分）、单帧D/h/xy估计、多盆地列表、边界/域外、拒判、绝对/相对D误差、C和Ibg图、数值资格、优化器完整退出轨迹/开销。六例不足以证明整个参数面泛化；结果必须逐例呈现而不是只给MAE。

**S4返回**：`validation/inversion_holdout_joint.csv`、`validation/holdout_profiles/`、`validation/holdout_gate_summary.json`、每例直接前向 H5/MAT 以及完整成功/失败记录。

## 7. D/h/x/y 单帧与共享 D 多帧反演（S5）

统一真实未知参数的模型：

\[
 C^{\rm model}_p(D,h,x,y)=\frac{I_{p}^{\rm particle}(D,h,x,y)-I_{p}^{\rm background}}{I_{p}^{\rm background}},
\]
\[
\widehat\theta_{1}=\arg\min_{D,h,x,y}\mathcal L(Y,F(D,h,x,y));\quad
\widehat D_{K}=\arg\min_{D,\{h_t,x_t,y_t\}}\sum_{t=1}^{K}\mathcal L_t(Y_t,F(D,h_t,x_t,y_t)).
\]

三条对照同一批输入：

- **M0**：只使用标量峰值/中心幅度，固定h450、居中，输出D；用于明确暴露忽略h和位置的偏差，不能当最终方法。
- **M1（主单帧）**：中央13×13有符号C图联合估计D/h/x/y，至少多起点+分段轮廓扫描；不根据真值选最好的起点或收紧参数域。搜索边界由训练网格和合法xy缓冲定，所有达到边界者单独标注。
- **M2（主短轨迹）**：同一颗粒的K帧共享**一个D**，每帧有自己的h/x/y；主光学版不使用生成器真值D、Dh或真实轨迹作为先验。只允许固定的公共相机/材料参数，不可每粒子独立自由调散射幅度、相位或每帧独立D。可另外以 `ORACLE_CENTERING_UPPER_BOUND` 标注真中心诊断，**正式指标不包括这一支**。

如果 D/h 本来就存在全局多解，最小残差很小也不保证唯一：保存**完整D条件轮廓**、候选h盆地和最低几种不同D的方案；对接近数值/噪声底限的候选标`AMBIGUOUS`，不可仅凭`1.05×fmin`比值判唯一。在似然模型尚未有真实概率校准时只能输出条件性兼容集合，不命名真实95%置信区间。

优化必须采用真正有限的搜索（例如所有训练网格粗筛前若干盆地→有界连续D/h/xy细化，冻结起点/收敛容差/最大迭代/最大目标函数调用），每次回调只使用离线库。将训练、留出、阈值开发的文件权限分离，避免 `h5.keys()` 或 glob 无条件读入holdout图。

**S5返回**：每个方法的全例 `accepted/rejected/ambiguous/boundary/out_of_domain/optimizer_failed`、D误差/轴向误差、耗时、搜索轨迹和被拒分母，不能只汇总成功例。

## 8. 噪声、空白、有限曝光和三维悬浮运动（S6）

### S6-A. 可用于含噪反演的统计目标

主值 `B100_p=10^3/10^4/10^5 e⁻/pixel` 指的是**理想线性期望背景**，并非用户实际CMOS已知电子数或满阱；100 μs是基准曝光，25 μs时同一固定光子通量下背景期望变为1/4，**不可简单给两种曝光设同一电子数**。空间非均匀背景按归一化 `Ibg_p` 模型保留，强度期望 `\mu_{p,t}=B_{p,t}[1+C_{p,t}(D,h,x,y)]`，先验证所有 \(\mu\ge0\)，然后前景 Poisson + 独立读噪；参考K=8独立原始空白共同估计背景；若多个目标帧共享背景，保留其噪声相关性。

推荐在**电子数域**比较 Poisson+Gaussian 的负对数似然或固定来源的高计数加权近似，而不是直接在C域使用干净图 `||Cobs−Ctemplate||/||Cobs||<0.10`。方差近似可在固定曝光下用：

\[
\operatorname{Var}(Y_p-\widehat B_p(1+C_p))\approx \mu_p+\sigma_r^2+(1+C_p)^2(B_p+\sigma_r^2)/K,
\]

不同帧共用同一 \(\widehat B_p\) 时不能假设独立。用于拒判的 null 模型比较、相对似然和数值误差/噪声门由**16个开发训练场景与100个开发空白**确定，冻结于 `validation/threshold_freeze.json`。100个独立验证空白**只评估**最终假阳性与置信限，不允许事后调阈值。如果没有真实标定的噪声参数/满阱，仍可做明确假设下的合成研究，`REAL_DETECTOR_VALIDATED=false`。

### S6-B. 本批真正的曝光实验

对每条轨迹，先以同一基准细时间网格生成保存的**三维** (x,y,h) Brownian路径及光学前向状态，主轨迹在h450nm附近开始；统计与生成**不允许**用光学真D=Dh作为反演器的输入。以相同轨迹做25与100μs的窗口平均，先输出无噪声`C25,C100`和静态真值模板的偏差，再加入固定通量噪声，区分运动模糊与光子损失。

- 细轨迹步长默认1.25μs；2.5μs积分用**同一条细路径**取稀疏/桥接子样本，不重抽路径。局部时间起点应覆盖每帧完整曝光窗，避免`round(ts/200μs)`；若帧中心固定在j×200μs，窗口左右各T/2。
- 示例模拟扩散系数 `\mathcal D=k_BT/(3πηD_h)`，本批 `D_h=D_opt` 仅作条件生成；近壁迁移率、磁场、流体驱动和真实包覆未知，结果明确标为理想布朗近似。对用户实际磁场周期运动，之后需要实测轨迹/驱动接口，不能从本次仿真宣称400Hz位移已测到。
- 真物理边界处如何反射须明确；**计算库h=350–550nm是数值支持域，不是物理边界**。路径若超出支持域或光学 x/y 余量，不能clip到边界，记录并拒判帧或整轨迹。留出物理域在计划锁定后不可依据成功样本再缩小。
- 默认12条模拟轨迹，每条8帧：D=55/115/185各4条；用相同轨迹在两曝光下生成`12×8×2=192`目标帧。这些D在V124已出现；而本次新增的D–h场只覆盖七个训练D，因此**沿D/h模型插值生成的轨迹观测只能标注`SHARED_LIBRARY_METHOD_DIAGNOSTIC`，不能称独立前向留出**。只有有真实不同来源的直接场轨迹观测才有资格另列独立物理验证。此批轨迹主要用于方法、时间积分和曝光消融；独立粒径多帧泛化留待新的直接物理真值。
- 主程序不能将实际帧直接用生成器真中心对齐。可做图像估计中心，再由M1/M2真实搜索；任何`ORACLE`对照与正式数据列严格分离。

### S6-C. 明确的合成样本与预算（前景、参考均计数）

| 用途 | 设定 | 计入曝光次数 |
|---|---|---:|
| 训练开发目标 | D=[50,100,160,200]×h=[375,425,475,525]共16条件；3个背景档×每档5次；每例1目标+8背景 | 16×3×5×9 = **2160** |
| 开发空白 + 独立验证空白 | 各100次，每次1个空白测试帧+8张背景参考 | 200×9 = **1800** |
| 新六例联合D/h留出噪声 | 6条件×3背景×5次；每例1目标+8背景 | 6×3×5×9 = **810** |
| 运动两曝光目标及参考 | 12轨迹×2曝光×8帧=192目标；每轨迹每曝光8张参考=192背景 | **384** |
| **名义总数** | | **5154** |
| **总上限** | 失败重算、追加必要验证均计 | **6000** |

注意：这张表是**拟执行计数**，不是V124历史运行数。随机噪声必须保存种子、真实逐事件账本和每次是否失败；**不补抽成功样本替换失败样本**。开发与留出使用不同种子域。针对1e5 e⁻/像元背景只能解释为理想未饱和探测情景，真实CMOS满阱/bit depth未知，不准称其设备可达。回放时从真实Poisson强度和8张参考帧核算C/似然，不只写数据生成计数。

### S6-D. 独立结果与统计

固定以上开发材料后，在六个新D/h直接物理留出及100独立空白上最终报告：各背景档的偏差、MAE、RMSE、D相对误差、有效样本接受率、拒判率、多解率、越界率、失败率，以及每个模型方法M0/M1/M2在同一批输入的配对差。100空白可计算精确二项置信上界，但仅对**这一合成空白分布**有效，不称实测仪器FPR。

主多帧方法如果不能在h支持域内得到足够有效帧，真实报告`INSUFFICIENT_VALID_FRAMES`；不得只报告成功的长轨迹导致结果偏好。没有实测噪声协方差时不要给出精密的实验95%测径区间。

### S6-E. 为用户下次重新实验预留**可直接输入图像**的反演入口

本轮除了验证数值，还须形成一个真正可调用的 `tools/v125_infer_experiment.py`（不存在时Codex创建），至少支持：

```bash
python tools/v125_infer_experiment.py \
  --model results/v125/library/v125_Dh_train_fields.h5 \
  --input <原始线性强度ROI.npy或.tif> \
  --background <同成像参数的线性空白ROI.npy或.tif> \
  --config config/effective_config.json \
  --out results/v125/experiment_interface_smoketest/
```

- 该入口**先在合成的真实直接物理场留出上做smoke test**；实验文件还未收到，不假装已经处理真实颗粒。支持原始单颗粒17×17线性ROI和同条件背景，也可显式支持带数据来源的 signed C 图；输入时要检查像元、大小、物方尺度、方向、线性/偏置和是否归一化。显示用min-max PNG、已做任意归一的幅度图一律拒绝直接当物理C。
- 输出逐颗粒记录：`particle_id,model_diameter_type,D_est_nm,h_est_nm,x_est_nm,y_est_nm,fit_loss,alternative_solutions,boundary,rejected,rejection_reason,assumption_hash,model_hash`，以及原/预测/残差对比图和原始数值。未知折射率、实际倍率、相机曝光未核准时，结果只能标记为`CONDITIONAL_MODEL_ESTIMATE_NOT_ABSOLUTE_MEASUREMENT`。
- **尤其区分静态有符号C与用户7.29历史约400Hz FFT**。后者观测为 `N=2001, Fs=5000 (script-recorded), k0=160→399.80009995Hz, C_k=2 X_k/(N Imean)`；它并不等于上文静态 `C=(I−Ibg)/Ibg`，也不等于对静态C简单乘sinc。Codex写`experimental_observable_contract.json`并提供两个独立观测入口/适配模式；实际用户若下一次采用约400Hz动态处理，必须先用真实磁驱动/轨迹→曝光强度→按同一个FFT提取算法生成 **动态D–Ck标定**，再做实验粒径反演。本轮未提供真实运动/触发参数时只完成接口与小型合成数学夹具，不冒充已完成动态真实标定。
- 该接口改动若只作用于输入解析或离线拟合，不需要新BEM；以保存模型内匿名留出确认能够输出完整逐例D、失败和多解，而不仅是可执行脚本存在。

## 9. 统一预算与分支规则（S0–S7，必须遵守）

本批批准**单独的新V125任务池**，不能把V124剩余64−60次叠加：

| 资源 | 总上限 | 主计划 | 缓存不可继承备用 |
|---|---:|---:|---:|
| 新 BEM 系统**尝试** | **64** | 7资格 + 48补训练 + 6直接留出 = **61**，余3 | 7资格 + 49全部小域训练 + 6直接留出 = **62**，余2 |
| 新光学位置/render尝试 | **240** | 一个新物理条件至少一个render，含负例/偏移/精细对照、失败重试 | 同池 |
| 合成相机曝光事件 | **6000** | 名义5154（前景＋参考均计） | 无效物理分支不伪造帧 |
| 重物理并发 | **1** | 不并行起两个MATLAB大型求解 | 同池 |
| 总研究执行窗 | **12小时** | 最后30分钟留给归档和外部验证；当前任务时间从实际启动时算 | 同池 |
| 独立留出 | 6个直接物理(D,h) | 不从训练模板制造，模型先锁 | 同池 |

**系统尝试**包括报错、内存失败、实际建系统后作废的计算；**render尝试**包含失败的光学调用，一次batch含N个位置按N次扣，不能只算外层函数调用1次。纯Python插值/优化器回调不得在背后触发BEM/render。必须按实际工作站日志记录 `attempt_id/start/end/config_sha/source_sha/phase/elapsed_s/status/reason`。补算资格、模型修订、放弃的格子都扣资源。

本批建议按**S0身份→S1实现→S2最多七个物理资格→S3四格前向先导并自动补满训练→冻结训练模型→S4六个新留出→S5二维联合反演→S6噪声/运动/多帧→S7归档**进行。只要没有硬门阻断，自动连续推进。不能因一个S1测试绿、一个D100、一个60行表而自然终止。

### 明确的部分失败处置

- **原V124严格n匹配门失败**：保持历史 FAIL，新诊断如实记录；如果主路径没有可信条件范围，暂停**依赖新物理资格的**S3/S4，继续独立Mie、数据身份修复和已合格旧库回放，形成PARTIAL。绝不把旧阈值从1e-10改成有利值后写“原门通过”。
- **材料、NA、总倍率仍为假设**：允许模型内**条件仿真**继续；全部研究结论带`ASSUMED_OPTICS/ASSUMED_MATERIAL`，真实实验绝对粒径验证继续NO。用户后续换参数后按依赖树重算。
- **改动BEM物理实现使旧库失效**：事先冻结七高度备用，最多49新训练；不在读取留出真值后回退择优。
- **某个格点BEM失败**：保存尝试、错误和状态；同级下一合法格点继续；冻结时训练格缺失则不能声称全D/h网格完成，反演只在实际矩形完整子域内进行，越界拒判。不能静默插值跨缺口。
- **平移回归不合格**：先做静态居中D/h结果、重新生成有限直接平移参考；所有非零位移和运动关联评价暂停为`UNQUALIFIED_SHIFT`，不用旧错误近似产生成功粒径。
- **时间/预算到顶**：保存已经完成的全部合格格点和失败原证据，继续**能离线完成的**模型检验、留出回放/档案；最后必须输出`PARTIAL`真实状态，不能为了显示COMPLETED补零表或改标签。

## 10. 本轮程序入口：Codex需要**实现/修改并真正运行**，不是现成脚本承诺

下面名称是要求Codex落实的**可执行入口**，存在时修复并标记版本，不存在时创建。不要把建议文件名当成已经存在。全部使用绝对化 `--repo --config --out`、内容SHA与结构化日志：

```text
config/v125_science_config.json                       # 本包已给出建议配置，复制至项目目录并冻结
source/v125_physical_forward_adapter.m                 # 从V124有限修改：真实根路径、配置+缓存键、求解和render账本
source/v125_mie_reference.m / tools/v125_mie_fixed.py  # 独立Mie复数参考
 tools/v125_forward_shift.py                           # 复场移位与边界/直接render对照
 tools/v125_exposure.py                                # 纳米/秒单位、3D细轨迹、共享随机路径曝光
 tools/v125_model_library.py                           # 训练/holdout物理隔离；D/h插值；字段SHA
 tools/v125_invert_particle.py                         # M0/M1/M2、噪声目标、全局多盆地和拒判
 tools/v125_infer_experiment.py                      # 单颗粒线性ROI+背景接口，未知实验参数拒绝绝对声明
 tools/v125_run_all.py                                 # 单一协调器，断点续跑，实际预算，多阶段状态
 tools/v125_validate_science.py                        # 从实际原场/数组独立重放并检验科学状态
 tools/v125_archive_check.py                           # 完整成员、原字节、来源和外部回执
```

推荐**执行顺序命令**（Codex先真正实现入口，不能用示例语法冒充已运行）：

```powershell
# 原工作站仓库内、Python/MATLAB环境实际验证后
python tools/v125_run_all.py --repo . --config config/v125_science_config.json --out results/v125 --resume
python tools/v125_validate_science.py --repo . --out results/v125 --strict
python tools/v125_archive_check.py --zip results/v125/iscat_v125_return.zip --receipt results/v125_external_receipt.json
```

在主入口的状态里依次记录`S0,S1,S2,S3,S4,S5,S6,S7`：`execution=NOT_STARTED/RUNNING/COMPLETED/PARTIAL/BLOCKED/FAILED`、`validation=PASS/FAIL/NOT_EVALUATED/INDETERMINATE`、`evidence=COMPLETE/PARTIAL/MISSING`，另列关键 `dependency_blockers[]`、`numeric/physics/experiment` 严格分开。**不许把归档机械PASS等于科学PASS。**

## 11. 必须交付的 V125 实际返回包（S7）

**唯一报告 ZIP**：`iscat_v125_return.zip`。Codex要在GitHub发布可读的 `status.json`、`review.md`、关键 CSV/图和真实源码，同时保留大原数组位置及可追溯 SHA。不能只交运行日志/PNG/文本摘要；至少应在ZIP中保留完整可独立重放的D/h关键原场或等价Eref/Esca系数，以及**全部有效D/h的C/Ibg数组**。物理BEM解原MAT若太大无法入包，必须明示工作站路径+SHA/bytes、源配置和不能独立远程重放的限制，不得冒称它们在包内。

```text
iscat_v125_return.zip
  00_START_HERE.md
  01_V125_Codex_完整执行合同.md
  status.json                          # 本轮真实阶段机器状态（不是旧v124）
  review.md                            # 已完成及失败科学范围、真实结果统计
  config/effective_config.json         # 含每参数来源类型和真实执行环境
  logs/source_identity.json
  logs/actual_commands_and_errors.txt
  logs/execution_ledger.csv
  logs/resource_budget.csv
  logs/cache_hits.csv
  validation/v124_intake.csv
  validation/s1_regression.csv
  validation/s1_red_green.json
  validation/numerical_qualification.csv
  validation/plan_lock.json
  validation/forward_replay.csv
  validation/holdout_gate_summary.json
  validation/inversion_holdout_joint.csv
  validation/inversion_methods_comparison.csv
  validation/noise_per_trial.csv
  validation/blank_per_trial.csv
  validation/exposure_motion_per_trial.csv
  validation/rejection_ambiguity_summary.csv
  experimental_observable_contract.json # 静态C与约400Hz复FFT两种观测不可混
  experiment_interface_smoketest/       # 真正回放的匿名直接物理留出
  validation/holdout_profiles/*        # 所有成功/失败，多盆地和条件轮廓
  library/v125_Dh_train_fields.h5      # 全部合格训练C/Ibg+相关复场，固定坐标/元数据
  library/v125_direct_holdouts.h5      # 直接独立物理留出；严格隔离训练读取
  library/train_grid_index.csv
  library/holdout_index.csv
  figures/contrast_vs_D_at_heights.png
  figures/contrast_vs_h_at_D.png
  figures/D_est_vs_D_true.png
  figures/ambiguity_and_rejection.png
  figures/exposure_noise_comparison.png
  source/                              # 实际执行入口、MATLAB代码、依赖版本、SHA
  manifest_sha256.csv                  # 所有ZIP普通文件（不含清单自身）逐成员SHA，精确集合
```

若部分阶段确实被阻断，`status`列出明确原因，不能创建零填数据表模拟成功。对无可执行阶段可跳过对应物理文件，但**状态、配置、账本、审查、资格记录和失败证据必须存在**。

**机器状态与资源CSV字段格式必须具体冻结（供随包机械检查器使用）**：

```json
{
  "schema": "iscat125.status.1",
  "task_id": "V125_SUSPENDED_DH_CALIBRATION_AND_BLIND_VALIDATION",
  "fixed_source_commit": "384a52304f77490c410d395dd150e0ea82760d1f",
  "stages": {
    "S0": {"execution": "COMPLETED", "validation": "PASS", "evidence": "COMPLETE"},
    "S1": {"execution": "NOT_STARTED", "validation": "NOT_EVALUATED", "evidence": "MISSING"},
    "S2": {"execution": "NOT_STARTED", "validation": "NOT_EVALUATED", "evidence": "MISSING"},
    "S3": {"execution": "NOT_STARTED", "validation": "NOT_EVALUATED", "evidence": "MISSING"},
    "S4": {"execution": "NOT_STARTED", "validation": "NOT_EVALUATED", "evidence": "MISSING"},
    "S5": {"execution": "NOT_STARTED", "validation": "NOT_EVALUATED", "evidence": "MISSING"},
    "S6": {"execution": "NOT_STARTED", "validation": "NOT_EVALUATED", "evidence": "MISSING"},
    "S7": {"execution": "NOT_STARTED", "validation": "NOT_EVALUATED", "evidence": "MISSING"}
  },
  "scientific_claims": {"EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED": false}
}
```

示例中的状态值**仅说明数据结构，不能复制为真实执行结果**。真实 `status.json` 中每阶段填入当前状态、运行任务、失败原因及对应结果路径。`logs/resource_budget.csv` 必须至少含列 `resource,attempted,limit,failed`，其中资源键精确为 `bem_system_attempts`、`optical_render_attempts`、`synthetic_exposure_events`，对照限制64/240/6000；合成帧数据除实际生成事件外还应记录 `foreground_or_reference`、`exposure_id` 和 `source_seed`。这不替代另行的原始逐事件账本。

**校验顺序**：1) 冻结所有产物、生成ZIP；2) **ZIP外**独立脚本打开原ZIP、查CRC、成员唯一、路径安全、清单逐字节SHA与成员集合闭合、来源、`status`和预算；3) 科学脚本**从ZIP数据**抽样重放 `Eref+Esca→逐subpixel强度→像元平均→C`，读至少一个旧缓存节点和一个新D/h节点，至少一个真正新holdout进行D/h/xy反演重算，对失败分支核对无伪PASS；4) 在ZIP**外**写 `results/v125_external_receipt.json` 记录真实ZIP SHA256和检查结果，不再修改ZIP。机械与科学两个 verdict 要分开，任何硬科学失败不得以`archive_verified=true`掩盖。

本包附带 `tools/check_v125_bundle.py` 是**独立的最小机械检查器**，用于从最终ZIP验证结构与SHA，**不是**整套科学验收器；Codex必须实现额外从H5复算物理和盲测的科学检查。

### 返回 ChatGPT 审查用的四个必备入口

1. **本轮固定GitHub `v125`提交SHA**（没有成功发布时说明原因，提供原ZIP，不可伪造分支）；
2. `status.json`与`review.md`可通过 GitHub raw 直接读取的固定提交地址；
3. `validation/inversion_holdout_joint.csv`、`validation/numerical_qualification.csv`、`logs/resource_budget.csv` 的原始完整行；
4. 唯一真实 `iscat_v125_return.zip` 及ZIP外 `v125_external_receipt.json`，必要的H5/MAT阵列已经包含，或严格声明大文件未随包。

**本批准入/结果命名**：
- `FORWARD_NUMERICAL_CONDITIONAL` 或具体 `FAILED`（V124旧严格匹配门仍FAIL）；
- `SYNTHETIC_FIXED_HEIGHT_CALIBRATION`（继承V124、作用域有限）；
- `SYNTHETIC_DH_JOINT_INVERSION_VALIDATED_WITHIN_TESTED_DOMAIN`（**只有真正六例D/h/xy新物理留出和对应门通过才可用**）；
- `SYNTHETIC_EXPOSURE_AND_NOISE_EVALUATED`（只有真实轨迹曝光/噪声代码/原数组通过才可用）；
- `EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false`（用户后续独立实验及样品真值未接入，保持false）。

## 12. 结束约束及给Codex的最后一句话

**完成标准**不是新增多少版本，而是 **物理有效的有限 D–h 库 + 新直径/新高度/真实横移的直接合成留出 + 明确的多解/拒判 + 能用到单颗粒图像中的反演程序**。全部测试按数值范围如实报告；多解和性能差都属于科研结果，**绝不为了漂亮的论文指标删除困难高度或弱信号粒径**。独立样品结构/光学常数/量尺未核实前，所有直径均为明确模型下的光学等效直径。

> **Codex执行**：从固定V124真实数组与MATLAB求解出发，先修S1和S2，再用统一64次新系统预算补全D/h库、冻结模型、运行六个全新D/h/xy物理留出，并在6000次合成曝光预算内完成统计与多帧。局部受阻只停依赖分支；其余可完成任务持续到结果和ZIP终验。请严格按照S0–S7实际执行，并返回唯一可审查证据包；**禁止只回复“代码写完”“等待参数”或“理论应该可行”。**

---

**文件性质**：完整科研执行合同；文内V124的数值明确来自已发布固定源码/CSV和独立算术复核，V125各项工况、预算、目标门都是**拟执行规定，不是已经得到的结果**。本文件需与机器配置及外部物理准入共同解释，不是对最终实验测径精度的保证。
