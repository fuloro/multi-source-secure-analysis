# 全量合成样例测试报告

测试日期：2026 年 11 月 5 日（Asia/Shanghai）。执行时间：10:50:58 至 10:51:26。

本次覆盖 `test/` 下两个场景的全部 30 个样例，30 个均符合预期。14 个正常样例完成 SPU 模拟执行，16 个异常样例在测试脚本的输入校验阶段拒绝，错误码全部一致。未修改聚合内核、输入样例、预期答案、依赖或虚拟环境。

## 验收依据与执行范围

依据 [数据使用说明](../docs/数据使用说明.docx) 第 1 页的验收步骤、第 2 页的业务语义与职责、第 3–4 页的医保字段和示例、第 5–6 页的客群字段及 CSV 批次规则；同时核对两个场景的 `reference_only/case_index.json`、逐例 `expected.json`、`expected_join.csv`、`expected_result.csv`。说明书已提取全文并渲染核对。

现有 demo 仅覆盖医保示例的 SUM；本次新增 [可复跑的验收脚本](../src/backend/groupby/experiments/test_scenarios.py)。脚本中的 CSV 校验器和明文 JOIN 是合成实验辅助代码，不是已部署的输入服务或队友的安全 JOIN 实现。异常样例通过，表示辅助校验器按文档拒绝了它们，不表示生产服务已经具备这些功能。

正常样例从各自 `owner_a/`、`owner_b/` 原始 CSV 计算独立明文内连接，再补齐到公开容量 4，使用秘密有效位送入 SPU。`reference_only/expected_join.csv` 仅用于核对独立连接结果，未作为 MPC 输入。Python 任意精度整数及 `Fraction` 作为参考，金额未转换成浮点数。

## 结果汇总

| 场景 | 正常样例 MPC 验证 | 异常样例按预期拒绝 | 总计 |
| --- | --- | --- | --- |
| 医保商保费用统计 | 7/7 | 8/8 | 15/15 |
| 客群消费分析 | 7/7 | 8/8 | 15/15 |
| 合计 | 14/14 | 16/16 | 30/30 |

每个正常样例检查 COUNT、SUM、MEAN、仅均值最简分数接口 MEAN_ONLY、MIN、MAX、MEDIAN，共 98 次“样例 × 聚合入口”比对。文档要求的 COUNT/SUM/MEAN 均通过；额外算子与独立参考比较，不将其描述为说明书要求。所有输出均为容量 4 的 int32 数组，有效位及无效填充载荷符合接口约定；分数的无效分母按接口为 1，MEDIAN 的分母固定为 2。

两个场景各 76 个文件，共 152 个文件与原有 SHA-256 清单完全一致，无缺失、无清单外文件。目录中的样例集合与索引完全一致，没有漏跑。

## 全部样例明细

正常行的“通过”表示输入校验、独立参考及预期文件核对、七个聚合入口的 MPC 比对均通过。异常行表示精确匹配所列拒绝码，未启动该样例的 MPC。

