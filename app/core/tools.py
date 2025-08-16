from langchain.tools import BaseTool
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain.schema import HumanMessage
from typing import Any, Optional, Dict, List
from app.core.llm import llm
from webscraper import bbc_search, cnn_search
import json
import requests
import cloudscraper
from app.config import WIKIRATE_API_KEY
from app.core.utils import search_and_filter_news  # According to your placement

# get_company_name
from wikirate4py import API
from pprint import pprint
import pandas as pd
from name_matching.name_matcher import NameMatcher
import time
import csv
import re
import multiprocessing

# Fuzzy name matching
# Custom normalization method (imitating NameMatcher transform=True)
def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s]', '', name)  # Remove punctuation
    name = re.sub(r'\s+', ' ', name)  # Remove extra spaces
    return name.strip()

def get_isin_count(company):
    """Read ISIN count from company object"""
    try:
        isin = getattr(company, "isin", None)
        isin_list = isin if isinstance(isin, list) else []
        return len(isin_list)
    except Exception as e:
        print(f"Cannot process company {company}: {e}")
        return 0


class WikirateClient:
    """Wikirate API client for retrieving and validating ESG data"""

    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://wikirate.org"
        self.api_key = api_key
        self.session = cloudscraper.create_scraper(  # Replace requests
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )

        # Cloudscraper by default attaches a real browser UA
        self.session.headers.update({
            'Accept': 'application/json'
        })

        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })

    def search_company(self, company_name: str) -> Dict[str, Any]:
        """Search for company information, supports exact and fuzzy search"""
        try:
            original_name = company_name.strip()
            clean_name = original_name.strip()
            print(f"[Wikirate] Attempting exact search: --{clean_name}--")
            direct_url = f"{self.base_url}/{clean_name}.json"

            response = self.session.get(direct_url, timeout=10)

            print(f"[DEBUG] Status Code: {response.status_code}")
            print(f"[DEBUG] Response preview:\n{response.text[:300]}")

            if response.status_code == 200:
                data = response.json()
                # Safely handle all fields to avoid None.get() errors
                def safe_get(d, key, default=None):
                    if d and isinstance(d, dict):
                        return d.get(key, default)
                    return default

                return {
                    "name": data.get("name"),
                    "url": data.get("url"),
                    "type": safe_get(data.get("type"), "name"),
                    "headquarters": (safe_get(data.get("headquarters"), "content", [None])[0]
                                     if safe_get(data.get("headquarters"), "content") else None),
                    "website": safe_get(data.get("website"), "content"),
                    "aliases": safe_get(data.get("alias"), "content", []),
                    "image_url": safe_get(data.get("image"), "content")
                }

            # If exact search fails, use search API for fuzzy search
            search_url = f"{self.base_url}/search.json"
            params = {
                'q': original_name,
                'type': 'Company'
            }

            response = self.session.get(search_url, params=params, timeout=10)
            if response.status_code == 200:
                results = response.json().get("items", [])
                for item in results:
                    if item.get("type") == "Company":
                        return item

            return {}

        except Exception as e:
            return {}

    # Main function: fuzzy match by input name and choose best match based on ISIN count
    def find_best_matching_company(self, input_name: str) -> str:
        csv_path = "wikirate_companies_all.csv"
        wikirate_companies = []

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    wikirate_companies.append({
                        'id': row['id'],
                        'name': row['name'],
                        'isin_count': int(row['isin_count'])
                    })
        except FileNotFoundError:
            print(f"Company data file not found: {csv_path}")
            return None

        keyword = input_name.lower()
        filtered_companies = [c for c in wikirate_companies if keyword in c['name'].lower()]
        if not filtered_companies:
            print("No companies found containing the keyword")
            return None

        # Print all matching company names
        print("🔍 Found the following companies containing the keyword:")
        for c in filtered_companies:
            print(f" - {c['name']}")

        company_names = [c['name'] for c in filtered_companies]

        # Build normalized mapping
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

        # Print all matched names and scores
        print("All match results:")
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
                    print(f"{i + 1}. {match_name}  Score: {score:.2f}  ISIN count: {isin_count}")
                    results.append((normalized, score))

        if not results:
            return None

        # Find highest score
        max_score = max(score for _, score in results)
        top_matches = [name for name, score in results if score == max_score]

        # If only one top score → return original name
        if len(top_matches) == 1:
            return normalized_map.get(top_matches[0], {}).get('original_name', top_matches[0])

        # If multiple top scores → select by ISIN count
        best_match = max(top_matches, key=lambda name: normalized_map.get(name, {}).get('isin_count', 0))
        return normalized_map.get(best_match, {}).get('original_name', best_match)

    def get_company_metrics(self, company_name: str) -> Dict[str, Any]:
        """Get company's ESG metrics data using wikirate4py API"""
        try:
            from wikirate4py import API

            api = API(self.api_key)
            company = api.get_company(company_name)
            if not company:
                return {"error": f"Company '{company_name}' not found"}

            all_answers = []
            limit = 10
            offset = 0
            max_total = 20  # Get up to 20 records

            while len(all_answers) < max_total:
                batch = api.get_answers(company=company.name, limit=min(limit, max_total - len(all_answers)), offset=offset)
                if not batch:
                    break
                all_answers.extend(batch)
                if len(batch) < limit or len(all_answers) >= max_total:
                    break
                offset += limit

            esg_topics = ["environment", "social", "governance"]
            esg_metrics = set()
            metric_cache = {}

            for answer in all_answers:
                metric_name = answer.metric
                if metric_name in metric_cache:
                    topics = metric_cache[metric_name]['topics']
                    unit = metric_cache[metric_name]['unit']
                else:
                    try:
                        metric_obj = api.get_metric(metric_name)
                        topics_raw = getattr(metric_obj, 'topics', [])
                        topics = []
                        for t in topics_raw or []:
                            if isinstance(t, str):
                                topics.append(t.lower())
                            elif isinstance(t, dict) and 'name' in t:
                                topics.append(t['name'].lower())
                        unit = getattr(metric_obj, 'unit', None)
                        metric_cache[metric_name] = {
                            'topics': topics,
                            'unit': unit
                        }
                    except Exception as e:
                        print(f"Failed to get metric {metric_name} info: {e}")
                        topics = []
                        unit = None
                        metric_cache[metric_name] = {
                            'topics': topics,
                            'unit': unit
                        }

                if any(topic in topics for topic in esg_topics):
                    esg_metrics.add(metric_name)

            results = {
                "company_name": company_name,
                "total_answers": len(all_answers),
                "esg_metrics_count": len(esg_metrics),
                "esg_data": []
            }

            for answer in all_answers:
                if answer.metric in esg_metrics:
                    record = {
                        "metric_name": answer.metric,
                        "year": getattr(answer, 'year', None),
                        "value": getattr(answer, 'value', None),
                        "unit": metric_cache.get(answer.metric, {}).get('unit'),
                    }
                    results["esg_data"].append(record)

            return results

        except Exception as e:
            print(f"Error getting company metrics: {e}")
            return {"error": str(e)}

    def get_metric_details(self, metric_name: str) -> Dict[str, Any]:
        """Get detailed information and definition of a metric"""
        try:
            url = f"{self.base_url}/{metric_name}.json"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()

            return {}

        except Exception as e:
            print(f"Error getting metric details for {metric_name}: {e}")
            return {}


