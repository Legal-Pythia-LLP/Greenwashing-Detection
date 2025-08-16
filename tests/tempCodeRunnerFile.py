# Test parameters
# input_name = "apple"
# csv_path = "wikirate_companies_2000.csv"

# # Read CSV
# df = pd.read_csv(csv_path)

# # Ensure required columns exist
# if "name" not in df.columns or "isin_count" not in df.columns:
#     raise ValueError("CSV file must contain 'name' and 'isin_count' columns")

# # Prepare as list of dicts
# wikirate_companies = df[["name", "isin_count"]].to_dict(orient="records")

# # Execute matching function
# best_match = find_best_matching_company(input_name, wikirate_companies)

# # Output result
# print(f"\n📌 For input '{input_name}', the best matching company name is: {best_match}")
