# V165 Codex交接包

**唯一合同**：`00_V165_Codex_唯一执行合同.md`。请先完整阅读，不得以README替代合同。

本包**不是已完成的工作站生产运行器**。ChatGPT完成了V164公开结果审查，提供冻结研究合同、假设高度读数生成器、GLS附加高度目标核、确切28项任务ID、冻结配置及本地回归测试。Codex的职责是在新的V165分支上将其集成到已通过V164工作站测试的版本化执行器与持久预算系统，并完成生产测试和仿真。不能把这7项本地测试称为工作站F2c验收。

`code/v152_gls_core.py`是从V164交接包直接复制的原冻结数学核；不得修改其GLS定义。V164代码/数据采用固定SHA进行核验。真实高噪声/材料等输入不得填入外部不可验证数值。

用于本包本地测试：

```bash
PYTHONPATH=code python -m pytest -q tests
```

工作站Windows使用等价的`python -m pytest -q`配合显式`PYTHONPATH`，输出实际收集的每个节点。必须执行工作站生产CLI、故障注入和完整数据回放测试。

辅助高度生成入口（**只有preflight确认场景映射和角色隔离后**才能运行）：

```text
python generator/v165_generate_height.py --truth <验证器专用N真值文件> --height-input-out <新的匿名高度读数JSON> --validator-sealed-out <估计器目录之外的新validator专用JSON>
```

禁止将`--validator-sealed-out`指向估计器可读取路径；禁止覆盖已生成值或更换随机种子筛选结果。

封存后评分器（要求另提供同组三帧的冻结检测真值布尔表）：

```text
python validator/v165_validator.py --estimates <估计结果列表> --estimates-sha256 <封存SHA文本> --truth <验证器N真值> --readings <匿名高度读数> --frozen-detections <每组3帧检测状态JSON> --out <新的评分结果JSON>
```
