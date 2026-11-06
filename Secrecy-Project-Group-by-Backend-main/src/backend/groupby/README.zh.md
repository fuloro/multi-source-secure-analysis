# Group-by 后端组件

中文 | [English](README.md)

本目录为 MPC 联合分析项目中的服务端 Group-by 组件预留。

本组件负责安全分组与聚合，并与其他后端组件的数据流和执行流程衔接。算法库已实现 COUNT、SUM、MEAN、MIN、MAX、MEDIAN；最终服务对外提供哪些聚合仍待确认。

待复现的协议、MPC 后端集成方式、输入输出表示、API 职责边界、结果公开规则及部署方式，已在下方设计计划中提出初步方案，仍待团队确认。

项目背景与职责范围见[工作区中文 README](../../../README.zh.md)。

## 设计与下一步

参见[实施计划](../../../docs/groupby-plan.zh.md)和[调研记录](../../../docs/research-notes.zh.md)。建议首先实现精确整数 COUNT/SUM、秘密分组键和有效位、固定容量的秘密共享输出，以及独立明文参考实现。集成接口与安全目标仍待确认。

在工作区根目录运行合成数据可行性检查：

```sh
.venv311/bin/python src/backend/groupby/experiments/probe_spu.py
```

## 整数 SUM 基线

`algorithm/g_sum.py` 使用共同分组、全局前缀和、秘密置换和差分求和。
原分段扫描实现保留在 `algorithm/g_sum_baseline.py` 用于对照。
输入为等长的 int32 键、值和 0/1 有效位。上游须保证所有输入值的
绝对值之和不超过 int32 上限。输出容量不变，无效载荷清零。
内核不重构结果。当前是论文高层步骤的 SPU 适配，底层置换和安全假设有差异。

运行：`.venv311/bin/python src/backend/groupby/experiments/demo_sum.py`。
演示读取 `reference_only/expected_join.csv` 作为合成 JOIN 交接数据，并按
公开 right_capacity 填充；不实现 JOIN。模拟器会公开最终返回值，仅用于测试。
包含独立 Python 整数参考实现、边界与固定种子随机检查，并核对 expected.json。

## 秘密置换适配层

`algorithm/permutation.py` 提供 `gen_perm`、`apply_perm`、`apply_inv`，
使用零基目标位置表示，支持复用置换重排多列。详见
[接口说明与聚合方法评估](../../../docs/permutation.zh.md)。
运行 `.venv311/bin/python src/backend/groupby/experiments/test_permutation.py` 验证。
这是基于 SPU 排序的功能适配，不是论文专用置换协议；该适配层也不复现论文的通信保证。原 SUM 基线另存，各聚合实现位于独立文件中。

## 共同分组与文件分工

参见[返回字段、步骤映射和实现差异](../../../docs/groupby-common.zh.md)。
运行 `.venv311/bin/python src/backend/groupby/experiments/test_common.py` 验证共同分组及 SUM 组合。

## 聚合算子

六种聚合均可通过 `backend.groupby.algorithm` 使用。实现位于 `aggregates/`，
置换位于 `primitives/`，参考基线位于 `baselines/`。原有的 `g_*.py` 和置换导入路径
仍受支持。MEAN/MEDIAN 返回 `(keys, numerator, denominator, valid)`，
其他算子返回三个数组。
运行 `.venv311/bin/python src/backend/groupby/experiments/test_aggregates.py` 验证。
这些实现是记录了差异的 SPU 适配，并非完整的协议复现。
详见[聚合接口与目录说明](../../../docs/aggregates.zh.md)。

COUNT 按协议 4.2 对压紧后的组末尾位置作差。
MEAN 提供两种秘密共享输出：`groupby_mean` 保留总和与计数；
`groupby_mean_only` 返回精确的最简分数，使相同均值在不同组大小下具有相同表示（§4.3）。

MIN/MAX/MEDIAN 现已遵循文档所述的论文高层构造。MEDIAN 返回两倍中位数，
分母固定为 2；其 int32 输入值的绝对值不得超过 1073741823。
算法目录顶层的 `sum_from_common.py` 和 `mean_from_common.py` 转发模块已移除，
请改从 `aggregates/` 中的相应模块导入。
参见[协议映射和接口变化](../../../docs/order-statistics.zh.md)。

## 全量合成场景检查

在工作区根目录运行
`.venv311/bin/python src/backend/groupby/experiments/test_scenarios.py`。
该脚本按数据使用说明验收全部 30 个样例：14 个正常样例在 SPU ABY3/FM64 模拟中
检查七个聚合入口，16 个异常样例在脚本输入校验阶段拒绝。
JOIN 参考实现为明文，仅适用于合成数据；本次不验证已部署的 CSV 服务或安全 JOIN。
详见[测试报告](../../../reports/scenario-test-report-2026-11-05.zh.md)。
