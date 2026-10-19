# 反射式 iSCAT 磁纳米颗粒测径：V116 独立审查与 V117 连续执行合同

**审查日期：2026-10-19。**

**审查对象：**`yyyyzoey/iscat-handoff`，V116 固定发布提交 `ae7f479775910654eb10b984ec7076b544ab0a61`，其直接父提交为 V115 发布提交 `59800bae2a6b5c0b37531c09b6cc97158fad1d5f`。

**任务性质：**读取用户上传的 `progress(4).md` 全文，审查固定 V116 源码、状态和数据，并制定下一轮方案。本文件不是 V117 已执行报告，不是新的 BEM、真实装置仿真或实验粒径结果。

**总体裁决：保留已有数值成果；V116 不能无保留签为全部验收完成。** 原仓库自报 `SOURCE_FORENSICS_AND_ACCEPTANCE_SEALED`，本次独立审查建议另外登记 `REVIEW_PARTIAL_ACTION_REQUIRED`：来源门未落实洁净条件，异常测试有可复现的假阳性，生产接口仍有具体合同缺口，最终 ZIP 的独立归档证据未提供到本次可读取来源。与此同时，73 项旧核心来源没有发现变化，48 BANK 内容核对通过，576 项保存探针桥接已在本次独立重算中通过。不得将这些不同层次合并为“全部错误”或“全部通过”。

---

## 第一部分：项目目标和本轮事实

### 1. 真正的任务及当前阶段

研究目标是在自搭反射式 iSCAT 装置中，用与实验处理一致的单颗粒复调制对比度，建立有物理约束、有校准和独立验证的粒径估计。粒径定义必须区分核心直径、包覆外径、流体力学直径和模型限定的光学等效直径。

当前已完成的是规定运动、演示光路和材料假设下的 48 态数值银行及大量后处理工作。银行为三尺寸 `{30,60,100}` nm、两焦面 `{450,550}` nm、两规定运动 `{M200,M400}`、四振幅 `{5,10,15,20}` nm；24 个端点状态是参考，24 个中间状态只作查询。不能把中间查询加入参考，也不能将模型内同 D 标签匹配称为实验测径精度。

真实装置的物方量尺、光路/参考场、曝光与同步、样品材料/结构及运动约束尚未完整接入。520 nm 是用户已确认值；65 nm/px 是演示值；旧 56 nm/px 是历史反推值；5000 fps 是脚本设置；实验样品标称 100 nm 不是某个粒子的独立尺寸真值。不要混入另一项目 `ustbfjw/keyan` 的记录。

本次维持：

| 层次 | 本次裁决 |
|---|---|
| 48 态历史演示银行 | 冻结并保留；没有发现本轮数据污染 |
| 保存探针的数值谱桥接 | 本次独立复算通过，限固定输入与指定像元 |
| 软件接口固定正例 | 有效成果保留；已发现的异常路径需修复 |
| 真实装置相对复 C 前向 | 当前输入不足，NO-GO |
| 真实电子/DN 绝对计数 | 当前输入不足，NO-GO |
| 绝对粒径验证 | NO-GO；`single_particle_diameter=NOT_ESTIMATED` |
| P0 / rule7 | P0 保持 OPEN；本文件不新增 rule7 计算授权 |

### 2. 本次真正执行的独立核查

本次实际读取和检查了固定 Git 提交、父链、V116 执行合同、生产接口、边界测试、桥接、来源与归档驱动、元数据和物理准入文件；下载并核查了 48 个 BANK 的原始 MAT 字节与保存探针 NPZ。没有运行 MATLAB/BEM、没有新增散射位置、没有生成新的物理时序、没有读取实验 BMP/视频、没有重算旧 5040/852/14400/1680 统计。

本地独立复验环境是 Python `3.12.14`、NumPy `2.3.5`、SciPy `1.17.0`。这与执行者报告的 Windows Python `3.11.7`、NumPy `1.26.4`、SciPy `1.11.4` 不同，因此本文件所列数值明确属于本次独立复验，不冒充工作站原生重跑。

生产模块 `tools/observation_operator.py` 的固定 Git blob 为 `3d00cdb5c5083dfd771d9f6b7101b374330b2042`，原文件 SHA-256 为：

```text
5acb61a5619b995827038c71cdc91d5278c348ff3bc484ae52737b0056b349c5
```

保存探针 `analysis/v093_probe_evidence.npz` 为 137,570 bytes，SHA-256 为：

```text
83c7aa2325f1ed380f2a9f7dc0bd7ba03e11dd98faf047ec3b24cc2efc8d6fc4
```

### 3. 可以正式保留的结果

#### 3.1 来源和 BANK 内容

| 本次独立核查 | 结果与范围 |
|---|---|
| 73 项角色/case 多重集合 | 精确等于 48 BANK + 24 BASELINE + 1 NPZ |
| 73 项 Git blob 和字节长度 | 与固定 V116 tree 一致 |
| 73 项源与 `review_inputs` 对应副本 | Git blob 全部一致 |
| 73 项源与固定 V113 对应源 | Git blob 全部一致 |
| 48 BANK 原字节 SHA-256 | 与 V116 清单全部一致 |
| `C/X` 原 dtype 和 shape | 全部 `complex128`，`(3,41,41)` |
| `Imean_map` 原 dtype 和 shape | 全部 `float64`，`(41,41)` |
| case、N、Fs、bin 和振幅字段 | 全部符合固定合同 |
| 有限性与掩码公式 | 全部通过；每个 BANK 均有 1681 个有效像元 |
| `C−2X/(N·Imean)` | 本次数组运算的最大绝对残差为 `0.0` |

