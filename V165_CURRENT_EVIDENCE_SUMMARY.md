# V165 当前成果与证据总结

生成日期：2026-10-28（Asia/Shanghai）

> 本文是现有本机证据的如实汇总，不是 V165 最终交付，不是粒径结果，也不是
> 物理或实验验收。未完成的生产阶段继续标记为 `NOT_STARTED`，已知失败继续标记为
> `FAILED`。

## 1. 固定输入与代码状态

| 项目 | 实际值 |
|---|---|
| 仓库 | `yyyyzoey/iscat-handoff` |
| V165 工作树 | `C:\iscat\v165` |
| V165 分支 | `v165` |
| 当前 HEAD | `2558e24ced48e65d34797a4021cab659aa045566` |
| V165 代码提交 | 尚未创建 |
| V165 结果提交 | 尚未创建 |
| 正式执行合同 SHA-256 | `1f52da3b6344773c0bc5d4e79e75fe7590a604fc06c1cddfc213ea201bfec3fe` |
| 交接 ZIP SHA-256 | `abac2611ff6f0618cb73dab4323fc4e7fbd7efc1f746cf35485ab9d5ffd7eec8` |

`v165` 本机分支从固定 V164 HEAD 创建。上传本总结前，远端不存在
`refs/heads/v165`。当前工作树中的 V165 执行代码、测试和现场证据仍为未提交文件；
本文不把这些未提交文件描述成已验收的生产实现。

## 2. 实际完成的核查

### 2.1 Gate A 来源资格

历史 Gate A 尝试 `gate_a_002` 返回 `PASS`，检查了四个场景、十二个相机事件、
冻结检测结果和来源字节身份。其回执明确限定为：

`READ_ONLY_PROVENANCE_ONLY_NOT_A_PHYSICAL_OR_SIZING_RESULT`

因此该结果只支持“来源链在当次检查时一致”，不支持粒径精度、高度信息增益或实验
磁纳米颗粒绝对测径。

| 产物 | SHA-256 |
|---|---|
| `results/v165/validator_only/gate_a_002/gate_a_receipt.json` | `6c03e1e5d5db95d010e772c59b7cb8b9a4d646dd45eeb6253ed6cd0dd2c87d5f` |
| `results/v165/validator_only/gate_a_002/full_report.json` | `71c20b9f112142b6a96a4bc3965d433398c873b8724fc3c6fce112415cc103cf` |
| `results/v165/preflight/gate_a_projection_002.json` | `99b4da1986904b822689d6d8f82382d93aaeaeeb99453d969fe759703282e418` |

Gate A 回执登记的新增资源为：F2c 模型调用 `0`、BEM `0`、render `0`、
相机曝光 `0`、相机噪声抽样 `0`。

### 2.2 工作站测试

最近一次完整收集和执行为：

`results/v165/workstation_tests/production_001/manual_pytest_output.txt`

实际结果：

- 收集：29 项
- 通过：26 项
- 失败：3 项
- pytest 退出码：`1`
- 测试 tripwire：`0` 字节
- 测试输出记录的 tripwire 字节数：`0`

因此工作站测试总状态是 **FAILED**，不是 PASS。三项实际失败为：

1. `test_execute_constructs_model_once_and_preserves_all_task_states`
   实际构造调用序列为 `[1, 1]`，测试要求新运行只构造一次 `[1]`。
2. `test_restart_with_sealed_loader_blocks_unfinished_dependents`
   sealed loader 重启后再次构造模型，实际序列为 `[1, 1]`。
3. `test_test_suite_does_not_import_real_model_or_have_truth_literals`
   `v165_io.py` 中含一个连续的真值身份 SHA 字面量。

这些失败是执行器缺陷，不是物理噪声，也不构成 V165 科学结论。现有生产入口尚未
通过放行门。

| 产物 | 字节 | SHA-256 |
|---|---:|---|
| `results/v165/workstation_tests/production_001/manual_pytest_output.txt` | 1947 | `c9b065e25167dc9ea2d9142234436aace62181bf0fc8aaebd6b89e135a01daf3` |
| `results/v165/workstation_tests/production_001/test_tripwire.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## 3. 尚未执行或无法验证的内容

本机未发现以下正式 V165 产物：

| 必要产物 | 状态 |
|---|---|
| `results/v165/logs/v165_budget.sqlite` | `NOT_STARTED` |
| `results/v165/height_input/height_readings.json` | `NOT_STARTED` |
| `results/v165/preflight.json` | `NOT_STARTED` |
| `results/v165/estimates.json` | `NOT_STARTED` |
| `results/v165/seal.json` | `NOT_STARTED` |
| `results/v165/execute_status.json` | `NOT_STARTED` |
| `results/v165/iscat_v165_return.zip` | `NOT_STARTED` |

由此，28 个 `D/h/x/y` 联合任务、12 个标准正态高度抽样及 24 条匿名读数、
独立 final verify、封存后 validator 和最终归档均未在本机找到正式执行证据。

此前用户提到的约 22 小时运行和账号欠费中断，在现有目录中无法由正式预算账本、
逐任务检查点或封存文件复核。不能据此声称已接管或复用了 22 小时生产结果；也没有
删除、重建或重置任何未知账本。

## 4. 科学状态

| 维度 | 状态 |
|---|---|
| 软件测试 | `FAILED`（26/29） |
| 最终代码 Gate A | `NOT_EVALUATED`；`gate_a_002` 只覆盖当时来源资格 |
| 正式生产 preflight | `NOT_STARTED` |
| 高度读数生成 | `NOT_STARTED` |
| 28 个联合拟合 | `NOT_STARTED` |
| 封存与独立评分 | `NOT_STARTED` |
| 返回 ZIP | `NOT_STARTED` |
| `reportable_D` | 没有正式估计；任何未来值仍须满足合同，当前不得报告 |
| 实验绝对粒径认证 | 不成立 |
| 高度读数是否改善 D 估计 | `NOT_EVALUATED` |

当前不能给出“V165 仿真通过”或“V165 仿真失败”的科学裁决，也不能把历史 V164
结果、Gate A 来源 PASS、或测试通过的子项重新标记为 V165 新结果。

## 5. 已知待修复项

1. 新运行只构造一次 live model，并对 sealed-loader resume 禁止重建模型。
2. 保存完整初始 RUNNING 检查点，恢复时不重放已封存真实调用。
3. final verify 固定检查 28 个拟合任务和 4 个 anchor，共 32 项。
4. 缺失兼容区间保持 `null`，不得默认成 `[30, 200]`。
5. 执行状态从真实任务状态派生，不得硬编码 `FINISHED`。
6. 修正历史组名提取、Gate A failure digest、receipt 文件覆盖和严格账本核验。
7. 真实记录 tripwire 前后状态和测试结果，禁止硬编码零调用。
8. 从真实 pytest collection 生成测试清单，并补齐 `run_all.py`、状态、报告包和
   独立归档验证入口。

在这些修复、完整测试和新 Gate A 通过之前，不得启动正式模型预算、高度读数生成
或 28 个拟合任务。

## 6. 本次上传范围

本次只上传本总结，使远端 `v165` 分支具有可审查的当前状态记录。没有上传伪造的
最终 ZIP、预算账本、拟合结果或物理结论。本机未提交的执行代码、失败日志和历史
现场继续原样保留。
