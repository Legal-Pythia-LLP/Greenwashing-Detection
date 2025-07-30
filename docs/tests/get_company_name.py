from wikirate4py import API
from pprint import pprint
import pandas as pd
from name_matching.name_matcher import NameMatcher
import time
import csv
import re
import multiprocessing

api = API("JoDaOQXoU2vzgRAbaArQlwtt")
# company = api.get_company("KPMG UNITED KINGDOM PLC")

# all_companies = []
# limit = 100
# offset = 0

# # while True:
# #     batch = api.get_companies(limit=limit, offset=offset)
# #     if not batch:
# #         break
# #     all_companies.extend(batch)

# #     print(f"✅ 抓取中: 累計 {len(all_companies)} 家公司")
# #     if len(batch) < limit:
# #         break

# #     offset += limit
# #     time.sleep(0.2)  # 建議小延遲避免過快被API限制

# companies = api.get_companies(limit=100, offset=0)
# print(f"✅ 已獲得 {len(companies)} 家公司資料")

# # print("📋 取得公司清單：")
# # for c in companies:
# #     print(c)

# # if companies:
# #     print("第一家公司範例：", companies[0])
# # else:
# #     print("❌ 沒有任何公司被回傳")



# # 將結果寫入 CSV 檔案
# with open("wikirate_companies.csv", "w", newline="", encoding="utf-8") as csvfile:
#     writer = csv.writer(csvfile)
#     writer.writerow(["id", "name"])  # 寫入欄位名稱
#     for i, company in enumerate(companies, start=1):
#         writer.writerow([str(company.id), str(company.name)])
#         print(f"type(company.id): {type(company.id)}")
#         print(f"type(company.name): {type(company.name)}")
#         print(f"📝 寫入第 {i} 筆：{company.name}")


# print("📁 公司名稱已寫入 wikirate_companies.csv ✅")

# 抓全部
# all_companies = []
# limit = 100
# offset = 0
# total_fetched = 0

# print("🚀 開始抓取所有公司資料...")

# while True:
#     batch = api.get_companies(limit=limit, offset=offset)
#     if not batch:
#         break

#     all_companies.extend(batch)
#     total_fetched += len(batch)

#     print(f"✅ 已抓取 {total_fetched} 家公司...")

#     if len(batch) < limit:
#         print("✅ 已抓取到最後一頁")
#         break

#     offset += limit
#     time.sleep(0.01)  # 加小延遲以防 API rate limit

# print(f"\n📦 共取得 {len(all_companies)} 家公司資料，準備寫入 CSV...")

# # 寫入 CSV
# with open("wikirate_companies_all.csv", "w", newline="", encoding="utf-8") as csvfile:
#     writer = csv.writer(csvfile)
#     writer.writerow(["id", "name"])
#     for i, company in enumerate(all_companies, start=1):
#         writer.writerow([str(company.id), str(company.name)])
#         if i % 500 == 0:
#             print(f"📝 寫入第 {i} 筆：{company.name}")

# print("📁 公司名稱已完整寫入 wikirate_companies_all.csv ✅")

# ============================================================================================================

# 抓2000
# all_companies = []
# limit = 100
# max_total = 2000  # 要抓幾筆資料
# offset = 0

# with open("wikirate_companies_2000.csv", "w", newline="", encoding="utf-8") as csvfile:
#     writer = csv.writer(csvfile)
#     writer.writerow(["id", "name"])  # 寫入表頭欄位

#     while len(all_companies) < max_total:
#         companies = api.get_companies(limit=limit, offset=offset)

#         if not companies:
#             print("❌ 沒有更多公司資料了，提前結束")
#             break

#         all_companies.extend(companies)

#         for company in companies:
#             writer.writerow([str(company.id), str(company.name)])

#         print(f"✅ 第 {offset // limit + 1} 頁，共 {len(all_companies)} 筆")

#         offset += limit

# print("📁 公司名稱已寫入 wikirate_companies_2000.csv ✅")

# ============================================================================================================
# 批量抓2000

# search_names = ["Apple", "Puma", "HSBC", "KPMG", "JP Morgan"]

# company = api.get_company("Apple Inc.")
# if not company:
#     print("❌ 公司未找到")
#     exit()
# else:
#     print(company)

