# 客群消费分析模拟数据包

日期：2026-11-03。仅含合成数据，供人工验收和后续接口联调。

本包共 15 组样例：7 组 SUCCESS、8 组 REJECT。请先使用 demo，再按 reference_only/case_index.json 验收全部样例。每次须使用同一 case 下的双方文件及 public_config.json。

- owner_a/：数据方 A 的原始 CSV。
- owner_b/：数据方 B 的原始 CSV。
- public_config.json：公开场景、期间、单位与容量，不包含真实行数或匹配数。
- 每个 case 的 reference_only/：仅用于合成数据验收的明文答案及异常预期。
- 场景根目录 reference_only/case_index.json：本场景测试索引，非公共运行配置。
- SHA256SUMS.json：本包其他文件的 SHA-256，用于完整性核对。

金额统一为人民币整数分，左右公开容量均为 4。空表为仅表头 CSV；真正执行前须填充为非零容量并使用秘密有效位。正常样例的 expected.json 给出精确分数和金额显示参考；expected_result.csv 是方便阅读的小数表。异常样例必须在输入阶段拒绝，不静默纠正或截断。

reference_only/expected_join.csv 禁止接入安全运行通路。目录划分不等于访问控制；真实部署由双方本地输入，仅授权分析者恢复最终聚合结果。不得从本机合成数据便利条件推断中央服务可以持有真实双方 CSV。

本数据包不包含完整 CSV 到 MPC 的运行服务，也不表示本批全部样例已通过 MPC 回归。业务定义、字段约束、权限与待验收事项详见同批交付的《数据使用说明》。