# Wikirate Validation Tool
class WikirateValidationTool(BaseTool):
    name: str = "wikirate_validation"
    description: str = "Validates ESG metrics and claims against Wikirate database"
    company_name: str = ""
    wikirate_client: WikirateClient = None

    def __init__(self, company_name: str):
        super().__init__()
        self.company_name = company_name
        self.wikirate_client = WikirateClient(WIKIRATE_API_KEY)

    def _run(self, extracted_metrics: str) -> str:
        """Validate extracted ESG metrics against Wikirate database"""
        try:
            # Perform fuzzy match by input name and select the best match based on ISIN count
            self.company_name = self.wikirate_client.find_best_matching_company(self.company_name)

            if self.company_name:
                # Get company's ESG metrics
                metrics_data = self.wikirate_client.get_company_metrics(self.company_name)

                if "error" not in metrics_data:
                    analysis_prompt = f"""
                    You are an expert ESG validation analyst. 

                    Your task is to assess how well each ESG claim is reflected in the following Wikirate Database Data.
            
                    You need to analyze each claim as follows.
                    
                    Claims:{extracted_metrics}

                    Wikirate Database Data: {json.dumps(metrics_data, indent=2)}

                    Instruction:
                    - If the ESG data provided directly proves that the statement is true, thereby refuting or partially refuting the greenwashing allegation, mark it as “Refuted”.
                    - If the ESG data provided directly refutes the statement, thereby confirming or partially confirming the greenwashing allegation, mark it as “Supported”.
                    - If the provided ESG data relates to relevant indicators or topics but is insufficient to directly verify or refute the greenwashing allegations in the quote, please mark it as “Mentioned.”
                    - If the provided ESG data is unrelated to the quote and cannot be evaluated in any way, please mark it as “Not Mentioned.”

                    For each claim, respond with:
                    1. **Status**: Supported / Contradicted / Indicated / Not mentioned  
                    2. **Reasoning**: Explain why you chose this status  
                    3. **news_quotation**: Include any relevant metrics from Wikirate Database Data if applicable  
                    
                    """

                    response = llm.invoke([HumanMessage(content=analysis_prompt)])

                    return response.content

                else:
                    return f"Company found in Wikirate but no ESG metrics available: {metrics_data['error']}"

            else:
                return f"Company '{self.company_name}' not found in Wikirate database. Manual verification required."

        except Exception as e:
            return f"Error in Wikirate validation: {str(e)}"