# all_companies = []
# total_target = 2000
# page_size = 100  # 每頁最多可抓100筆
# pages_per_round = 5  # 每輪抓幾頁（一次最多500筆）
# offset = 0

# with open("wikirate_companies_2000.csv", "w", newline="", encoding="utf-8") as csvfile:
#     writer = csv.writer(csvfile)
#     writer.writerow(["id", "name"])  # 寫入表頭

#     while len(all_companies) < total_target:
#         batch_companies = []

#         for i in range(pages_per_round):
#             if len(all_companies) + len(batch_companies) >= total_target:
#                 break

#             companies = api.get_companies(limit=page_size, offset=offset)
#             if not companies:
#                 print("❌ 沒有更多公司資料了，提前結束")
#                 break

#             batch_companies.extend(companies)
#             offset += page_size
#             print(f"📥 已抓第 {offset // page_size} 頁（+{len(companies)} 筆）")

#         # 寫入 CSV
#         for company in batch_companies:
#             writer.writerow([str(company.id), str(company.name)])

#         all_companies.extend(batch_companies)
#         print(f"✅ 累計 {len(all_companies)} 筆資料")

# print("📁 公司名稱已寫入 wikirate_companies_2000.csv ✅")

# ============================================================================================================


# search_names = ["Apple", "Puma", "HSBC", "KPMG", "JP Morgan"]

# company = api.get_company("Apple Inc.")
# if not company:
#     print("❌ 公司未找到")
#     exit()
# else:
#     print(company)

# 測試抓 ISIN 數量
# def get_isin_count(company):
#     """直接接收 company 物件，回傳 ISIN 數量"""
#     try:
#         isin_list = company.isin if hasattr(company, "isin") else []
#         isin_count = len(isin_list)

#         print(f"🆔 ID: {company.id}")
#         print(f"🏷️ Name: {company.name}")
#         print(f"111🔢 ISIN 數量: {isin_count}")
#         return isin_count

#     except Exception as e:
#         print(f"⚠️ 無法處理公司 {company}: {e}")
#         return 0

# def get_isin_count_by_id_or_name(company_id_or_name):
#     try:
#         company = api.get_company(company_id_or_name)
#         if not company:
#             print(f"❌ 找不到公司: {company_id_or_name}")
#             return 0
#         return get_isin_count(company)
#     except Exception as e:
#         print(f"⚠️ 無法取得公司 {company_id_or_name} 的 ISIN 數量: {e}")
#         return 0

# # 🔍 指定公司 ID 測試
# target_company_id = 637  # Apple Inc.
# company = api.get_company(target_company_id)
# if not company:
#     print("❌ 找不到公司")
# else:
#     isin_count = get_isin_count(company)




# 🔍 指定公司 ID 測試
# target_company_id = 637  # 👈 你可以改成任何一間公司的 ID（例如 Apple 是 1578）
# company = api.get_company(target_company_id)

# print(f"🆔 ID: {company.id}")
# print(f"🏷️ Name: {company.name}")
# print(f"🔢 ISIN 數量: {isin_count}")

# ============================================================================================================

# 抓2000 並且抓 ISIN 數量


# all_companies = []
# total_target = 300
# page_size = 100  # 每頁最多可抓100筆
# pages_per_round = 5  # 每輪抓幾頁（一次最多500筆）
# offset = 0

# def get_isin_count(company):
#     """直接從公司物件中讀取 ISIN 數量"""
#     try:
#         isin = getattr(company, "isin", None)
#         isin_list = isin if isinstance(isin, list) else []
#         isin_count = len(isin_list)

#         print(f"🆔 ID: {company.id}")
#         print(f"🏷️ Name: {company.name}")
#         print(f"🔢 ISIN 數量: {isin_count}")
#         return isin_count

#     except Exception as e:
#         print(f"⚠️ 無法處理公司 {company}: {e}")
#         return 0

# with open("wikirate_companies_2000.csv", "w", newline="", encoding="utf-8") as csvfile:
#     writer = csv.writer(csvfile)
#     writer.writerow(["id", "name", "isin_count"])  # 寫入表頭

