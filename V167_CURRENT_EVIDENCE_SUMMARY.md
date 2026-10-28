# V167 当前成果与证据总结

生成时间：2026-10-29（Asia/Shanghai）

> 本文是 V167 本轮现有本机证据的如实汇总，不是粒径结果，不是物理验证，
> 也不是实验磁芯绝对测径验收。已失败的继续标 `FAILED`，被阻断的继续标
> `BLOCKED`，未启动的继续标 `NOT_STARTED`。Git 发布只是交付动作，
> 不构成科学验收（合同第 10.6 节）。

## 1. 固定输入与代码状态

| 项目 | 实际值 |
|---|---|
| 仓库 | `yyyyzoey/iscat-handoff` |
| 工作树 | `C:\iscat\v167` |
| 分支 | `v167` |
| 本轮 HEAD | `e4939e19f353f8118d98b97ae2af989f298315ea` |
| V166 发布提交（固定父提交） | `06b35cd4e0a47f7f49ef4b05401a07266f2c03b6` |
| 唯一执行合同 SHA-256 | `d842922f340ad0f31f136d486c26d25536c33898e9dc1f3be2815455709069c5` |
| 合同计划 SHA-256 | `eeae31bb98bafa4893c1c993ebfb7c985a702f1bd32aaba75546c16bd4ebab5d` |
| 当前代码身份 SHA-256 | `9d267addaf905669824b7c226a479d4dc233fed58afed2e8583a553dc8b07185` |
| 已固定运行身份 | `v167-20261028T190448Z-8cf9a24b19c5` |
| 已固定代码身份 | `8cf9a24b19c5e261478440d0de4376069a49a781a6eae179d809f11b99d536b8` |

合同第 0 节四项固定输入本机逐一重算，全部匹配：

| 固定输入 | SHA-256 | 结果 |
|---|---|---|
| `results/v166/estimates.json` | `8f97339e9645a29ec929e5c792d234a28821970338cf92a62d2982bfebba7634` | 一致 |
| `results/v166/height_input/height_readings.json` | `bbfd793aff48247623081dd607168cd9afbba2deeff5f37c7a0cbd62b032ad4e` | 一致 |
| `results/v166/logs/v165_budget.sqlite` | `254b5485164a57865328c81f8890ea4aa458d1386ed6f5f34533f2848f7e4ece` | 一致 |
| `results/v166/iscat_v166_return_001.zip` | `866feed02333f244df72f55e38ccf74060962007a5010c5c29df5ebe9f16a74e` | 一致 |

V166 的 28 项原始结果（23 `FINISHED` + 5 `PARTIAL_SEARCH`）、56 个起点、
4,937 条账本调用与 24 条冻结高度读数全部原样保留，未重抽噪声、未重跑任务、
未改写历史状态（`v166_historical_states_rewritten = 0`）。

## 2. 实际完成的工作

### 2.1 P0 现场保护：EXECUTED / VERIFIED

只读复核已发布 V166 证据：返回归档 17,554,667 字节、5,177 名成员、CRC 干净；
V166 账本以只读打开，56 个起点全部重算且最差绝对 Q 偏差 0.0；24 条读数配对
残差 5.7e-14 nm。未执行任何 reset、clean、删除、覆盖或改名 fresh。

回执：`results/v167/audit/v166_archive_ledger_recheck.json`
（`630ea79d1f2e706e2d109139b5e49116ea06c5e1509aa60f9be050d4e3b16311`）、
`v166_start_and_ledger_recheck.json`（`e2cb3c95…`）、
`v167_p0c_identity_and_pins_recheck.json`（`c34fba19…`）。

### 2.2 P1 估计器输入隔离修复：EXECUTED / VERIFIED

完整配对高度表不再进入估计器。23 个任务沙盒各自只含三个文件：本任务单条读数
`input.json`、同组三帧 `frames.json`、同组六条合法记录 `legal_records.json`。
`single_reading_per_task` true，`tasks_with_exactly_three_files` 23，
staged 文档中真值键命中 0，受控偏差不暴露给估计器，跨 σ 同组不互见，
模型调用 0。11 项测试守门；没有改字段名、拆字符串、修改测试或取消验证。

回执：`results/v167/estimator_inputs/00_isolation_receipt.json`
（`60c22bf048a92085dfbc638429181701ee2099ee241a0cb7d4b7275a8674e8bf`）。
隔离级别如实标注为 `NON_ADVERSARIAL_PYTHON_RUNTIME_ISOLATION_NOT_A_KERNEL_SANDBOX`。

### 2.3 P2 模型绑定：FAILED

在固定身份 `8cf9a24b…` 下，loader 记费一次真实 F2c 前向
（theta `[30.0, 350.0, 0.0, 0.0]`，`theta_sha256 6cf3b6ee…`，
charge digest `2d1dc886…`）之后在构造内的库自检处抛出
`MODEL_ID_MISMATCH_IN_RETURN`。这是真实生产代码行为，不是测试假象，
已在提交 `0526452` 修复（按冻结 F2c 场父件校验 loader 返回值），
由 11 项 `test_v167_model_identity.py` 覆盖。V167 至今没有任何一轮完成绑定。