24 BASELINE 在本次采用 Git 对象身份、对应副本和长度核验，没有重新下载其内部数组做新的数值分析。BANK 的恒等式是内部代数一致性，不是独立电磁物理正确性。

#### 3.2 576 项桥接

192 条保存时序均为原始 `float64`，shape 为 `(2001,)`，有限、正均值，键恰等于 48 个 case × 4 个既定像元。三个频点产生恰好 576 个唯一桥接键。

本次实际调用未修改的生产 `production_fft`、独立 `independent_dft` 和原桥接脚本，并另外核对两算法之间的差及银行均值：

| 比较量 | 本次最大绝对误差 | 门槛 |
|---|---:|---:|
| `X_FFT − X_bank` | `6.581525322081668e-15` | `<1e-11` |
| `X_DFT − X_bank` | `6.5762010206102364e-15` | `<1e-11` |
| `C_FFT − C_bank` | `4.808666304334051e-16` | `<1e-11` |
| `C_DFT − C_bank` | `4.805342546375331e-16` | `<1e-11` |
| `X_FFT − X_DFT`，同一保存数组 | `1.734723475976807e-17` | `<1e-11` |
| `C_FFT − C_DFT`，同一保存数组 | `1.939479807224432e-18` | `<1e-11` |
| `fsum(series)/N − Imean_bank`，192 条 | `8.673617379884035e-18` | `<1e-12` |

本次原桥接脚本返回 `576/576 PASS, complete=True`。这些结果可以保留。576 不是 576 个新物理工况，也不是 576 颗实验粒子；四个保存像元的数值复验不等于 41×41 全 ROI 独立物理时域验证。

#### 3.3 正常软件行为

本次重放 V116 边界测试，仍是 12/12；旧 12 组测试和 4 项变异也全部通过。`run_roi` 的每求积时刻一次完整 `(P,Q)` 帧、按像元归约 Q 个子像元、不混相邻像元、合法标量/向量广播及三种单位模式确实存在并有效：

\[
\overline I_p\longrightarrow\mu_{e,p}=\kappa_pT\overline I_p
\longrightarrow\mu_{DN,p}=b_p+g_p\mu_{e,p}.
\]

V116 的 P=1681 检查只检查了 `(50,1681)` 的软件维度，不是完整 2001 帧的真实相机物理验证。

### 4. 本次发现的确定问题

#### 4.1 Git 根因方向正确，但运行源与发布身份又被混淆

真实链如下：

| 身份 | 提交 |
|---|---|
| V113 发布 | `89a5b353ba104a3dbf0764816933739f8edda33b` |
| V114 主提交 | `1548ea810b9870251dc57e37ddec32ad8be68e42` |
| V114 红侧证据补充、最终 tip | `7a9102d5f8c6f98305ed9b10279083de96be66e6` |
| V115 发布 | `59800bae2a6b5c0b37531c09b6cc97158fad1d5f` |
| V116 发布 | `ae7f479775910654eb10b984ec7076b544ab0a61` |

表中每个后继的直接父就是上一行。V115 失败运行时，源 HEAD 是 `7a910…`，其父是 `1548…`；V115 发布提交才是 `59800…`。V116 取证运行的源 HEAD 为 `59800…`，父为 `7a910…`。

因此旧驱动把“V113 是祖先”误写成“V113 是直接父”，确实会错误拒绝。但 V116 `review.md` 写“V115 tip 的 HEAD^ 是 1548”及“同一 HEAD 59800 上的历史失败运行”不成立；驱动第 106–118、139–140 行也把 `1548` 的主提交/addendum 身份写混。应保留历史原件，在新纠正记录中区分 `base/source commit`、`execution code identity`、`release commit`。

V116 中 later-green ZIP 的 SHA 和说明有硬编码部分，不能据此断言那个历史 green 运行的命令、工具、时间、目录和实际 ZIP 已完全闭合。

#### 4.2 A 来源门漏掉洁净条件和部分实质核验

`run_v116_all.py` 第 99 行计算 `porcelain_clean`，第 229 行的 A 门却没有使用它。本轮日志显示三个未跟踪文件：

```text
?? tools/run_v116_all.py
?? tools/v116_archive_check.py
?? tools/v116_operator_boundary_tests.py
```

故它不是 V116 合同要求的干净源工作树，不能签“clean-worktree gate PASS”。当前 dirty 日志只涉及三个新工具，不构成旧银行污染证据。

此外，V116 A 检查只在传入 mask 选出的区域计算 C 恒等式，未重建 mask 公式；未完整检查 shape；`review_inputs_match=MISMATCH` 只是填表，没有进入 issues；BANK/BASELINE 记录了现算 blob，却没有逐项强制匹配固定提交的预期 blob。它们是验收器漏检。本次独立检查已证明现有输入实际正确，不应为此重做物理。

#### 4.3 T11 的实际布尔值被丢弃，存在假阳性

`tools/v116_operator_boundary_tests.py` 第 199–202 行先保存 `(label, bool_result)`，随后却执行：

```python
all(ok for ok, _ in checks) and calls_after == 0
```