#     # while len(all_companies) < total_target: //看要抓多少
#     while True: # 無限抓
#         batch_companies = []

#         for i in range(pages_per_round):
#             # if len(all_companies) + len(batch_companies) >= total_target:
#             #     break

#             companies = api.get_companies(limit=page_size, offset=offset)
#             if not companies:
#                 print("❌ 沒有更多公司資料了，提前結束")
#                 break

#             for company in companies:
#                 isin_count = get_isin_count(company)  # ✅ 改成直接傳 company
#                 writer.writerow([str(company.id), str(company.name), isin_count])
#                 time.sleep(0.2)  # 控制速度避免 API 限制

#             batch_companies.extend(companies)
#             offset += page_size
#             print(f"📥 已抓第 {offset // page_size} 頁（+{len(companies)} 筆）")

#         all_companies.extend(batch_companies)
#         print(f"✅ 累計 {len(all_companies)} 筆資料")

# print("📁 公司名稱與 ISIN 數量已寫入 wikirate_companies_2000.csv ✅")

# ============================================================================================================
# # 多線程抓 company id, company name, ISIN 數量
# PAGE_SIZE = 100
# MAX_PAGES = 100000  # 預估最多抓幾頁，無資料時會自動停止
# OUTPUT_FILE = "wikirate_companies_all.csv"  # ✅ 你要的檔名

# def get_isin_count(company):
#     """從公司物件中讀取 ISIN 數量"""
#     try:
#         isin = getattr(company, "isin", None)
#         isin_list = isin if isinstance(isin, list) else []
#         return len(isin_list)
#     except Exception as e:
#         print(f"⚠️ 無法處理公司 {company}: {e}")
#         return 0

# def worker(task_queue, result_queue, worker_id):
#     """每個進程抓取指定 offset 頁的資料"""
#     while True:
#         try:
#             offset = task_queue.get(timeout=2)
#         except:
#             break  # 沒有新工作就退出

#         companies = api.get_companies(limit=PAGE_SIZE, offset=offset)
#         if not companies:
#             print(f"🚫 Worker {worker_id} - offset {offset} 沒有資料，停止")
#             break

#         results = []
#         for company in companies:
#             isin_count = get_isin_count(company)
#             results.append((str(company.id), str(company.name), isin_count))

#         for row in results:
#             result_queue.put(row)

#         print(f"✅ Worker {worker_id} - 抓取 offset {offset} 共 {len(companies)} 筆")
#         time.sleep(0.2)  # 控制速度避免 API 限制

# def parallel_fetch(num_workers=6):
#     manager = multiprocessing.Manager()
#     task_queue = manager.Queue()
#     result_queue = manager.Queue()

#     # 動態產生 offset 任務
#     for i in range(MAX_PAGES):
#         task_queue.put(i * PAGE_SIZE)

#     # 建立多個進程
#     processes = []
#     for i in range(num_workers):
#         p = multiprocessing.Process(target=worker, args=(task_queue, result_queue, i))
#         p.start()
#         processes.append(p)

#     # 等待全部完成
#     for p in processes:
#         p.join()

#     print("📝 所有 worker 完成，準備寫入檔案...")

#     # 寫入 CSV 結果
#     with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow(["id", "name", "isin_count"])
#         while not result_queue.empty():
#             writer.writerow(result_queue.get())

#     print(f"📁 已寫入 {OUTPUT_FILE}")

# # ✅ 執行主程式
# if __name__ == "__main__":
#     parallel_fetch(num_workers=6)

# ============================================================================================================

# 名字模糊比對
# ✅ 自訂 normalization 方法（模仿 NameMatcher transform=True）
def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s]', '', name)   # 移除標點符號
    name = re.sub(r'\s+', ' ', name)          # 移除多餘空白
    return name.strip()


