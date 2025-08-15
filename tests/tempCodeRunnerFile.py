# 測試參數
# input_name = "apple"
# csv_path = "wikirate_companies_2000.csv"

# # 讀取 CSV
# df = pd.read_csv(csv_path)

# # 確保欄位存在
# if "name" not in df.columns or "isin_count" not in df.columns:
#     raise ValueError("CSV 檔案中需要包含 'name' 和 'isin_count' 欄位")

# # 準備成 list of dict 結構
# wikirate_companies = df[["name", "isin_count"]].to_dict(orient="records")

# # 執行匹配函數
# best_match = find_best_matching_company(input_name, wikirate_companies)

# # 輸出結果
# print(f"\n📌 對於輸入 '{input_name}'，最佳匹配公司名稱為：{best_match}")