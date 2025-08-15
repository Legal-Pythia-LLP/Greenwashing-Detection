import wikirate4py
import urllib.parse
from pprint import pprint


api = wikirate4py.API('JoDaOQXoU2vzgRAbaArQlwtt')

# # requesting to get details about a specific Wikirate company based on name
# # wikirate4py models the response into a Company object
# company = api.get_company('Puma')

# # print company's details
# pprint(company.json())

# # get the raw json response
# pprint(company.raw_json())

# # print company's aliases
# for alias in company.aliases:
#     print(alias)

# # Get the Metric object for Address metric with metric designer Clean Clothes Campaign
# metric = api.get_metric(metric_name='Address', metric_designer='Clean Clothes Campaign')

# print(metric.id)
# print(metric.name)
# print(metric.designer)
# print(metric.question)
# print(metric.value_type)
# print(metric.json())
# print(metric.raw_json())

# # prints all available parameters of Metric model
# print(metric.get_parameters())


# 初始化 API 實例，API key 可選
# api = wikirate4py.API("JoDaOQXoU2vzgRAbaArQlwtt")  # 可留空：API()

# def fuzzy_search_company(query: str, limit: int = 10):
#     try:
#         companies = api.search_company(query=query, limit=limit)
#         if not companies:
#             print(f"❗ 找不到與 '{query}' 相關的公司")
#             return []

#         print(f"🔍 找到與 '{query}' 相關的公司：")
#         for i, company in enumerate(companies, start=1):
#             print(f"\n[{i}] 公司名稱: {company.name}")
#             print(f"    ID: {company.id}")
#             print(f"    網站: {company.website}")
#             print(f"    別名: {company.aliases}")
#         return companies

#     except Exception as e:
#         print("❌ 搜尋發生錯誤:", e)
#         return []

# 🧪 測試搜尋：關鍵字 "apple"
# fuzzy_search_company("apple")

def fuzzy_search_company(query: str, limit: int = 10):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"/search.json?q={encoded_query}&type=Company"
        response = api.get(url)
        all_items = response.json().get("items", [])

        # ✅ 只要是 Company 都列出來，不做額外 alias 檢查
        companies = [item for item in all_items if item.get("type") == "Company"][:limit]

        if not companies:
            print(f"❗ 找不到與 '{query}' 相關的公司")
            return []

        print(f"🔍 找到與 '{query}' 相關的公司（原始 Company 條目）：")
        for i, item in enumerate(companies, 1):
            print(f"\n[{i}] 公司名稱: {item.get('name')}")
            print(f"    網址: {item.get('url')}")
        return companies

    except Exception as e:
        print("❌ 搜尋發生錯誤:", e)
        return []

fuzzy_search_company("apple")


