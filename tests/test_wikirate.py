import wikirate4py
import urllib.parse
from pprint import pprint

api = wikirate4py.API('JoDaOQXoU2vzgRAbaArQlwtt')

def fuzzy_search_company(query: str, limit: int = 10):
    """Perform a fuzzy search for companies on Wikirate"""
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"/search.json?q={encoded_query}&type=Company"
        response = api.get(url)
        all_items = response.json().get("items", [])

        # ✅ Only include items of type Company
        companies = [item for item in all_items if item.get("type") == "Company"][:limit]

        if not companies:
            print(f"❗ No companies found related to '{query}'")
            return []

        print(f"🔍 Companies found for query '{query}' (raw Company entries):")
        for i, item in enumerate(companies, 1):
            print(f"\n[{i}] Company Name: {item.get('name')}")
            print(f"    URL: {item.get('url')}")
        return companies

    except Exception as e:
        print("❌ Search error:", e)
        return []

# 🧪 Test fuzzy search with keyword "apple"
fuzzy_search_company("apple")
