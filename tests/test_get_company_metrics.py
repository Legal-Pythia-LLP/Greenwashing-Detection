from app.core.tools import WikirateClient
from app.config import WIKIRATE_API_KEY
import json
import os

def test_get_company_metrics():
    """Test fetching ESG metrics data for companies"""
    
    # Initialize client
    wikirate_client = WikirateClient(WIKIRATE_API_KEY)
    
    # Test company list
    test_companies = ["Apple Inc", "Puma", "HSBC", "KPMG UNITED KINGDOM PLC"]
    
    # Store all test results
    all_results = {}
    
    for company_name in test_companies:
        print(f"\n{'='*60}")
        print(f"Testing company: {company_name}")
        print(f"{'='*60}")
        
        try:
            # Fetch ESG metrics data
            results = wikirate_client.get_company_metrics(company_name)
            
            # Store results
            all_results[company_name] = results
            
            # Check for errors
            if "error" in results:
                print(f"❌ Error: {results['error']}")
                continue
            
            # Print basic info
            print(f"✅ Company Name: {results.get('company_name')}")
            print(f"📊 Total Answers: {results.get('total_answers')}")
            print(f"🌱 ESG Metrics Count: {results.get('esg_metrics_count')}")
            
            # Print ESG data details
            esg_data = results.get('esg_data', [])
            if esg_data:
                print(f"\n📋 ESG Data Details (first 5 records):")
                for i, record in enumerate(esg_data[:5], 1):
                    print(f"  {i}. Metric: {record.get('metric_name')}")
                    print(f"     Year: {record.get('year')}")
                    print(f"     Value: {record.get('value')}")
                    print(f"     Unit: {record.get('unit', 'N/A')}")
                    print()
            else:
                print("⚠️  No ESG data found")
            
            # Save individual company result to JSON file
            filename = f"test_results_{company_name.replace(' ', '_')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"💾 Results saved to: {filename}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            all_results[company_name] = {"error": str(e)}
            continue
    
    # Save all results to a single JSON file
    current_file = os.path.basename(__file__)
    json_filename = current_file.replace('.py', '.json')
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 All test results saved to: {json_filename}")
    return all_results

def test_single_company():
    """Test detailed data for a single company"""
    
    wikirate_client = WikirateClient(WIKIRATE_API_KEY)
    company_name = "Apple Inc"
    
    print(f"\n{'='*60}")
    print(f"Detailed Test: {company_name}")
    print(f"{'='*60}")
    
    results = wikirate_client.get_company_metrics(company_name)
    
    if "error" not in results:
        print(f"✅ Successfully fetched data")
        print(f"📊 Total Answers: {results.get('total_answers')}")
        print(f"🌱 ESG Metrics Count: {results.get('esg_metrics_count')}")
        
        # Display all ESG data
        esg_data = results.get('esg_data', [])
        print(f"\n📋 All ESG Data:")
        for i, record in enumerate(esg_data, 1):
            metric_name = record.get('metric_name', '')
            year = record.get('year', '')
            value = record.get('value', '')
            unit = record.get('unit', '')
            print(f"{i:2d}. {metric_name} ({year}) = {value} {unit}")
    else:
        print(f"❌ Error: {results['error']}")

if __name__ == "__main__":
    print("Starting test for get_company_metrics function...")
    
    # Run general test
    all_results = test_get_company_metrics()
    
    # Run detailed test
    # test_single_company()
    
    print("\nTesting completed!")