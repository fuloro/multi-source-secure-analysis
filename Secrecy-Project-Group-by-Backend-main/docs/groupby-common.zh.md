# 共同分组和 SUM 的文件分工

各聚合位于 `src/backend/groupby/algorithm/g_{sum,count,mean,max,min,median}.py`。
六种聚合已实现；当前模块与精确分数接口参见 [聚合说明](aggregates.zh.md)。旧路径作为兼容入口。
`gen_perm.py`、`apply_perm.py`、`apply_inv.py` 各负责一个置换操作；
`permutation.py` 保留统一导入入口，`_validation.py` 负责公开形状和类型检查。

## GroupBy.common 并非只返回最终键

依据：[论文 §4.1、Protocol 4.1](https://eprint.iacr.org/2024/141.pdf)。
`g_common.py` 返回命名元组，避免依赖位置记忆六种中间量。

| 论文字段 | 代码字段 | 作用 |
| --- | --- | --- |
| kG | keys_grouped | 分组顺序的键 |
| vG | values_grouped | 对应数值；扩展为将无效行数值清零 |
| e | end_flags | 秘密组末尾标志 |
| kGN | keys_masked | 只有组末尾保留键，其他载荷清零 |
| πGNtoOUT | output_perm | 将组末尾稳定移动到前部的秘密置换 |
| kOUT | keys_out | 固定容量的分组输出键 |
| 本项目扩展 | valid_grouped / valid_out | 分别区分输入填充和输出填充 |

所有字段均是计算内部状态；不允许因为返回了对象就向业务端公开。
`keys_masked` 以 end_flags 区分合法零和填充；`keys_out` 以 valid_out 区分。
因此不能对 keys_out 使用非零过滤。
默认只按有效性和键排序；公开编译期选项 `sort_values=True` 增加组内数值排序。
返回值为 NamedTuple，可作为 JAX/SPU 的数组树使用。

## SUM 如何复用

`groupby_sum` 调用 common 后交给 `aggregates.sum.sum_from_common`，后者也可直接接收已计算的 common。
按照论文 Protocol 4.4，先计算全局前缀和，组末尾选择该前缀值，其他位置选择总和；
应用输出置换后作相邻差分。末尾填充位置因此得到零。

## 明确的适配差异

- 论文的 null 在本项目用零载荷加秘密有效位表达，增加全无效和空输入处理。
- 对无效行屏蔽数值，并禁止无效行产生组末尾；每个结果仍为公开容量 N。
- 底层使用 SPU 排序封装的置换，不能继承论文专用置换的通信成本。
- ABY3 半诚实运行环境不继承论文的恶意安全证明。
- 使用 int32，调用方须保证有效位为 0/1，输入金额绝对值总和不超过 int32 上限。
- 论文步骤从可检索的原文片段核对；这不是完整密码协议与安全证明的复现。

## 验证

运行 `test_common.py` 验证各字段、排序选项、全无效输入、零键、负值、零和、
填充及空输入，并与原分段扫描基线比较。`demo_sum.py` 继续用独立 Python 整数
参考实现验证随机/边界数据和医疗保险样例。`test_permutation.py` 验证置换方向与稳定性。
这些均为合成数据测试，模拟器会重构测试返回值。