`ok` 在这里是非空测试名称，不是真正的布尔值。本次从原文件 AST 抽取并执行未经修改的 `t11`，只改变它调用的 `run_roi`：

| 被测入口行为 | 原 T11 返回 |
|---|---|
| 正常实现 | `True` |
| 回调前直接抛 `TypeError` | `True` |
| 回调前直接 `return None` | `True` |

三者均打印“all static rejects unified; callback calls=0”。所以当前 12/12 不能证明这些异常守卫可靠，`NO_PRODUCTION_PATCH_REQUIRED` 结论需要撤回为待修复。修复不仅是换解包顺序，还应逐例验证正确异常类型、错误代码及静态阶段零回调。

#### 4.4 生产入口仍有可重复的合同缺口

最小例使用两帧时间 `[0.0, 0.0002]`、曝光 `1e-4 s`、常数强度回调。结果如下：

| 输入问题 | 实际结果 | 应修正内容 |
|---|---|---|
| `run_pipeline` electron 的 `kappa=-1` | 64 次回调后才 `OperatorError` | 所有可确定静态参数在积分前核查 |
| `run_pipeline` DN 缺 gain 或 offset | 各 64 次回调后才拒绝 | 同上 |
| 上述三个问题在 `run_roi` 中 | 均 0 回调、正确 `OperatorError` | 保留这些已正确路径 |
| `run_roi` 的 `spatial_weights=[1.0]` | 0 回调、裸 `TypeError` | 统一 shape 校验与领域异常 |
| `run_roi` 的 `kappa=['bad',1.0]` | 0 回调、裸 `TypeError` | 向量元素复用标量类型校验 |
| `run_roi` 的 `kappa=[True,1.0]` | 被接受，True 当作 1 | bool 规则应与标量一致 |
| 回调自身抛 `ValueError` | 一次回调后裸 `ValueError` | 封装为带阶段/时间信息的 `OperatorError`，保留原因 |
| ROI partial-grid 计数乘法溢出 | 正常返回 Inf series/mean，`dft=None` | 在任何 partial/full 返回前检查转换结果有限性 |

最后一项的有限输入为 `P=2,Q=1,T=1e-4,kappa=1e308,I=1e10`。它是有限性合同的压力反例，不表示实验装置具有这种数值规模。此处并没有声称 full-N 已把 Inf 谱认证通过。

#### 4.5 桥接当前数值正确，但应补两个显式门

原桥接第 75–76 行的 PASS 确实包括原 dtype、有限、正均值和两条算法各对银行的四个复数差；第 103–114 行还强制完整唯一键集合。不能再指责它“完全没检查 dtype/finite/键集合”。

但它没有将以下量显式并入桥接 PASS：

1. 同数组 `FFT−DFT` 的原始 `<1e-11` 门；两者各离银行 `<1e-11` 只能推出彼此 `<2e-11`。
2. 保存时序均值对银行 `Imean_map` 的 `<1e-12` 门。

本次已经直接核实当前数据这两项也满足原门。下一轮把这两项写进正式校验即可，不把缺守卫改写成旧数据失败。

#### 4.6 D 准入门只是数量检查

`run_v116_all.py` 第 405 行实际为：

```python
ok_d = len(items) == 16 and len(inherited) == 14
```

16 项参数是硬编码清单；分层根据英文描述的 `startswith`；物理 GO 全部硬编码 false。因此当前 D=true 只说明清单生成和数量检查通过，不等于来源、单位、有效批次、边界、生效语义或证据等级通过完整准入审计。当前 NO-GO 结论仍然合理。

下一轮应使用稳定参数 ID 和显式依赖，不应把路线 A 和 B 同时列作必需；`nominal_D=100` 的银行 case 来源也不能代替 7.29 样品记录。

#### 4.7 归档证据不齐，不等于已损坏

固定 V116 tree 中未发现本轮真正的 `iscat_v116_return.zip`、最终外部 receipt/archive_check/post_archive_summary，以及 fresh-run `tables/v116_bridge576.csv`；仓库 Releases 查询为空。存在最终 SHA 的文字报告和桥接摘要，也存在旧 `tables/v115_bridge576.csv`。

本轮被报告的 final ZIP SHA 为：

```text
e8a4d8cbe327c503f8871b4750a11542fb97ee8ab68819a92f3589365f981f50
```

没有取得最终 ZIP 的实际字节，不能以该字符串替代 CRC、成员、manifest 和外部 receipt 的独立核验。不要断言 ZIP 根本不存在；它可能仍在工作站或其他未交付位置。

`status.json` 内 `archive=PRE_ARCHIVE_VERIFICATION` 符合两阶段归档协议，本身不是错误。12 项 verifier 自测中的 positive control 是 provisional ZIP 的机械完整性阳性；它的 exit=2 也不自动代表自测失败。最终全门阳性仍需最终 ZIP 的外部 checker 结果。

还需修复协调器字段传播：`run_v116_all.py` 第 687–696 行把 checker 的总退出成功当作 `archive_integrity`。checker 的总成功实际上是 `archive_integrity AND numerical_accepted`；今后数值失败而 ZIP 完好时，不应将完整性误记为 false。

两个关键工具的 SHA 差异已经排除误报：Git LF 字节转换为 Windows CRLF 后，driver SHA 精确等于 `74ce0748…`，checker SHA 精确等于 `c6b5eccb…` 的工作站记录。不能称为源码篡改。

