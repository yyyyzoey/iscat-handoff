# Codex小范围补丁映射

本表说明实际要改哪类代码。不得把旧文件名中的v167全部文本替换成v168，旧来源身份必须保留。

| 现有位置 | 新V168要求 | 不允许做的事 |
|---|---|---|
| v167_common：OUT/PLAN_ROOT/OWNER/TOTAL/PHASES | 新输出及ledger属V168，TOTAL=9999，MODEL_BINDING=199；其他阶段不变 | 改旧results/v167、改老授权文件 |
| v167_service：make_store/reserve_loader/reserve_binding/seal | 新plan_id、loader100、binding99，统一由同一描述符签名 | loader/binding仍只绑定model_id、不绑定执行代码 |
| check_returned_model_id/resolve_loader_field_parent | loader精确旧F2；候选与计算精确F2c；验证parent链 | 对任意返回放行、仅凭shape或字符串前缀 |
| charged_call | invoke、返回校验、落盘三个阶段的失败保留收费与异常 | 返回校验失败后悄悄留下未解释CHARGED或退款 |
| prepare/reserve | 全部测试与源码提交冻结后，一次性创建新run与26项签名 | 事后修改旧run_identity、UPDATE旧签名 |
| worker run_pass/main | R一次least_squares实例，cap400真实新调用；B每起点一次，cap200 | 把max_nfev=200当回调配额并自动重启第二pass |
| runner/service per-start计费 | 受信端按start_index持久charge总量硬限；缓存另记 | 只相信worker自报，缓存也冒记真实调用 |
| binding/final | 新模型真实重放，缓存不能证明新模型正确 | 已保存C与自身比较后标独立复核 |
| status/pack | 独立只读路径，不依赖prepare/reserve/construct | 由于run身份过期就无法交付失败报告 |
| tests | 保留原测试；新角色身份、累计预算、单次求解器、freeze、失败打包回归 | 删除断言、硬写PASS或硬写0调用 |

所有改动都要有实际diff、代码SHA和测试回执。科学目标函数/数据/噪声/起点选择不变。