那一次已记费未返回的调用按合同第 7 节计入消耗，不洗成 0；
`reconcile_loader_orphans()` 位于现已不可达的 `bind()` 内，因此该记费悬置并公开披露。

### 2.4 工作站生产测试：EXECUTED / VERIFIED

`results/v167/workstation_tests/full_008/` 在当前字节上执行，177 项全绿：
继承 41 + bundle 38 + V167 生产 98。`zero_charged_calls_proved` true，
`budget_ledger_opened_mid_run` false，29 项源码哈希运行前后一致，
零真实构造 tripwire 记录 `real_construction_attempts` 0。

边界：这 177 项仍是软件证据。合同第 12 节明确，本地规划与守卫测试
不得描述为 23 项真实仿真通过；本轮真实执行了 0 项估计任务。

## 3. 阶段状态表

| 阶段 | EXECUTION | VERIFICATION | EVIDENCE | SCIENTIFIC_SCOPE |
|---|---|---|---|---|
| P0 保护现场 | `EXECUTED` | `VERIFIED` | 三份 audit 回执 | 只读复核，无新声明 |
| P1 输入隔离修复 | `EXECUTED` | `VERIFIED` | 隔离回执 `60c22bf0…` | Python 运行时隔离，非内核沙盒 |
| P2 模型绑定 | `FAILED` | `NOT_VERIFIED` | `controller_only/step_sequence.json` | 无可用 live 模型 |
| P3 授权计算（5 R + 18 B） | `BLOCKED` | `NOT_EVALUATED` | `audit/v167_round1_blocked_task_table.json` | 未拟合，不谈直径/误差/MAE/偏差 |
| P4 final verify | `BLOCKED` | `NOT_EVALUATED` | 同上 | 无封存估计可复算 |
| P5 封存与独立评分 | `NOT_STARTED` | `NOT_STARTED` | 无；`validator_only/` 按设计为空 | `NOT_EVALUATED` |
| 生产测试 | `EXECUTED` | `VERIFIED` | `full_008` 回执 | 仅本地测试清单 |

阻断原因：`prepare()` 要求固定代码身份等于当前字节身份
（`tools/v167/v167_controller.py:963`）。为完成合同强制要求的修复，身份链为
`8cf9a24b…` → `c5e27bfb…` → `9d267add…`。`task_descriptor()` 把身份写进
23 个估计签名与 `V167_FINAL_VERIFY`：26 项预占中 24 项签名改变，只有
`V167_LOADER_1` 与 `V167_BINDING` 稳定，`reserve()` 对改变者拒绝
`StoreError:task signature changed`。两次拒绝日志均保留：
`logs/controller_run_20261028T193101Z.log`、`logs/controller_close_20261028T194417Z.log`。

估计器本体字节在三个身份之间完全一致（`v167_common.py fe261c07…`、
`v167_jail.py 9fc9b46a…`、`v167_rpc.py 6281d75c…`、`v167_worker.py c237779e…`），
因此科研定义没有发生任何移动。

## 4. 预算

| 阶段 | 上限 | 已用 | 预占任务 |
|---|---:|---:|---:|
| MODEL_BINDING（含 loader 自检） | 200 | 1 | 2 |
| SEARCH_EXTENSION（5×400） | 2,000 | 0 | 5 |
| BIAS_STRESS（18×400） | 7,200 | 0 | 18 |
| FINAL_VERIFY | 600 | 0 | 1 |
| 合计 | 10,000 | 1 | 26 |

账本 `results/v167/logs/v167_budget.sqlite`
（`212fc61391070cc0d8f07e41d1a356f31d76a4aed713bfc8c0e0031ef1d1eb34`，24,576 字节）：
26 个任务全部 `RUNNING`，`attempts` 表仅 1 行且状态为 `CHARGED`，从未结算。
本轮报告制作过程中新增真实 F2c 调用为 **0**；新增 BEM、render、相机曝光、
相机噪声、高度抽样、固定 D 扫描、整批 Jacobian 全部为 0（合同第 9 节）。
V166 剩余预算不结转。

## 5. 未执行与缺失项（如实标注）

`results/v167/` 根下以下合同第 11 节产物不存在，因为对应步骤从未执行：
`run_round.json`、`tasks/` 逐起点结果、估计表、`seal.json`、
`validator_only/` 评分、`verification.json`、`manifest.json`。
不存在不等于零结果，也不得被汇总成“已完成”。

`status.json`（`92259db0…`）是在修复之前按旧身份写出的，曾把 P3 标为
`EXECUTED`。该文件按“证据只追加”原则原样保留、不覆盖；当前字节的真实状态
见 `audit/v167_current_bytes_readonly_status.json`（`8c8fadcb…`）。
该项根因与修复见 `results/v167/history_corrections.md` 第 1 条。

## 6. 科学状态