| 场景 | 样例 | 实际状态或错误码 | MPC 执行秒 | 结果 |
| --- | --- | --- | --- | --- |
| 医保 | `demo` | `SUCCESS` | 2.3616 | 通过 |
| 医保 | `repeated_amount` | `SUCCESS` | 2.2001 | 通过 |
| 医保 | `fractional_mean` | `SUCCESS` | 1.7199 | 通过 |
| 医保 | `no_overlap` | `SUCCESS` | 2.0333 | 通过 |
| 医保 | `empty_left` | `SUCCESS` | 1.8415 | 通过 |
| 医保 | `empty_right` | `SUCCESS` | 1.7373 | 通过 |
| 医保 | `zero_amount` | `SUCCESS` | 1.6097 | 通过 |
| 医保 | `reject_duplicate_subject` | `DUPLICATE_LEFT_ID` | 未执行 | 通过 |
| 医保 | `reject_duplicate_record` | `DUPLICATE_RECORD_ID` | 未执行 | 通过 |
| 医保 | `reject_missing_amount` | `MISSING_VALUE` | 未执行 | 通过 |
| 医保 | `reject_negative_amount` | `AMOUNT_RANGE` | 未执行 | 通过 |
| 医保 | `reject_unknown_group` | `GROUP_CODE` | 未执行 | 通过 |
| 医保 | `reject_capacity` | `CAPACITY_EXCEEDED` | 未执行 | 通过 |
| 医保 | `reject_scientific_amount` | `INTEGER_FORMAT` | 未执行 | 通过 |
| 医保 | `reject_amount_limit` | `AMOUNT_RANGE` | 未执行 | 通过 |
| 客群 | `demo` | `SUCCESS` | 2.1424 | 通过 |
| 客群 | `repeated_amount` | `SUCCESS` | 2.0447 | 通过 |
| 客群 | `fractional_mean` | `SUCCESS` | 1.9719 | 通过 |
| 客群 | `no_overlap` | `SUCCESS` | 1.2928 | 通过 |
| 客群 | `empty_left` | `SUCCESS` | 1.2956 | 通过 |
| 客群 | `empty_right` | `SUCCESS` | 2.0788 | 通过 |
| 客群 | `zero_amount` | `SUCCESS` | 1.9789 | 通过 |
| 客群 | `reject_duplicate_subject` | `DUPLICATE_LEFT_ID` | 未执行 | 通过 |
| 客群 | `reject_duplicate_record` | `DUPLICATE_RECORD_ID` | 未执行 | 通过 |
| 客群 | `reject_missing_amount` | `MISSING_VALUE` | 未执行 | 通过 |
| 客群 | `reject_negative_amount` | `AMOUNT_RANGE` | 未执行 | 通过 |
| 客群 | `reject_unknown_group` | `GROUP_CODE` | 未执行 | 通过 |
| 客群 | `reject_capacity` | `CAPACITY_EXCEEDED` | 未执行 | 通过 |
| 客群 | `reject_scientific_amount` | `INTEGER_FORMAT` | 未执行 | 通过 |
| 客群 | `reject_amount_limit` | `AMOUNT_RANGE` | 未执行 | 通过 |

## 正常样例的聚合结果

金额单位为分。下列结果已逐项与 MPC 返回值及预期 JSON 比较；均值保留精确分数，元显示采用十进制 ROUND_HALF_UP。

| 场景 | 样例 | 分组编码 | COUNT | SUM 分 | MEAN 分 | 均值显示 元 |
| --- | --- | --- | --- | --- | --- | --- |
| 医保 | `demo` | 1 | 2 | 2000 | 1000 | 10.00 |
| 医保 | `demo` | 2 | 1 | 3000 | 3000 | 30.00 |
| 医保 | `repeated_amount` | 1 | 2 | 500 | 250 | 2.50 |
| 医保 | `fractional_mean` | 1 | 3 | 8 | 8/3 | 0.03 |
| 医保 | `no_overlap` | 无有效分组 | — | — | — | — |
| 医保 | `empty_left` | 无有效分组 | — | — | — | — |
| 医保 | `empty_right` | 无有效分组 | — | — | — | — |
| 医保 | `zero_amount` | 1 | 1 | 0 | 0 | 0.00 |
| 客群 | `demo` | 1 | 2 | 299 | 299/2 | 1.50 |
| 客群 | `demo` | 2 | 1 | 1999 | 1999 | 19.99 |
| 客群 | `repeated_amount` | 1 | 2 | 500 | 250 | 2.50 |
| 客群 | `fractional_mean` | 1 | 3 | 8 | 8/3 | 0.03 |
| 客群 | `no_overlap` | 无有效分组 | — | — | — | — |
| 客群 | `empty_left` | 无有效分组 | — | — | — | — |
| 客群 | `empty_right` | 无有效分组 | — | — | — | — |
| 客群 | `zero_amount` | 1 | 1 | 0 | 0 | 0.00 |

## 关键验收点