---

## 第二部分：科学判断和下一物理先导的设计

### 5. 为什么当前仍不能从约 400 Hz 幅度直接得到绝对粒径

正式观测仍为：

\[
\bar I_p=\frac1N\sum_{j=0}^{N-1}I_{p,j},\qquad
X_{p,k}=\sum_{j=0}^{N-1}(I_{p,j}-\bar I_p)e^{-2\pi i k j/N},\qquad
C_{p,k}=\frac{2X_{p,k}}{N\bar I_p}.
\]

这里 N=2001，Fs=5000，零基 k={80,160,320}，主频点为 `399.800099950 Hz`，不是恰好 400 Hz 正弦拟合幅度；MATLAB 对应索引为 81/161/321。保留原第四维时间语义、窗口和均值有效 mask；不能用显示 PNG 的 min-max 值恢复 C。

局部数学例子：若规定横移 `x(t)=x0+a cos(ωt)`，在位移足够小且强度对位置可微时：

\[
I_p(t)\approx I_p(x_0)+aI'_p(x_0)\cos\omega t
+\frac{a^2}{4}I''_p(x_0)[1+\cos2\omega t].
\]

因此 200 Hz 位移的二阶空间响应可以产生 400 Hz 分量，400 Hz 位移的一阶响应也可以产生同频分量。两者分别依赖 `a²I''/4` 与 `aI'`。这只是说明参数混杂的局部展开，不是对真实磁运动的认定，不是用 D³ 替代 BEM 的理由。

实际 D 还与 n/k、核心/壳层、焦面、轴向高度、参考场和运动等共同影响 C。原 D={30,60,100} 三个粗标签不能支持精密的局部 D 导数、粒径分辨率或置信区间。

后续应在真实输入约束下，比较改变 D 的响应能否被允许的其他参数变化抵消。如果抵消后仍能在实验误差内产生相同观测，应输出可行范围或条件模型结论，不能强制输出一个“唯一绝对 D”。这项未来可辨识性分析不授权本轮暗中增加 D 节点。

### 6. 曝光、相位和暗偏置是当前实际问题

对矩形曝光且以曝光中心为时间标签的连续强度分量，曝光传递因子为：

\[
H_T(f)=\frac{\sin(\pi fT)}{\pi fT}.
\]

下表仅为本次解析数学计算，T 都是假设值，不是相机实际设置：

| 假设曝光 | 真实 200 Hz 强度分量 | 真实 400 Hz 强度分量 | 真实 800 Hz 强度分量 |
|---|---:|---:|---:|
| 50 μs | 0.9998355147 | 0.9993421562 | 0.9973701828 |
| 100 μs | 0.9993421562 | 0.9973701828 | 0.9895056210 |
| 200 μs | 0.9973701828 | 0.9895056210 | 0.9584184823 |

例如假设曝光 200 μs 时，真实 400/800 Hz 分量的幅度分别约减少 1.0494%/4.1582%。这说明曝光会改变频率间比例，不能用同一个全局比例因子处理。

**不能直接给保存的三个 DFT bin 各乘一个 sinc 来冒充曝光后结果。** 有限 N 的非整数周期记录存在正/负频率泄漏，有限窗均值也要重新计算。正确顺序是先按曝光窗积分强度，再按冻结采样和 DFT 计算 X/C。先平均复场再求平方也不正确。

固定曝光、线性相机、恒定响应下，若 `DN=b+gκT I`，则对非零频：

\[
C_{DN}=\frac{\overline{DN}-b}{\overline{DN}}C_I.
\]

所以即使未知的常数 gκT 可在零偏置相对 C 中抵消，暗偏置 b 仍改变分母。逐像元不同的 b 还会改变复图形状和 mask。不能把暗偏置与绝对 κ/g 全部后置。

相机暗场、无颗粒光学空白、颗粒 B-off 是三个不同对照。新暗校正后的 C 和旧源脚本直接输出的 C 应分别命名、分别冻结；不要悄悄改变旧观测量后继续声称同一合同。

### 7. 真实输入应按用途取得

| 输入组 | 优先取得的记录 | 用途和证据边界 |
|---|---|---|
| 光学量尺与光路 | 物方 nm/px 的独立标定及误差；物镜型号/NA/浸液；照明与偏振；参考路径或可验证约束 | 不使用演示 65 或历史反推 56 代填 |
| 相机与时间 | 该批采集配置、曝光、触发起止/中心含义、时间戳/掉帧记录、暗场偏置 | Fs 脚本常数不自动证明实际时钟；不擅自吸附时间轴 |
| 样品与几何 | 批次、材料/包覆/形状/团聚；目标尺寸定义；介质/基底；高度与焦面或可信范围 | 文献 Fe₃O₄ n/k 是材料模型来源，非批次实测 |
| 运动路线 A | 有独立空间量尺和共同时间基准的轨迹及误差，z 必须有测量或有依据的范围 | 不用同一未知 D 的幅度反推出轨迹再自证 D |
| 运动路线 B | 同步 B(t) 矢量、梯度、磁性/黏性、固定或接触边界 | 仅当由磁场预测运动时必需；路线 A 与 B 是或关系 |
| 绝对计数及尺寸验证 | κ；DN 模式另需 g/b；尺寸定义适配且误差可审查的独立参考、空白/B-off、留出样本 | 批次均值不赋作每个粒子真值；标称值不代替独立表征 |

