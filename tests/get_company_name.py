from wikirate4py import API
from pprint import pprint
import pandas as pd
from name_matching.name_matcher import NameMatcher
import time
import csv
import re
import multiprocessing

api = API("JoDaOQXoU2vzgRAbaArQlwtt")

# Multi-threaded fetching of company id, company name, and ISIN count
PAGE_SIZE = 100
MAX_PAGES = 100000  # Estimated maximum pages, will stop automatically if no data
OUTPUT_FILE = "wikirate_companies_all.csv"  # Desired output file
csv_path = "wikirate_companies_all.csv"

def get_isin_count(company):
    """Read the number of ISINs from a company object"""
    try:
        isin = getattr(company, "isin", None)
        isin_list = isin if isinstance(isin, list) else []
        return len(isin_list)
    except Exception as e:
        print(f"⚠️ Cannot process company {company}: {e}")
        return 0

def worker(task_queue, result_queue, worker_id):
    """Each process fetches data for the given offset page"""
    while True:
        try:
            offset = task_queue.get(timeout=2)
        except:
            break  # Exit if no new task

        companies = api.get_companies(limit=PAGE_SIZE, offset=offset)
        if not companies:
            print(f"🚫 Worker {worker_id} - offset {offset} has no data, stopping")
            break

        results = []
        for company in companies:
            isin_count = get_isin_count(company)
            results.append((str(company.id), str(company.name), isin_count))

        for row in results:
            result_queue.put(row)

        print(f"✅ Worker {worker_id} - fetched offset {offset}, total {len(companies)} records")
        time.sleep(0.2)  # Control speed to avoid API limits

def parallel_fetch(num_workers=6):
    manager = multiprocessing.Manager()
    task_queue = manager.Queue()
    result_queue = manager.Queue()

    # Dynamically generate offset tasks
    for i in range(MAX_PAGES):
        task_queue.put(i * PAGE_SIZE)

    # Create multiple processes
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=worker, args=(task_queue, result_queue, i))
        p.start()
        processes.append(p)

    # Wait for all to finish
    for p in processes:
        p.join()

    print("📝 All workers completed, preparing to write file...")

    # Write CSV results
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "name", "isin_count"])
        while not result_queue.empty():
            writer.writerow(result_queue.get())

    print(f"📁 Written to {OUTPUT_FILE}")

# ✅ Execute main program
if __name__ == "__main__":
    parallel_fetch(num_workers=6)

# ============================================================================================================

# Fuzzy name matching
# ✅ Custom normalization function (mimicking NameMatcher transform=True)
def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s]', '', name)   # Remove punctuation
    name = re.sub(r'\s+', ' ', name)          # Remove extra whitespace
    return name.strip()

# ✅ Main function: perform fuzzy match on input name and select best match by ISIN count
def find_best_matching_company(input_name: str, wikirate_companies: list) -> str:
    
    keyword = input_name.lower()
    filtered_companies = [c for c in wikirate_companies if keyword in c['name'].lower()]
    if not filtered_companies:
        print("❌ No company found containing the keyword")
        return None

    # ✅ Print all matching companies
    print("🔍 Found the following companies containing the keyword:")
    for c in filtered_companies:
        print(f" - {c['name']}")

    company_names = [c['name'] for c in filtered_companies]

    # Create normalization mapping
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

    # 🧪 Print all matching names and scores
    print("🧪 All matching results:")
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
                print(f"{i+1}. {match_name}  👉 Score: {score:.2f}  🆔 ISIN count: {isin_count}")
                results.append((normalized, score))

    if not results:
        return None

    # Find highest score
    max_score = max(score for _, score in results)
    top_matches = [name for name, score in results if score == max_score]

    # If only one top match → return original name
    if len(top_matches) == 1:
        return normalized_map.get(top_matches[0], {}).get('original_name', top_matches[0])

    # If multiple top matches → select by ISIN count
    best_match = max(top_matches, key=lambda name: normalized_map.get(name, {}).get('isin_count', 0))
    return normalized_map.get(best_match, {}).get('original_name', best_match)