class ESGDocumentAnalysisTool(BaseTool):
    name: str = "esg_document_analysis"
    description: str = "Analyzes ESG documents for greenwashing indicators using vector search and semantic analysis"
    vector_store: Any = None

    def __init__(self, vector_store: Chroma):
        super().__init__()
        self.vector_store = vector_store

    def _run(self, query: str) -> list:
        try:
            docs = self.vector_store.similarity_search(query, k=10)
            context = "\n\n".join([doc.page_content for doc in docs])
            analysis_prompt = f"""
            Analyze the following ESG document content to obtain potential evidence of greenwashing using the following thought. There may be multiple pieces of potential evidence in content. Please identify all potential evidence as much as possible.:

            Content: {context}

            Thought: {query}

            For each potential evidence, provide:
            - Quotation of the corresponding content in the original text
            - Specific explanations for potential greenwashing
            - Indicate whether further verification using external data is required. If verification is required, describe the specific verification method, including what data is needed.
            - A greenwashing likelihood score (0-10, where 0 means no likelihood and 10 means very high likelihood)

            Please format your response as a JSON list, where each element is a JSON object representing a potential greenwashing evidence. Each evidence object should contain the following key-value pairs:
            * "quotation" (string): A quote of the corresponding suspicious content from the original text.
            * "explanation" (string): A detailed explanation of why this content represents potential greenwashing.
            * "greenwashing_likelihood_score" (integer): An integer score from 0 to 10, indicating the likelihood of this being greenwashing.
            * "verification_required" (boolean): Indicates whether further verification using external data is required (true/false).
            * "verification_method" (string): If verification is required, describe the specific verification method and steps.
            * "data_needed" (string): If verification is required, specify what external data is needed.
            """

            response = llm.invoke([HumanMessage(content=analysis_prompt)])
            raw_llm_content = response.content

            # Remove potential Markdown code block wrappers
            cleaned_llm_content = re.sub(r'```json\n(.*)```', r'\1', raw_llm_content, flags=re.DOTALL)
            cleaned_llm_content = cleaned_llm_content.replace('```json', '').replace('```', '').strip()
            try:
                parsed_json_response = json.loads(cleaned_llm_content)

                if isinstance(parsed_json_response, list):
                    return parsed_json_response
                else:
                    return [
                        {
                            "quotation": "",
                            "explanation": f"Error: LLM returned JSON but not a list. Content: {response.content}",
                            "verification_required": False,
                            "verification_method": "",
                            "data_needed": ""
                        }
                    ]

            except json.JSONDecodeError as json_e:
                return [
                    {
                        "quotation": "",
                        "explanation": f"Error: LLM did not return valid JSON. Original content: {response.content[:500]}... Error: {str(json_e)}",
                        "verification_required": False,
                        "verification_method": "",
                        "data_needed": ""
                    }
                ]

        except Exception as e:
            return [
                {
                    "quotation": "",
                    "explanation": f"An unexpected error occurred during document analysis: {str(e)}",
                    "verification_required": False,
                    "verification_method": "",
                    "data_needed": ""
                }
            ]