- 客群 demo 的同一用户两条记录（299 分、0 分）均计数：COUNT=2、SUM=299、MEAN=299/2 分，即 1.495 元，显示 1.50 元。MPC 精确整数分数与参考相等，本例没有浮点误差改变舍入边界。显示逻辑在测试脚本中核对，尚未验收前端页面。
- 医保 demo：产品 1 为 COUNT=2、SUM=2000、MEAN=1000 分；产品 2 为 COUNT=1、SUM=3000、MEAN=3000 分。仅 B 侧存在的主体被排除。
- `repeated_amount` 保留不同记录 ID 的同主体同金额记录：COUNT=2、SUM=500、MEAN=250 分。没有误做去重。
- `fractional_mean` 为 COUNT=3、SUM=8、MEAN=8/3 分；精确均值与 0.03 元的显示结果均匹配。
- 两个场景的无交集、空左表、空右表，共 6 个样例均以容量 4 实际执行 MPC；输出全部无效，没有虚构零值分组。
- 两个 `zero_amount` 样例均输出有效分组、COUNT=1、SUM=0、MEAN=0，没有把零金额当成缺失或填充。
- 重复左侧主体、重复记录 ID、缺失金额、负金额、未知分组、容量超限、科学计数法金额和超过 100000000 分的金额均在输入阶段拒绝。

## 环境与耗时

| 项目 | 实测配置或结果 |
| --- | --- |
| Python | 3.11.18 |
| SPU | 0.9.5 |
| JAX / JAXLIB | 0.4.34 / 0.4.34 |
| NumPy | 1.26.4 |
| 系统 | Linux-7.1.5+kali-amd64-x86_64-with-glibc2.43 |
| 协议与域 | 三方 ABY3 / FM64，进程内模拟 |
| 输入 / 输出 | int32，公开容量 4；三个输入的编译可见性均为 VIS_SECRET |
| 编译 | 1.6529 秒；一次编译七个聚合入口，14 个样例复用同一可执行程序 |
| 14 次执行合计 | 26.3087 秒 |
| 单次执行范围 | 1.2928–2.3616 秒 |
| 单次执行中位数 | 1.9754 秒 |
| 通信字节数 / 轮数 | 不可用，未测量 |

执行计时包含模拟器的份额生成、内存链路运行和最终输出重构，不包含编译及 CSV 读取/明文 JOIN；每个样例运行一次，没有性能预热。该数据用于记录本次运行，不能作为 LAN/WAN 性能或单个聚合算子的独立基准。

## 未覆盖与后续验收

本次结果支持这 30 个合成样例的输入约束及 Group-by 功能正确性。实际安全 JOIN、数据拥有方分别本地接入、跨机器传输、保持共享状态的 JOIN → Group-by 组合、指定分析者的结果发布权限、恶意安全及真实数据隔离均未验证。模拟器在本测试进程中持有明文输入并重构最终输出。部署、接收方与发布策略仍需团队确认。

当前 CSV 无日期列，因此只核对公开批次元数据，没有验证逐行期间筛选。容量 4 与单值上界 100000000 的乘积为 400000000，符合 int32 累加范围；这是一项公开上界检查，不代表已穷举金额全范围。现有样例没有覆盖金额上限的正常输入、ID 两端边界、BOM/换列、缺列/未知列/重复表头、其他非法数值格式及所有容量配置。完整输入服务仍需针对这些规则补充测试。

未发现本批样例的聚合差异，也未修改算法来迎合预期。新增的实验校验器不应直接接入真实数据服务。

## 复现与原始证据

在项目根目录使用现有环境运行：

```sh
.venv311/bin/python src/backend/groupby/experiments/test_scenarios.py
```

脚本退出码：0。默认生成 JSON 结果；若样例、错误码或文件完整性任一不符，退出码为 1。

- [机器可读逐例结果与版本记录](scenario-test-results-2026-11-05.json)
- [完整验收脚本](../src/backend/groupby/experiments/test_scenarios.py)
- 本次说明书 SHA-256：`ca00a4fd7f8c95a851e6abbd1c75e1a4f8eb8d35f7c1bd609cef51d6d3046db4`。
- 本次脚本 SHA-256：`a550fad998898da5a794efe58fd74eaff7f7b5d390a705b609bb5db5816f5bf2`。
