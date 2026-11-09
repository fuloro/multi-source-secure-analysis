# Join 与 Group By 接口对接 v0.1

日期：2026-11-05。状态：合成数据联调接口，待双方确认。

本目录对接`backend/join` 的明文 Join 与 `backend/groupby` 的 SPU Group-By，不修改双方原代码。当前可运行链路为双方 CSV → 输入校验 → 组员明文 Join → 固定容量适配 → SPU 聚合 → 合成数据结果对照。它不是安全 Join→Group-By 端到端实现。

## 统一字段

| 接口语义 | 医保主应用 | 消费拓展应用 |
| --- | --- | --- |
| 主体键 | person_id | user_id |
| 分组键 | product_code | age_band |
| 右表记录键 | settlement_id | transaction_id |
| 金额 | total_expense_cent | amount_cent |

输入校验复用 Group-By 成果中的实验校验器，先转为受约束的整数，再将两场景映射为原 Join 函数的字段。左表主体唯一，右表记录键唯一、主体可重复；每笔匹配分别计数。记录 ID 仅校验与合成对照使用，不送入聚合接口。

## Join 输出与 Group By 输入

`JoinBatch(group_key, amount_cent, valid)` 是三个等长一维 int32 数组。协议为三方 ABY3、FM64；三列（包括 valid）均以 VIS_SECRET 编译输入。valid 只允许 0/1，不由金额或 ID 是否为零推导。输入合法性由拥有方适配器保证，内核不提供恶意输入合法性证明。

左右公开输入容量 N、M；初版统一中间容量 K=N×M。当前 N=M=4，因此 K=16。即使没有匹配，仍使用 16 槽。聚合内核返回同样容量，不以真实匹配数或组数调整消息长度。数据行顺序不是接口语义的一部分。

真实安全 Join 应在 MPC 内为每个行对生成 `valid = left_valid AND right_valid AND id_equal`，传递左分组键与右金额；填充不得贡献聚合。不可在宿主程序按秘密位过滤、取长度或打印中间表。本次明文适配器会先获得匹配列表再补齐，仅允许合成数据使用，不能借此宣称隐藏了输入或匹配规模。

## 聚合输出

`AggregateBatch(group_key, count, sum_cent, mean_numerator, mean_denominator, valid)`，六个秘密 int32 数组，形状均为 `[K]`。

COUNT/SUM/MEAN 复用一次 `groupby_common`，分别从共同分组中取计数、总和。均值以总和与计数精确表示，不额外运行仅均值约分算法。分子为 sum，分母为 count；无效槽为 group=0、count=0、sum=0、分子=0、分母=1、valid=0。有效组按键排序。

初版金额上限 100000000 分，采用保守界 K×上限≤2147483647。容量变更先检查该界并重新验收，不能自动扩容。金额显示在最终授权恢复后以 Fraction/Decimal 转为元，ROUND_HALF_UP 保留两位；不逐条先舍入。

前端业务字段仍沿用项目字典：医疗使用 product_code、record_count、sum_expense_cent、mean_expense_cent；消费使用 age_band、transaction_count、sum_amount_cent、mean_amount_cent。后端保留均值分子和分母，展示层再形成对应均值字段，避免 JSON 浮点丢精度。示例联调报告中 rows 为通用字段，不等同于已经发布的前端 API。

## 运行与验收

在项目根目录的 WSL Python 3.11/SPU 环境执行，依赖原来的两个成果目录，保留新的目录关系：

```bash
python -B backend/integration/join_groupby_adapter.py --all --output backend/integration/acceptance-results.json
python -B backend/integration/join_groupby_adapter.py --scenario medical_insurance --case demo --output backend/integration/demo-results.json
```

测试使用现有两场景共 30 组样例；14 组正常输入把实际组员 Join 返回值与独立参考及预期文件核对，再送入 SPU 验证聚合，16 组异常输入在 Join 前拒绝。测试不把 expected_join.csv 当作计算输入。新生成结果单独保存，不覆盖原报告。辅助校验器固定当前批次和容量，尚不是通用业务服务。

2026-11-05 本地 WSL Python 3.11/SPU 环境联调：30/30 符合预期，14 组正常输入通过容量 16 的 SPU COUNT/SUM/MEAN 联合内核，16 组异常输入按预期拒绝，进程退出码 0。逐例证据见 acceptance-results.json。本次仅验收明文 Join 与安全聚合之间的合成数据适配，不计为安全 Join 流水线通过。

## 安全 Join 替换位置与责任

`secure_join_kernel` 是唯一预留的安全 Join 算法入口，当前明确抛出 NotImplementedError。其六个输入依次为 left_ids、left_groups、left_valid、right_ids、right_amounts、right_valid，分别形状 `[N]` 或 `[M]`，全为秘密 int32。返回上述 JoinBatch，形状 `[N*M]`。`secure_pipeline_kernel` 已写好其与聚合的组合关系；后续须将六列一次秘密输入编译此组合内核，不调用明文适配器，也不在两次模拟器调用之间传递恢复结果。

Join 负责人实现并验证此入口；Group-By 负责人确认三列及有效位契约与容量；C 负责同会话编排、输入适配和授权结果服务；D 负责场景字段及展示映射。原接口草案“输出给 B”统一改为“本批次指定分析者”，双方机构不默认获得输出。实际身份授权服务仍待 C 实现。

下一阶段通过条件：同一次共享执行中完成安全 Join→本聚合内核；覆盖唯一键、一对多、无交集、零金额及全无效；仅指定分析者恢复固定容量最终结果。验证中间有效位、匹配数及组大小不进入公共日志；本目录的合成测试进程持有双方明文和最终结果，不代表生产隔离或权限已经实现。

## 2026 年 11 月 9 日目录调整

已上传的第一周A成果迁至 backend/join；Secrecy-Project-Group-by-Backend-main 迁至 backend/groupby。Word 中旧目录名以此映射为准，接口不变。Group-By 独立命令请先进入 backend/groupby 后运行。
