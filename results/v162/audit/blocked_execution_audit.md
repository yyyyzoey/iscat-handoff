# V162 执行阻断只读法医审计（blocked_execution_audit）

生成时间（UTC）：2026-10-26T12:38:24.513148+00:00
仓库：C:\iscat\v162；分支 HEAD：dc919aada7cc750c19383470021878fab5814db5
审计性质：只读；不改冻结字节、不改账本、不新增模型调用、不重置 task id。

## 结论摘要
- 软件测试：222/222 通过（官方回执校验器复核通过，见下方哈希）。
- preflight 阶段：FINISHED（含 BASE 字节锁验证，含 360 个受锁文件）。
- execute 阶段：BLOCKED_OR_FAILED，首个任务 LOADER_1 在 v146_runtime.construct_bound 处抛出 
  ValueError: FROZEN_SOURCE_CHANGED:tools/v133_recover_M.py；依赖阶段全部未开始。
- 真实模型前向尝试总数（账本口径）：0 / 500。
- 科学结论：NOT_EVALUATED；all_reportable_D_null=true；实验绝对粒径验证=false。

## 根因（互斥冻结门的证明）
- 门 A：v162_deployment.verify_locked_inputs 要求工作树文件字节 == BASE(71333a9f193d00012972e8fd6c188805c7a6b18e) git blob 字节。
  该 blob：0ee71c80664d5661ed4f7eea5d620d1c24adc461， 9533 B，sha256 142052e012a89191bd0d6fa943af06d8ca1fec5d3ae8f09298fb8e9bec997a4c。
- 门 B：v146_runtime.construct_bound 要求同一文件 sha256 == v146 配置中的冻结 pin 4b89adf9354c468e706da9d63e70d545fb8b3ad18da69ec87f6fb87a7e01d4ba（9662 B 变体，仅存在于历史 results 归档副本）。
- 两个 sha256 是否相等：False ⇒ A∧B 不可同时满足；且该路径在全部 git 历史中只有一个提交（7c209897, 2026-10-22），即 BASE/HEAD blob 就是 9533 B 版本。
- 官方 preflight 回执（preflight.json）自身记录了该文件 sha256=142052e012a89191bd0d6fa943af06d8ca1fec5d3ae8f09298fb8e9bec997a4c，与门 B 的 pin 冲突 ⇒ 该矛盾是交付包内部的，与工作站环境无关。
- 由包自身设计，修复窗口已关闭：restore_new_worktree 在存在模型账本时抛 NO_REPAIR_AFTER_MODEL_RUN；v162_run.execute 在账本存在时拒绝自动重跑（EXISTING_LEDGER_USE_READONLY_VERIFY_OR_FORENSICS_NO_AUTO_REEXECUTION）。

## 依赖阻断而未执行的阶段（NOT_STARTED）
- ANCHORS (36 Q replay, 6 E1 regression, 72 start rescoring, 12 candidate selection)
- NONLINEAR_PROBES (3 groups x 24 planned points)
- FINAL_VERIFY / verification.json

## 资源账本（只读快照）
- 账本：logs/v162_budget.sqlite，sha256 94368faf65b7329253a70c86ad909d694d4444071d39d0366c0480886327a2e5，integrity_check=ok。
- tasks 行数 1；attempts（计费）行数 0；attempt 状态统计 {}。
- 唯一任务记录：[{"id": "LOADER_1", "phase": "REPAIR_AND_ANCHOR", "cap": 100, "used": 0, "state": "FAILED"}]。
- 说明：加载器尚未发生任何一次受计费前向；LOADER_1 在构造模型阶段即失败，任务已封存为 FAILED（result_sha 复核见 JSON）。

## 关键产物哈希（审计时点）
- iscat_v162_return.zip（最终重打包前）sha256 c9a508fdbfb1bf0b79ea0a6ec0c5c748a281568d0b57569dbc1d512ca149d828（392535 B，74 成员）。
- manifest_sha256.csv sha256 f57bcb2a4e53bfbd0046da4e704fd516cd1444944ab14db634507f3cedea1164；archive_receipt.json sha256 {"members": 74, "note": "Receipt is external to ZIP; CRC does not establish scientific acceptance.", "path": "iscat_v162_return.zip", "sha256": "c9a508fdbfb1bf0b79ea0a6ec0c5c748a281568d0b57569dbc1d512ca149d828"}。
- 首次失败回合快照 zip sha256 b9d658b5497c42c6184d37d26bc3c2ab1cc0db8d91694484365c15c28caa5166。
- 测试回执 test_receipt.json sha256 70482bfe4cc0d4acde0b3b7acd364d6d02a553043e59f3aaa243df71160e541d；pytest_outcomes.json sha256 c4d658e1a9f139d50c3e5e4499d7c28e2cee73510006467f0b431d2610d08657。
- 失败记录 failures/000.json sha256 4db0b2494d734e947a98c3183ba44564211271b35d2a83ca1191925ccf6ed068（共 1 条）。

## 诚实性披露
- 首次修复调查中对 tools/v162_bundle/run_workstation_tests.py 的一次工作树编辑已在任何提交与任何模型调用之前恢复为 HEAD 原始字节，diff/前后字节保存在 deployment_repair_evidence/runner_edit_reverted_before_commit/。
- pytest 7.4 内建 nose 插件与冻结测试模块的模块级 setup 冲突，通过调用方环境 PYTEST_ADDOPTS='-p no:nose' 规避；包内字节改动为 0，A/B 复现证据在 deployment_repair_evidence/。
- 本审计生成于最终重打包之前；最终 zip 的一致性由 audit/final_zip_mechanical_verification.json（外部伴随回执）单独核验。