520 nm 已确认，不重复索要。有效的证据可以是可审查的测量和误差记录、采集日志、适用的厂商精度或有依据的文献范围，不一概要求“证书”。只有假设时，必须标为条件模型；关键参数既无值又无可信界限时，对应真实前向保持 NO-GO。

均匀各向同性球的光学模型若严格不依赖取向，取向可以写 `NOT_APPLICABLE` 并给出理由；不要写成“实测取向为 0”。真实非球形/团聚或磁动力学需要取向时，不能滥用这一例外。

### 8. 后续真实物理先导：最多两个工况，单独预注册

这部分是设计，不是本轮自动执行权限。V117 当前默认新物理额度仍为零。真实输入与具体物理批次安排到位后，可开一个有界先导：

1. **工况 P1：**一个有独立尺寸约束的参考样品，在实际量尺/光路/曝光和受约束运动下做前向；预先分开用于共同参数确定的窗口和留出验证窗口。
2. **工况 P2：**只有必要且输入齐全时，增加一个预先选定的验证工况，例如同一参考尺寸下已知焦面或轨迹变化，或者第二个独立参考样品。预注册时只能确定一个目的，不能看到 P1 残差后随意挑选最好通过的 P2。

每工况最多生产设置/参考设置各一份顶层前向，总计最多四个顶层计算单元；能复用已有匹配复场时扣除新求解。不得将“两个工况”暗中扩成 5–9 个 D 节点或噪声大扫描。

顶层数量不是计算资源上限。启动前必须展开实际 BEM 调用数、变化的几何/材料、位置或轨迹支持点、曝光求积节点、探测像元和子像元数、峰值内存、墙时与重试次数；未填写这张预算表，不启动物理计算。生产与参考只是更细离散对照，不能自称绝对真解。

必须先判断 P0 开放问题是否落在拟用调用路径上。若有关联且误差无界，相应路径不放行；若能证明不涉及，或虽有关联但已有独立误差界限且满足本先导预注册预算，可在该明确范围内做条件性先导，P0 全局仍 OPEN。FFT 软件门不能关闭 P0。

先导需保留平均图、三个复 C 图、幅度及相位残差、空白/B-off 对照和输入不确定度。冻结 mask 的生成规则及用于实验/模拟比较的像元集合，不把旧演示库 mask 直接搬到实验；无效预测必须报告，不能通过临时改变比较 mask 逃避残差。以复数残差为主，接近零幅度时不以相位误差单独判失败。验证时不允许给每个未知粒子任意幅度/相位/焦面修正使拟合通过。

数值收敛门、实验误差容许范围及停止规则应由所需测量精度、实际重复性和输入误差预先确定；没有这些证据时可报告残差和范围，不能借用金球 2% 门宣称真实 Fe₃O₄ 测径已验收。一个尺寸或两个工况吻合都不等于建立跨尺寸标定曲线，也不能据此承诺未知粒径置信区间。

---

## 第三部分：交给 Codex 的 V117 唯一连续执行合同

### 9. 本轮目标、边界和停止条件

**建议任务 ID：`V117_TARGETED_ACCEPTANCE_REPAIR_AND_PHYSICAL_INPUT_CONTRACT`。**

本轮只完成：已确证的验收/接口缺口修复、一次固定输入回归、元数据语义准入、可复核归档及下一物理先导预注册。完成后停止同类软件验收循环，把进展转到真实输入取得和物理先导。

| 资源/任务 | 本轮上限 |
|---|---|
| 新 BEM / rule7 / 新物理状态 / 新散射位置 render | 0 |
| 新光学物理时序、实验 BMP/视频重读 | 0 |
| 旧 5040 / 852 / 14400 / 1680 统计重算 | 0 |
| 新 D/z/振幅/频率/窗口搜索、噪声 Monte Carlo | 0 |
| 73 项源身份、48 BANK 内容检查 | 只读；围绕修复后的来源验收做一次正式核验 |
| 保存探针桥接 | 修复后一次 192 条 / 576 频点核验；失败仅重测受影响部分 |
| 软件夹具 | 既有必要回归一次 + 不超过 12 组定向缺陷/负例验证 |
| 修复循环 | 最多两轮，第二轮只处理本次修复的关联问题；保留每轮红/绿证据 |
| 实验元数据 | 一次定向检查已存在的元数据、标定记录和样品记录；缺失不编造 |
| 解析曝光诊断 | 可保存本文件 9 格解析结果；它不是新光学仿真 |

原源树、银行、参考池和旧报告不得覆盖。不得把完成本指令写成实验测径完成。已在工作站运行的其他任务先核实身份，不能按历史 PID 中断、重启或启动重复任务。

正常情况下连续执行全部具备前置的任务，最终一次性交回。某阶段失败只停止依赖分支；来源/软件失败不妨碍完成元数据报告和失败证据归档。两轮定向修复后仍有问题，保留 PARTIAL，不放宽门、不扩展到无关重构。

### 10. S0：锁定源、执行代码和输出三种身份

**[放行条件]** 能读取 V116 固定提交及本轮需要的核心文件。

**[必查项]**