class NewsValidationTool(BaseTool):
    name: str = "news_validation"
    description: str = "Validates ESG claims against recent news articles from credible sources"
    company_name: str = ""

    def __init__(self, company_name: str):
        super().__init__()
        self.company_name = company_name

    def _run(self, claims: str) -> str:
        try:
            # 👇 Modification: make the search function return content + titles
            news_content, used_titles = search_and_filter_news(self.company_name, max_articles=10)

            if not news_content:
                return "No relevant news articles found for this company"

            # Print the news titles used
            print("[ Used News Articles]")
            for idx, title in enumerate(used_titles, start=1):
                print(f"{idx}. {title}")

            news_text = "\n\n".join(news_content)

            validation_prompt = f"""
            You are an expert ESG validation analyst. 

            Your task is to assess how well each ESG claim is reflected in the following news articles.
            
            You need to analyze each claim as follows.

            ---

            Instructions:
            - If the news_text provided directly proves that the statement is true, thereby refuting or partially refuting the greenwashing allegation, mark it as “Refuted”.
            - If the news_text provided directly refutes the statement, thereby confirming or partially confirming the greenwashing allegation, mark it as “Supported”.
            - If the provided news_text relates to relevant indicators or topics but is insufficient to directly verify or refute the greenwashing allegations in the quote, please mark it as “Mentioned.”
            - If the provided news_text is unrelated to the quote and cannot be evaluated in any way, please mark it as “Not Mentioned.”

            ---

            Claims:
            {claims}

            News Articles:
            {news_text}

            For each claim, respond with:
            1. **Status**: Supported / Contradicted / Indicated / Not mentioned  
            2. **Reasoning**: Explain why you chose this status  
            3. **news_quotation**: Include any relevant quotation from news_text if applicable  
            """

            response = llm.invoke([HumanMessage(content=validation_prompt)])
            return response.content

        except Exception as e:
            return f"Error in news validation: {str(e)}"



class ESGMetricsCalculatorTool(BaseTool):
    name: str = "esg_metrics_calculator"
    description: str = "Identify types of greenwashing and calculate a comprehensive greenwashing score"

    def _run(self, analysis_evidence: str) -> dict:
        """Calculate ESG metrics from analysis and return a parsed dict"""
        try:
            metrics_prompt = f"""
            Based on the following Greenwashing Evidence and the result of validation, comprehensively analyze the types of greenwashing present in this report and assign each type of greenwashing a probability score indicating the likelihood of its presence. The higher the score, the greater the likelihood of that type of greenwashing being present. The score range is 0–10.
            At the same time, calculate an overall greenwashing score (0–10).

            Greenwashing Evidence: {analysis_evidence}

            Five types of greenwashing:
            1. Vague or unsubstantiated claims
            2. Lack of specific metrics or targets
            3. Misleading terminology
            4. Cherry-picked data
            5. Absence of third-party verification

            Format the output strictly as JSON:
            {{
                "Vague or unsubstantiated claims": {{"score": 0}},
                "Lack of specific metrics or targets": {{"score": 0}},
                "Misleading terminology": {{"score": 0}},
                "Cherry-picked data": {{"score": 0}},
                "Absence of third-party verification": {{"score": 0}},
                "overall_greenwashing_score": {{"score": 0}}
            }}
            """
            response = llm.invoke([HumanMessage(content=metrics_prompt)])
            raw = (response.content or "").strip()

            # Remove ```json/``` fence
            clean = raw.replace("```json", "").replace("```", "").strip()

            # Parse JSON; if it fails, return a zero-score skeleton to avoid frontend crash
            import json
            try:
                data = json.loads(clean)
                if not isinstance(data, dict):
                    raise ValueError("metrics JSON is not a dict")
            except Exception:
                data = {
                    "Vague or unsubstantiated claims": {"score": 0},
                    "Lack of specific metrics or targets": {"score": 0},
                    "Misleading terminology": {"score": 0},
                    "Cherry-picked data": {"score": 0},
                    "Absence of third-party verification": {"score": 0},
                    "overall_greenwashing_score": {"score": 0},
                    "_raw_failed_to_parse": raw[:500]
                }

            return data

        except Exception as e:
            return {
                "Vague or unsubstantiated claims": {"score": 0},
                "Lack of specific metrics or targets": {"score": 0},
                "Misleading terminology": {"score": 0},
                "Cherry-picked data": {"score": 0},
                "Absence of third-party verification": {"score": 0},
                "overall_greenwashing_score": {"score": 0},
                "_error": f"Error calculating metrics: {str(e)}"
            }