# ✅ 主函數：根據輸入名稱模糊比對，並根據 ISIN 數量選擇最佳匹配
def find_best_matching_company(input_name: str, wikirate_companies: list) -> str:
    
    keyword = input_name.lower()
    filtered_companies = [c for c in wikirate_companies if keyword in c['name'].lower()]
    if not filtered_companies:
        print("❌ 找不到任何名稱包含關鍵字的公司")
        return None

    # ✅ 印出所有符合條件的公司名稱
    print("🔍 找到以下包含關鍵字的公司：")
    for c in filtered_companies:
        print(f" - {c['name']}")

    company_names = [c['name'] for c in filtered_companies]

    # 建立轉換對照表
    normalized_map = {}
    for c in wikirate_companies:
        original_name = c['name'] if isinstance(c, dict) else c
        normalized = normalize_name(original_name)
        normalized_map[normalized] = {
            'original_name': original_name,
            'isin_count': c.get('isin_count', 0) if isinstance(c, dict) else 0
        }

    df_master = pd.DataFrame({'Company name': company_names})
    df_input = pd.DataFrame({'name': [input_name]})

    matcher = NameMatcher(
        number_of_matches=5,
        legal_suffixes=True,
        common_words=False,
        top_n=50,
        verbose=False
    )
    matcher.set_distance_metrics(['bag', 'typo', 'refined_soundex'])
    matcher.load_and_process_master_data(column='Company name', df_matching_data=df_master, transform=True)
    matches = matcher.match_names(to_be_matched=df_input, column_matching='name')

    if matches.empty:
        return None

    # 🧪 印出所有匹配的名稱與分數
    print("🧪 所有匹配結果：")
    results = []
    for i in range(5):
        match_name_col = f'match_name_{i}'
        score_col = f'score_{i}'
        if match_name_col in matches.columns and score_col in matches.columns:
            match_name = matches.at[0, match_name_col]
            score = matches.at[0, score_col]
            if pd.notna(match_name):
                normalized = normalize_name(match_name)
                isin_count = normalized_map.get(normalized, {}).get('isin_count', 0)
                print(f"{i+1}. {match_name}  👉 分數: {score:.2f}  🆔 ISIN數量: {isin_count}")
                results.append((normalized, score))

    if not results:
        return None

    # 找出最高分
    max_score = max(score for _, score in results)
    top_matches = [name for name, score in results if score == max_score]

    # 如果只有一個最高分 → 回傳原始名稱
    if len(top_matches) == 1:
        return normalized_map.get(top_matches[0], {}).get('original_name', top_matches[0])

    # 如果有多個最高分 → 用 isin_count 挑選
    best_match = max(top_matches, key=lambda name: normalized_map.get(name, {}).get('isin_count', 0))
    return normalized_map.get(best_match, {}).get('original_name', best_match)

# ============================================================================================================
# # test
# input_name = "Apple Inc"
# company_list = ["Apple Inc.", "Apple AB", "APPLE PTY LIMITED", "APPLE EUROPE LIMITED", "APPLE APPAREL (CAMBODIA) CO., LTD"]

# best_match = find_best_matching_company(input_name, company_list)
# print("🔍 最佳匹配結果:", best_match)

# 測試參數
input_name = "apple"
csv_path = "wikirate_companies_all.csv"

# 讀取 CSV
df = pd.read_csv(csv_path)

# 確保欄位存在
if "name" not in df.columns or "isin_count" not in df.columns:
    raise ValueError("CSV 檔案中需要包含 'name' 和 'isin_count' 欄位")

# 準備成 list of dict 結構
wikirate_companies = df[["name", "isin_count"]].to_dict(orient="records")

# 執行匹配函數
best_match = find_best_matching_company(input_name, wikirate_companies)

# 輸出結果
print(f"\n📌 對於輸入 '{input_name}'，最佳匹配公司名稱為：{best_match}")

# ============================================================================================================
# # 模擬 csv 中的公司資料
# wikirate_companies = [
#     {"id": 637, "name": "BP plc.", "isin_count": 117},
#     {"id": 932, "name": "Chevron Corporation", "isin_count": 1},
#     {"id": 993, "name": "Shell plc", "isin_count": 1},
#     {"id": 1578, "name": "Apple Inc.", "isin_count": 1004},       # ✅ 應該選這個
#     {"id": 1102, "name": "Apple AB", "isin_count": 20},
#     {"id": 1103, "name": "Apple AInc", "isin_count": 100}
# ]

# input_name = "apple"
# result = find_best_matching_company(input_name, wikirate_companies)

# print(f"\n📌 測試結果：輸入『{input_name}』，匹配到：{result}")