1. 建立只读的 `source_root`，精确签出 `ae7f479775910654eb10b984ec7076b544ab0a61`，保持该源树干净；执行工具和所有输出放在源树外。
2. 新的执行工具包 `execution_root` 从已核查代码衍生，独立记录全部实际执行文件的原字节 SHA、Git 身份（若有）、导入模块 `__file__`、运行参数、环境和开始/结束时间。新工具不能只放进冻结源树成为未跟踪文件后仍自称洁净。
3. 分别记录 `base_source_commit`、`execution_code_manifest`、最终 `release_commit`；不要用一次发布后的 commit 冒充发布前运行的 HEAD。
4. 初次与最终核对源树 porcelain、完整 73 项预期清单及实际原字节；Git 命令非零退出不能当成功。文本 LF/CRLF 分域记录，不静默改写原件。
5. 保存 V115/V116 原状态与本次修正说明。V115 失败源 HEAD=7a910、发布=59800；V116 运行源=59800、发布=ae7。若不能取得某个历史运行的实际工具/ZIP，就把那段执行身份标为未独立证实。

**[失败处置]** 本轮固定源、实际执行代码或所需输入身份不确定时 A=false，相关生产认证暂停；可在可信的独立快照上做标明范围的软件诊断及元数据整理。V115/V116 历史运行工具或原 ZIP 未取得，单独记录历史证据未核实，不因此否决已经独立验证的 V117 当前来源门。不能修改历史提交或手工将 A 改 true。

### 11. S1：修复来源验收器

**[放行条件]** S0 的实际源路径和固定 Git 身份已确定。

**[必查项]**

1. A 必须要求干净源树、所有必要 Git 命令成功、固定 source commit/祖先关系正确、精确 73 项角色/case，以及每个实际文件对固定 Git tree 的预期 blob/长度/来源 SHA 匹配。
2. 对预注册的 73 项 `review_inputs` 对应副本核查缺项、重复映射、错误角色/case 及字节不一致，并使这些问题成为失败，不能仅填表。该目录中的其他历史文件不计入本轮集合，也不因此判失败。源与副本的不同算法哈希各自比较对应域。
3. 对 48 BANK 检查原 dtype 后再计算，核查完整 shape、finite、N/Fs/bin/case/振幅、二值 mask；按正值有限均值中位数的 1% 重建 mask 并要求精确相同。
4. 内容恒等式保持 V116 A 的既有 `<1e-10` 比较门并报告全精度残差；它不能替代 S3 的 `<1e-11` 复谱门。本次既有 BANK 的该残差为 0，不需要重建数组。
5. 用源树外小型副本对实际来源校验入口做针对性负例：错误来源字节/副本不一致、dirty 状态、错误 mask、错误 case/shape 或 dtype 等；必须检查实际 gate=false 和原因，不以“某字典已变化”当检出。

**[失败处置]** 保留真实失败键及原数组；不重算 BEM，不修补旧银行以迎合验收。只有来源与内容真正满足合同才生成本轮 A=true。

### 12. S2：修复 T11 和已证实的生产接口缺口

**[放行条件]** 测试/执行代码身份固定，生产模块实际导入位置可核对。此阶段可独立于旧归档缺失继续。

**[必查项]**

1. 修正 T11 的布尔解包。每个负例分别记录入口、输入、是否拒绝、异常类型/错误码、callback 次数；聚合使用实际布尔字段。强制加入“静默返回”和“普通 TypeError 泄漏”的变异，二者必须被测试判为失败。
2. `run_pipeline` 与 `run_roi` 复用静态参数规则。electron 的 κ、DN 的 g/b、曝光、bin、时间、权重 shape/type 以及可确定的配置错误，必须在第一次强度回调前拒绝。
3. 标量和每像元向量按相同规则检查。明确接受的实数标量类型及 NumPy 实数类型；拒绝 bool、复数、字符串、非有限值、错误维度/长度；不要通过先转 float 静默接受非法原类型。
4. 回调 shape/type/finite 错误用稳定的 `OperatorError`；回调执行异常封装时保留 `raise ... from exc` 的原始原因及时间/阶段。静态错误应零回调，数据依赖错误按首次可知时拒绝；不要把后者错误要求成零回调。不要吞掉进程中断类异常。
5. 强度积分与单位转换后，在任意 partial/full 返回前验证 series/mean 的有限性及电子期望非负；数值溢出应明确失败。不要把任意大小上限（如 `<1e6`）当作有限性检查，也不要将失败元素置零。
6. 保留既有正确的同步整帧采样、探测像元/子像元轴、强度先平方后曝光、合法单位转换和广播。partial 输出不伪装成已认证 DFT；full-N 任一像元/频点原门失败，整次认证失败且不泄漏认证的 dft。
7. 必要回归一次：旧 27 项生产回归、旧 12 组及 4 变异、修正后的 12 项 V116 边界测试；新增缺口验证组织为不超过 12 个明确组。维度夹具仍可用 partial grid，不新增 1681 像元全光学时序。
8. 沿用严格 X/C `<1e-11`、均值 `<1e-12`。不同浮点时间重新采样与同一数组的谱误差分开；不借 G11 或计数单位扩张偷偷放宽门。

**[失败处置]** 未通过时 B=false，记录各项原始输出/异常、输入和模块 SHA；不根据旧套件仍显示全绿就写 `NO_PRODUCTION_PATCH_REQUIRED`。最多两轮定向修复，相关分支未过则最后交 PARTIAL，其余可完成工作继续。

### 13. S3：一次保存探针正式桥接