| 维度 | 状态 |
|---|---|
| `reportable_D` | `null`，V167 不得引用任何直径值 |
| 实验绝对粒径认证 | `false`；仿真拟合粒径误差不等于装置绝对测径精度 |
| ANON_01 检出 | 既有高背景测试仍为 `0/3`，不报告为已成功测径 |
| 五项未完成第二起点受控补充 | `BLOCKED`，0 次调用 |
| 三组 ±2 nm 固定偏差试验 | `BLOCKED`，0 次调用，无方向/曲率表 |
| 封存后独立评分 | `NOT_STARTED` |
| 高度读数是否改善 D 估计 | `NOT_EVALUATED` |

## 7. 等待 PI 的单次决策

`results/v167/audit/v167_decision_required_pi.json`（`46e6a9c3…`）：

- 方案 A：授权新的运行身份与新账本，把悬置的 1 次记费结转，本轮上限降为 9,999，
  同一冻结计划、同一目标、同一 24 条读数、同一起点，不重抽、不重定义；
- 方案 B：接受本轮 BLOCKED 作为 V167 交付，R/B 分支保持未执行。

自行新建账本、改名 fresh、删库或递增修订号绕过身份门，正是合同第 175 行禁止的
预算规避，因此等待期间未启动任何计算。未获授权时的默认结果是：阻断状态成立并按
阻断交付。

## 8. 交付物 SHA

| 交付物 | 字节 | SHA-256 |
|---|---:|---|
| `results/v167/p5_delivery/v167_code_sha256_manifest.csv` | 5,017 | `d01a7c818a64afe0301128757e493bad4d62498db9a8a5928c6116b588d12688` |
| `results/v167/p5_delivery/v167_results_sha256_manifest.csv` | 479,018 | `87394c0b06bfa78471bc9cb704413e8cc98ec43bb0b00a958e7eb248e31435bf` |
| `results/v167/p5_delivery/delivery_manifest_receipt.json` | 2,800 | `54b31754429617d26d4374371a046061931fd18dd8e59bd0043951d737a45a13` |
| `results/v167/00_execution_truth_report.md` | 11,164 | `16a8d7222675a16cebf16d4e6e6f17b6a40867cabcb17bfbfcbbea0454f0e992` |
| `results/v167/history_corrections.md` | 5,230 | `1e50b08512a7c998846de651e8d1932a735b1315574108250e57076b30d07658` |
| 唯一返回归档 `results/v167_prepared/pack_rehearsal/iscat_v167_rehearsal_20261028T204438Z.zip` | 27,280,244 | `273b20b94b1053f4f25de725ab29f4ee534e4997931c7284f27361927755fcae` |
| 归档外部 SHA 回执（同名 `.zip.sha256`） | 108 | `c8b6ccbfe5dab9b32697d4e8f40e3f59c785ac4ca769deb4fd092473038729b1` |
| `results/v167/audit/v167_package_publish_receipt.json` | 8,580 | `5e232320a0a65c4cfff5fe17da9cf6db1e21a85107094b8ff7ec864e362745d3` |

代码清单 46 行覆盖 `code_identities()` 实际绑定的全部文件集；结果清单覆盖生成时刻
`results/v167/` 下 2,719 个文件。两份清单无法哈希自身字节，这五个自排除路径已在
`delivery_manifest_receipt.json` 中披露。
返回归档在两份清单生成之后重新打包，因此新增的 `p5_delivery/` 六个文件已进入归档，
而打包回执与审计本身仍写在归档之外，已由发布回执按路径披露。

## 9. 本轮上传范围

本次向远端 `v167` 分支上传：本总结、`results/v167/` 全部证据、当前唯一返回归档
及其外部 SHA 回执、发布回执与发布确认。上传的是**阻断轮的交付物**，
不是放行门通过。归档不含 `results/v167/README_V167_RETURN.md`（打包器设计排除，已披露）。
未上传伪造的最终 ZIP、拟合结果或物理结论。

## 10. 对本总结上一版的更正

第 9 节此前写有"归档内不含任何真值、种子、epsilon 或封存真值文件"。该句**不准确**，
已更正。实测事实是：`results/v167/audit/v167_p0c_identity_and_pins_recheck.json`
为证明 24 条假设高度读数按冻结种子复现、而非重新抽样，记录了种子 `16520261027`、
真值文件 SHA-256 `0f069b71ec803a8e8e236357e21a151be4cf0996c70b05d6f49a622910943d08`
以及 24 组 recovered epsilon/h。

这些内容属于校验侧证据，估计器不可达：`00_isolation_receipt.json` 证明 23 个任务监狱
各自只含自身的单条读数 payload、同组三帧文档与同组六条合法记录，
`truth_valued_key_offenders_in_any_staged_document` 为 0。
同一批真值文件已随 V166 公开：`results/v166/iscat_v166_return_001.zip`
内含 `results/v165/validator_only/v166_height_truth_sealed.json`、
`v166_independent_score.json` 与 `v166_validator_score.json`，
且 `results/v166/validator_only/gate_a_003` 已在 `v166` 分支受版本控制。
因此本分支没有新增任何真值披露，"数据是模拟高度读数"这一科学边界不变。
