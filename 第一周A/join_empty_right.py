
import csv

# 双方数据文件的位置
left_file = "data/medical_insurance/medical_insurance/empty_right/owner_a/insured_members.csv"
right_file = "data/medical_insurance/medical_insurance/empty_right/owner_b/medical_settlements.csv"

# 读取 A 方数据
with open(left_file, "r", encoding="utf-8-sig", newline="") as f:
    left_rows = list(csv.DictReader(f))

# 读取 B 方数据
with open(right_file, "r", encoding="utf-8-sig", newline="") as f:
    right_rows = list(csv.DictReader(f))

# 建立 A 方的 person_id 索引
left_index = {}

for row in left_rows:
    person_id = row["person_id"]
    left_index[person_id] = row

# 执行 Inner Join
join_result = []

for right in right_rows:
    person_id = right["person_id"]

    # 只有双方 person_id 相同，才保留记录
    if person_id in left_index:
        left = left_index[person_id]

        join_result.append({
            "person_id": person_id,
            "product_code": left["product_code"],
            "settlement_id": right["settlement_id"],
            "total_expense_cent": right["total_expense_cent"]
        })

# 输出结果
print("Inner Join 结果：")
for row in join_result:
    print(row)

print("匹配记录数：", len(join_result))