**[放行条件]** 核心原字节可信，实际调用模块及相关谱计算路径的身份和局部验证清楚。高层 callback 守卫失败或历史 ZIP 缺失不阻断独立保存探针桥接；如果相关谱实现本身尚未通过，则不认证 C。可信快照上的核验应注明来源范围，总任务仍按全部必选门诚实汇总。

**[必查项]**

1. 使用原 `analysis/v093_probe_evidence.npz` 和 48 BANK，不生成新时序。
2. 原始时序恰好 192 条、原 dtype=float64、shape=(2001,)、finite、正均值；在转换 dtype 之前判定。检查预期 case×四个像元，不漏项、重复或混用 key。
3. 在同一个保存数组上调用实际 `production_fft` 与 `independent_dft`，检查对原银行 X/C 的四个复差，各严格 `<1e-11`。
4. 另外明确检查 `X_FFT−X_DFT`、`C_FFT−C_DFT` 均严格 `<1e-11`；保存均值对银行 `Imean_map` 严格 `<1e-12`。不要只在报告列中输出而未进入 PASS。
5. 精确 576 个唯一频点键作为总门；每行保存完整复数、各差、原类型/shape/finite 标志、均值、NPZ/BANK/生产模块 SHA。部分失败也保留全部已完成行和未完成原因。
6. 最终逐行表命名 `tables/v117_bridge576.csv`，summary 与本轮表实际计数一致；不要发布摘要却遗漏这份新表，或用旧 v115 表冒充本轮 fresh run。

**[失败处置]** C=false，保留异常和最大失败键，不修改历史数据、不放宽门。通过后停止反复重算此桥接；以后未改相关代码/数据时以严格来源继承。

### 14. S4：把物理清单变成实际语义准入

**[放行条件]** 无需先等软件或归档全绿；可独立完成参数整理。

**[必查项]**

1. 用稳定 ID 显式列出每项 `value/unit/evidence_class/evidence_reference/source_sha_if_applicable/valid_dataset/valid_time/run_effective/uncertainty_or_bounds/required_for/missing_acquisition`。不以行数或英文说明字符串前缀判定科学准入。
2. `MISSING` 保持 null；有值不等于实测，有文献不等于批次实测，脚本赋值不等于该次运行实际生效。用户陈述可保留其证据类型，不伪造文件 SHA。
3. 明确分开演示 D={30,60,100}、7.29 样品标称 D、独立表征参考 D；区分 D 为直径、核心还是包覆外径。
4. 分开材料 n/k/来源/适用波长、壳层和形状/团聚、介质/基底、高度、焦面、光学参考约束。各项可实测、可有依据的有界假设或有理由 NOT_APPLICABLE；没有证据不填零。
5. 运动路线为 `A_trajectory_ready OR B_field_mechanics_ready`。路线 A 不强求全部 B 参数；路线 B 必须有相应动力学边界。两者均不齐时真实运动前向保持 false。
6. 相对 C 分支在固定曝光、线性、偏置已校正/可约束的情况下，不应因缺绝对 κ/g 一刀切关闭；但相机偏置/非线性影响相对 C，必须提前处理。κ 用于电子期望；DN 另需 g/b。噪声预测还需对应噪声证据。
7. 区分 `METADATA_SCHEMA_VALID`（如实表达缺失也可通过）、`CONDITIONAL_MODEL_DESIGN_READY`、`REAL_DEVICE_RELATIVE_FORWARD_GO`、`ABSOLUTE_COUNT_GO`、`ABSOLUTE_DIAMETER_VALIDATION_GO`。物理 GO 由明确条件推导，不能数够 16 行即通过，也不能把“清单生成通过”写成“实验参数已齐”。
8. 一次性列出最关键的缺失记录、取得方式和被阻断的具体分支。520 nm 不再重复索取；不泛化证书要求；原 BMP/视频重读本轮仍为 0。
9. 保存本文件第 8 节的至多两个工况设计，并填写能从真实记录确定的部分。未知项保留 null，具体数值资源预算未锁定时保持 `DESIGN_ONLY`、`auto_physics_solves=0`。

**[失败处置]** 来源矛盾时写 `CONFLICTING` 而不是挑方便值。真实输入缺失是物理 `INPUTS_PENDING`，不应伪装成软件失败，也不能阻止诚实完整的本轮报告交付。

### 15. S5：正确的失败传播、真实归档和单次交付

**[放行条件]** 完成所有具备前置的步骤，失败/跳过原因均可定位。

**[必查项]**

1. 总协调器按 A/B/C/D 等实际布尔门生成状态；schema-valid 与 physical-ready 分开。任何本轮必选软件/来源门失败，数值验收保持 PARTIAL 和非零总退出，不妨碍归档失败证据。
2. 从 checker JSON 分别读取 `archive_integrity`、`numerical_accepted` 和 `archive_valid`，不得用 checker 总退出码代替单独的完整性字段。验证“数值 FAIL + ZIP 完整”能够被正确表达。
3. 包检查包括实际 ZIP CRC、无重复/遍历成员、manifest 精确覆盖及 SHA、73 项精确角色/case与字节、严格布尔门，以及本轮阶段证据的必要文件集合。检查“成员与自有 manifest 一致”不自动保证应交的新桥接表存在。
4. 保留 provisional 自测，解释其机械阳性；最终 ZIP 生成后另做一次真正的最终 checker。不要循环把最终 ZIP 哈希写回 ZIP 内造成自指；内部 status 可为 `PRE_ARCHIVE_VERIFICATION`，外部 receipt 对最终 ZIP、内部 status 和外部检查结果给出原字节 SHA。
5. 若本机可以取得 V116 原 final ZIP，核对本文件记录的 hash 及真实 receipt 后补齐历史证据；若原件找不到，写 `V116_ARCHIVE_REVIEW_UNVERIFIED`，不得重新拼一个包冒充原 V116。历史原包缺失不阻止基于固定 Git 源完成 V117 新修复和本轮归档。
6. 返回实际 `iscat_v117_return.zip`，以及外部 receipt、archive_check、post_archive_summary、launch/run identity。按既有交接方式提供可读 GitHub V117 精确提交和本轮新增正文/JSON/逐行 CSV；没有实际发布就不填造 release SHA。

