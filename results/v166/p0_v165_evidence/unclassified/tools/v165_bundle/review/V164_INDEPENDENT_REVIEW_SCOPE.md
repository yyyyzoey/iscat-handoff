# V164科研审查范围

- 固定HEAD `2558e24ced48e65d34797a4021cab659aa045566`，源代码提交 `d802b9e26d5ace14bb5055e3e1426d68b6e43c23`。
- 本次从固定GitHub文件独立解析：`results/v164/profiles_all.json`的24行与两起点状态、`pooled_all.json`六行和四条件数值、`status.json`、`verification.json`，并核读`tools/v164_bundle/code/v164_run.py`和与交接包相符的`v164_profile_core.py`。
- 24任务全部`LOCAL_TERMINATIONS_ONLY`，每任务2个起点`OPTIMIZER_RETURNED:true`。固定D实验调用合计1,254；工作站报告的加载70、绑定6、终验27与任务求和形成账本1,357。
- `results/v164/audit/independent_recheck_v164.md/json`报告原ZIP 2,722成员、2,721清单、SHA `3191f1d5600dd68d464f471480472946147910c0ce0865e7d0b030a134f73dd7`，SQLite完整性ok、65项工作站测试通过；本模型未在此容器完整下载7.12MB返回ZIP并对其独立解包，**不可冒称已在ChatGPT容器核验原ZIP所有CRC及SQLite全部内部字节**。
- 六个共同参数池符合free≤sigma10≤sigma1≤exact的离散可达值关系，但不证明连续域全局最小或可校准置信区间。有限高度中心是当前候选h_hat，不是独立实测h。
- ANON_02：原模拟真值D=101,h=432.5；V164锚D=124.0904,h=412.0394。候选的高度偏差约-20.46 nm；该事实来自V142原验证器专用真值和V164已经保存的锚点，不是本次新模拟。ANON_03真值D=143,h=478.75；候选D≈134.848,h≈476.593。ANON_04真值D=181,h=526.25；候选D≈188.224,h≈524.561。
- 因此下一轮采用真实模拟场景真值生成**假设、独立于相机噪声**的高度读数，再用旧三帧GLS和共同初始化比较实际模拟粒径误差。不是再次以h_hat作为测量中心。
- 真实磁颗粒材料、运动、观测传递链和实际高度传感器仍未标定；V165即使成功也不能输出真实磁芯绝对测径精度。
