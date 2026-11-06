# 安全 Group-by 后端

中文 | [English](README.md)

本工作区用于开发**安全多方联合分析项目中的 Group-by 部分**，负责在服务端 MPC 计算流程中完成分组与聚合。

整个项目的目标是基于现有 MPC 库复现研究协议，并通过前后端分离的应用进行演示。本工作区聚焦 Group-by；前端开发、JOIN 实现及完整查询系统的建设不属于本部分的职责范围。

## 研究背景

前期讨论涉及两项相互补充的研究：

- *Secure Statistical Analysis on Multiple Datasets: Join and Group-By*（CCS 2023）：安全关系算子的协议设计。
- *SECRECY*（NSDI 2023）：安全查询执行及跨算子优化。

目前以 SPU 作为技术起点。[实施计划](docs/groupby-plan.zh.md)建议先完成 COUNT/SUM 基线，再逐步进行论文协议映射与后端集成。安全目标及待团队确认的接口约束也记录在计划中。

## 职责范围

本组件在服务端 MPC 执行流程中，对受保护的记录进行分组，并计算所需的聚合结果。后续需要与项目中的其他后端组件及经授权的结果交付流程衔接。

实现时需要明确区分“可完成聚合功能的基线方案”和“对特定论文协议的复现”。本地 MPC 实验也不足以证明整个应用的安全性或生产部署能力。

## 目录说明

| 位置 | 用途 |
| --- | --- |
| `src/backend/groupby/` | 为 Group-by 后端组件预留的目录。 |
| `requirements-py311-tested.txt` | 已有的 Python 依赖版本清单，初始化时原样保留。 |
| `.venv311/` | 已有的本地 Python 环境，已配置为不纳入版本控制。 |

## 当前状态

已实现 SPU 置换适配器、共同分组，以及采用前缀和、置换和差分的整数 SUM。
保留分段扫描基线用于对照。COUNT/MEAN/MIN/MAX/MEDIAN 均已实现；MEAN/MEDIAN 返回精确整数分子与分母。
当前交付是记录差异的算法适配，不是恶意安全复现或已部署的后端服务；JOIN 由队友负责。

## 运行合成数据检查

```sh
python3.11 -m venv .venv311
.venv311/bin/python -m pip install -r requirements-py311-tested.txt
.venv311/bin/python src/backend/groupby/experiments/test_permutation.py
.venv311/bin/python src/backend/groupby/experiments/test_common.py
.venv311/bin/python src/backend/groupby/experiments/demo_sum.py
```

版本清单记录已测试的本地环境，本次尚未验证全新安装。
演示有意使用合成数据的参考 JOIN 测试数据，并重构模拟器输出，不实现安全 JOIN。
现已验收 `test/` 中全部 30 个样例：14 个正常样例通过 SPU 模拟，16 个异常样例
由合成数据测试脚本在 MPC 执行前拒绝。运行
`.venv311/bin/python src/backend/groupby/experiments/test_scenarios.py`，
详见[测试报告](reports/scenario-test-report-2026-11-05.zh.md)。
该脚本使用明文参考 JOIN，不是生产输入服务或安全 JOIN 与 Group-by 的集成测试。

参见[实施计划](docs/groupby-plan.zh.md)、[调研记录](docs/research-notes.zh.md)
及[共同分组映射](docs/groupby-common.zh.md)。

## 聚合算子

六种聚合均可通过 `backend.groupby.algorithm` 使用。实现位于 `aggregates/`，
置换位于 `primitives/`，参考基线位于 `baselines/`。原有的 `g_*.py` 和置换导入路径
仍受支持。MEAN/MEDIAN 返回 `(keys, numerator, denominator, valid)`，
其他算子返回三个数组。
运行 `.venv311/bin/python src/backend/groupby/experiments/test_aggregates.py` 验证。
这些实现是记录了差异的 SPU 适配，并非完整的协议复现。

`sum_from_common` 和 `mean_from_common` 应分别从各自的聚合模块导入。
详见[聚合接口与目录说明](docs/aggregates.zh.md)。

### 第 4 节覆盖情况

下表对应[论文扩展版第 4 节](https://www.eprint.mirror.cypherpunks.su/2024/141/1706767899.pdf)列出的六种聚合。

| 论文 | `src/backend/groupby/algorithm/` 下的实现 |
| --- | --- |
| 4.1，共同分组 | `common.py` 将有效行排在前面，并压紧组末尾行。秘密有效位用于区分真实的零键与填充行。 |
| 4.2，COUNT | `aggregates/count.py` 对从 1 开始编号的组末尾位置进行置换，再对相邻位置作差。由于最后一个有效位置可能小于容量，实现会屏蔽填充行。 |
| 4.4，SUM | `aggregates/sum.py` 对组末尾的前缀和进行置换，再作差。 |
| §4.3，MEAN | `aggregates/mean.py` 通过 `groupby_mean` 提供秘密共享的总和与计数对。若只需均值结果，`groupby_mean_only` 会在 MPC 内使用固定步数的欧几里得最大公约数算法和整数长除法，将该数对约为最简分数。相等的均值始终具有相同表示。 |
| 4.6 / 4.8，MAX / MIN | `aggregates/max.py` 和 `aggregates/min.py` 在每组按值排序后，分别选择最后一行或第一行。 |
| 4.10，MEDIAN | `aggregates/median.py` 结合正向与反向秩进行两次选择（4.12 / 4.14，位于 `protocols/ranks.py`）。`protocols/find_zero_or_one.py` 中的协议 4.16 先清除最低位，再测试是否为零。结果的分母固定为 2，输入值的绝对值不得超过 1073741823。 |

内核采用有界 int32 算术、固定容量输出、基于 SPU 排序的置换，以及本地模拟中的
半诚实 ABY3。论文的恶意安全证明和通信界限适用于论文本身的协议。
另见[协议映射和接口变化](docs/order-statistics.zh.md)。
