# V168：收费保留、加载身份修复与原任务接续

按`00_V168_唯一执行合同.md`执行，不根据本README另行改变科学任务。

## 明确决策

- V167一条CHARGED原记录永久保留，保守计1次；不是零消耗。
- 授权一个V168新run、一个独立新ledger、一次新模型构造。
- 新上限9999，合并V167旧1次仍≤10000。阶段199/2000/7200/600。
- 科学任务仍为原五项PARTIAL第二起点补充、原十八项±2 nm偏差试验；新随机数为0。
- 原V166结果不重跑，原V167状态不改成成功。

## 包含什么

合同、授权JSON、controller-only的23项/41起点矩阵、只读恢复守卫、原字节GLS目标、57项本地测试、审查说明和完整原V167交接ZIP。

`code/v168_recovery_gate.py`是受信控制器组件，不可交给估计worker，不是完整F2c运行器。它不会创建预算、加载模型或修改旧账本。实际生产集成由Codex在V167已修复代码上小范围实现。

## Codex接续顺序

1. 固定父提交`ab0cfeb7c34c8019143498965b5ef8e6ca3843d8`，只读保护V167现场；建立独立V168工作树。
2. 完整安装本包到`tools/v168_bundle/`，不得拆散目录。
3. 在新工作树运行：

```text
python tools/v168_bundle/code/v168_recovery_gate.py --old-ledger results/v167/logs/v167_budget.sqlite --out results/v168/audit/v167_ledger_native.json
python -m pytest tools/v168_bundle/tests -q
```

第一条只是原生只读审计；第二条只是本包57项测试，不是工作站生产验收，也不运行模型。

4. 对照合同修复生产入口，实际完成继承/新增集成测试、提交和冻结，再创建唯一run并一次性预约。
5. 通过加载F2自检→F2c parent关联→绑定后，连续执行R/B、终验、封存、评分。
6. 受阻时原样归档，不重建fresh账本、不使用改签名或新任务ID绕过收费。

本包没有一键光学启动器。不要臆造一个不存在的launcher或把某个审计命令当作正式科学执行。