建议返回包至少包含：

```text
iscat_v117_return/
  00_README.md
  00_Codex_v117_contract.md
  review.md
  status.json
  review_corrections_v117.md
  source_identity.json
  execution_code_manifest.json
  admission_v117.json
  physics_pilot_preregistration.json
  missing_inputs_action_sheet.csv
  tables/v117_bridge576.csv
  tables/v117_bridge576.summary.json
  metadata_readiness_v117.csv
  logs/source_before_after.json
  logs/source_negative_controls.json
  logs/operator_red_green.json
  logs/operator_targeted_regressions.json
  logs/verifier_selftest.json
  logs/compute_budget_and_actuals.json
  tools/                         # 实际执行源码及对父版本的差分
  snapshot73/                    # 原文件只读副本，不重算
  manifest_sha256.csv
```

若某阶段因前置失败未形成完整表，保留已有部分和明确的 failure/NOT_RUN 记录；归档必须如实容纳这种部分完成状态，不能填造 576 个 PASS。外部 receipt/最终 checker 不伪装成 ZIP 内自认证。

### 16. 给 Codex 的最终执行口令

> 请从 `yyyyzoey/iscat-handoff@ae7f479775910654eb10b984ec7076b544ab0a61` 按本文件第三部分连续执行 V117。先分开冻结源、执行工具和输出身份，修复 A 门实际漏检、T11 假阳性、两入口静态验证与 ROI 异常/有限性缺口，再做一次必要回归和原保存探针 576 项桥接，把元数据清单改为语义准入，完善至多两个后续物理工况的设计。保留历史原件与失败证据，不手工改 PASS；不要每完成一个小步骤就返回 GPT。新 BEM、散射 render、光学物理时序、实验 BMP/视频读取和旧大表重算全部为 0。未齐的真实输入如实列明，全部能做的独立工作完成后一次性交回真实 ZIP、外部校验材料及实际 GitHub 固定提交。完成这些已定位修复后停止同类验收循环，后续以真实输入和有界物理先导推进。

---

## 第四部分：固定来源索引与结论边界

以下链接均指向本次审查的固定提交或明确的历史固定提交。GitHub 报告是执行者证据，不能替代本文件明确列出的独立复算或尚缺的实际归档字节。

1. [V116 固定提交](https://github.com/yyyyzoey/iscat-handoff/commit/ae7f479775910654eb10b984ec7076b544ab0a61)
2. [V116 status.json](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/status.json)
3. [V116 review.md](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/review.md)
4. [V115 原发布状态](https://github.com/yyyyzoey/iscat-handoff/blob/59800bae2a6b5c0b37531c09b6cc97158fad1d5f/status.json)
5. [V116 原生 Git 取证日志](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/logs/v116_git_forensics.json)
6. [V116 协调器源码](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/tools/run_v116_all.py)
7. [生产观测接口源码](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/tools/observation_operator.py)
8. [V116 边界测试源码](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/tools/v116_operator_boundary_tests.py)
9. [实际保存探针桥接源码](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/tools/v115_saved_probe_bridge.py)
10. [73 项来源清单](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/logs/v116_snapshot73_manifest.csv)
11. [48 份 BANK 所在目录](https://github.com/yyyyzoey/iscat-handoff/tree/ae7f479775910654eb10b984ec7076b544ab0a61/analysis/bank)
12. [原保存探针 NPZ](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/analysis/v093_probe_evidence.npz)
13. [V116 物理准入](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/admission_v116.json)
14. [V116 元数据清单](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/metadata_readiness_v116.csv)
15. [归档校验器源码](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/tools/v116_archive_check.py)
16. [verifier 自测汇总](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/logs/v116_verifier_selftest.csv)
17. [V116 工具哈希记录](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/logs/v116_tool_shas.json)
18. [冻结实验采样输入](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/experimental/experimental_inputs_v073.json)
19. [磁材料演示合同](https://github.com/yyyyzoey/iscat-handoff/blob/ae7f479775910654eb10b984ec7076b544ab0a61/experimental/material_contract_v071.json)

用户上传 `progress(4).md` 是研究目标、历史纠错和协作约束的来源；其中后附 V059 原文仅为历史快照，不能当作当前待续跑命令。本文件没有将旧 v059 R2–R6 工作重新放行。

**最终边界：**本次保留的是固定演示源与保存探针的可靠数值证据。真实装置相符性、独立标定、粒径可辨识性和逐颗粒不确定度仍需对应实验证据。下一轮修复的必要性来自这里已复现的具体缺口；它不构成重新扩算旧银行的理由。
