import csv
import argparse


def read_csv(file_path):
    """读取 CSV 文件，兼容 UTF-8 BOM。"""
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def inner_join(left_rows, right_rows):
    """按照 person_id 执行 Inner Join。"""

    # 检查 A 方 person_id 是否唯一
    left_index = {}

    for row in left_rows:
        person_id = row["person_id"]

        if person_id in left_index:
            raise ValueError(f"A 方 person_id 重复：{person_id}")

        left_index[person_id] = row

    # 遍历 B 方，保留所有匹配的结算记录
    join_result = []

    for right in right_rows:
        person_id = right["person_id"]

        if person_id in left_index:
            left = left_index[person_id]

            join_result.append({
                "person_id": person_id,
                "product_code": left["product_code"],
                "settlement_id": right["settlement_id"],
                "total_expense_cent": right["total_expense_cent"]
            })

    return join_result


def main():
    parser = argparse.ArgumentParser(description="医保商保数据明文 Inner Join")
    parser.add_argument("--left", required=True, help="A 方 CSV 文件路径")
    parser.add_argument("--right", required=True, help="B 方 CSV 文件路径")
    args = parser.parse_args()

    left_rows = read_csv(args.left)
    right_rows = read_csv(args.right)

    result = inner_join(left_rows, right_rows)

    print("Inner Join 结果：")
    for row in result:
        print(row)

    print("匹配记录数：", len(result))


if __name__ == "__main__":
    main()
