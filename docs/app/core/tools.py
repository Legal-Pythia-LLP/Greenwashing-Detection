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
from app.core.utils import search_and_filter_news  # 按你放的位置

# get_company_name
from wikirate4py import API
from pprint import pprint
import pandas as pd
from name_matching.name_matcher import NameMatcher
import time
import csv
import re
import multiprocessing

# 名字模糊比對
# 自訂 normalization 方法（模仿 NameMatcher transform=True）
def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s]', '', name)  # 移除標點符號
    name = re.sub(r'\s+', ' ', name)  # 移除多餘空白
    return name.strip()

def get_isin_count(company):
    """從公司物件中讀取 ISIN 數量"""
    try:
        isin = getattr(company, "isin", None)
        isin_list = isin if isinstance(isin, list) else []
        return len(isin_list)
    except Exception as e:
        print(f"無法處理公司 {company}: {e}")
        return 0


class WikirateClient:
    """Wikirate API客户端，用于获取和验证ESG数据"""

    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://wikirate.org"
        self.api_key = api_key
        self.session = cloudscraper.create_scraper(  # 替代 requests
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )

        # Cloudscraper 預設會附帶真實瀏覽器 UA
        self.session.headers.update({
            'Accept': 'application/json'
        })

        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })

    def search_company(self, company_name: str) -> Dict[str, Any]:
        """搜尋公司資訊，支援精準名稱與模糊搜尋"""
        try:
            original_name = company_name.strip()
            clean_name = original_name.strip()
            print(f"[Wikirate] 嘗試精準搜尋：--{clean_name}--")
            direct_url = f"{self.base_url}/{clean_name}.json"

            # print(f"[Wikirate] 嘗試精準搜尋：{direct_url}")
            response = self.session.get(direct_url, timeout=10)

            print(f"[DEBUG] Status Code: {response.status_code}")
            print(f"[DEBUG] Response preview:\n{response.text[:300]}")

            if response.status_code == 200:
                data = response.json()
                # 安全地处理所有字段，避免None.get()报错
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

            # 若精準搜尋失敗，改用 search API 做模糊搜尋
            # print(f"[Wikirate] 精準搜尋失敗，改用模糊搜尋: '{original_name}'")
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
                        # print(f"[Wikirate] 模糊搜尋找到公司: {item.get('name')}")
                        return item

            # print(f"[Wikirate] 公司 '{company_name}' 未在 Wikirate 找到")
            return {}

        except Exception as e:
            # print(f"[Wikirate] 搜尋時發生錯誤: {e}")
            return {}

    # 主函數：根據輸入名稱模糊比對，並根據 ISIN 數量選擇最佳匹配
    def find_best_matching_company(self, input_name: str) -> str:
        # self.parallel_fetch(num_workers=6)

        # 加载公司数据
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
            print(f"找不到公司数据文件: {csv_path}")
            return None

        keyword = input_name.lower()
        filtered_companies = [c for c in wikirate_companies if keyword in c['name'].lower()]
        if not filtered_companies:
            print("找不到任何名稱包含關鍵字的公司")
            return None

        # 印出所有符合條件的公司名稱
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

        # 印出所有匹配的名稱與分數
        print("所有匹配結果：")
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
                    print(f"{i + 1}. {match_name}  分數: {score:.2f}  ISIN數量: {isin_count}")
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

    def get_company_metrics(self, company_name: str) -> Dict[str, Any]:
        """获取公司的ESG指标数据，使用wikirate4py API"""
        try:
            from wikirate4py import API

            # 初始化wikirate4py API
            api = API(self.api_key)

            # 获取公司信息
            company = api.get_company(company_name)
            if not company:
                return {"error": f"Company '{company_name}' not found"}

            # 分页获取所有答案
            all_answers = []
            limit = 10
            offset = 0
            max_total = 20  # 最多获取200条记录

            while len(all_answers) < max_total:
                batch = api.get_answers(company=company.name, limit=min(limit, max_total - len(all_answers)), offset=offset)
                if not batch:
                    break
                all_answers.extend(batch)
                if len(batch) < limit or len(all_answers) >= max_total:
                    break
                offset += limit

            # 筛选ESG相关指标
            esg_topics = ["environment", "social", "governance"]
            esg_metrics = set()
            metric_cache = {}

            # 获取所有指标的ESG主题和单位信息
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

                        # 获取单位信息
                        unit = getattr(metric_obj, 'unit', None)

                        metric_cache[metric_name] = {
                            'topics': topics,
                            'unit': unit
                        }
                    except Exception as e:
                        print(f"获取指标 {metric_name} 信息失败: {e}")
                        topics = []
                        unit = None
                        metric_cache[metric_name] = {
                            'topics': topics,
                            'unit': unit
                        }

                if any(topic in topics for topic in esg_topics):
                    esg_metrics.add(metric_name)

            # 构建返回结果
            results = {
                "company_name": company_name,
                "total_answers": len(all_answers),
                "esg_metrics_count": len(esg_metrics),
                "esg_data": []
            }

            # 提取ESG相关指标的数据
            for answer in all_answers:
                if answer.metric in esg_metrics:
                    record = {
                        "metric_name": answer.metric,
                        "year": getattr(answer, 'year', None),
                        "value": getattr(answer, 'value', None),
                        "unit": metric_cache.get(answer.metric, {}).get('unit'),
                        # "comments": getattr(answer, 'comments', None),
                        # "source": getattr(answer, 'source', None),
                        # "topics": metric_cache.get(answer.metric, {}).get('topics', [])
                    }
                    results["esg_data"].append(record)

            return results

        except Exception as e:
            print(f"Error getting company metrics: {e}")
            return {"error": str(e)}

    def get_metric_details(self, metric_name: str) -> Dict[str, Any]:
        """获取指标的详细信息和定义"""
        try:
            url = f"{self.base_url}/{metric_name}.json"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()

            return {}

        except Exception as e:
            print(f"Error getting metric details for {metric_name}: {e}")
            return {}


# Wikirate验证工具
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
        """验证提取的ESG指标与Wikirate数据库的一致性"""
        try:
            validation_results = {
                "company_found": False,
                "metrics_verified": {},
                "discrepancies": [],
                "verification_score": 0.0
            }

            # 根據輸入名稱模糊比對，並根據 ISIN 數量選擇最佳匹配
            self.company_name = self.wikirate_client.find_best_matching_company(self.company_name)

            if self.company_name:
                validation_results["company_found"] = True

                # 获取公司的ESG指标
                metrics_data = self.wikirate_client.get_company_metrics(self.company_name)

                if "error" not in metrics_data:
                    validation_results["metrics_verified"] = metrics_data

                    # 分析提取的指标与Wikirate数据的对比
                    analysis_prompt = f"""
                    Compare the extracted ESG metrics from the document with Wikirate database data:

                    Extracted Metrics from Document: {extracted_metrics}

                    Wikirate Database Data: {json.dumps(metrics_data, indent=2)}

                    Analyze:
                    1. Which metrics match between the document and Wikirate database?
                    2. What discrepancies exist in values, methodologies, or reporting periods?
                    3. Are there missing metrics that should be reported?
                    4. How reliable are the document claims compared to verified Wikirate data?
                    5. Calculate a verification score (0-100) based on data consistency.

                    Provide specific examples of matches and discrepancies.
                    """

                    response = llm.invoke([HumanMessage(content=analysis_prompt)])

                    # 提取验证分数
                    verification_text = response.content

                    # 简单的分数提取逻辑（可以改进）
                    if "verification score" in verification_text.lower():
                        import re
                        score_match = re.search(r'(\d+)(?:/100|\%)', verification_text)
                        if score_match:
                            validation_results["verification_score"] = float(score_match.group(1))

                    return f"""
                    Wikirate Validation Results:

                    Company Found: {validation_results['company_found']}
                    Verification Score: {validation_results['verification_score']}

                    Detailed Analysis:
                    {verification_text}

                    Raw Wikirate Data Available: {len(metrics_data)} metrics found
                    """

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
            # return response.content
            raw_llm_content = response.content

            # 使用正则表达式移除潜在的Markdown代码块包装
            # 匹配开头```json\n 和 结尾的 ```（可能是\n```）
            cleaned_llm_content = re.sub(r'```json\n(.*)```', r'\1', raw_llm_content, flags=re.DOTALL)
            # 进一步清理可能只剩下 ```json 和 ``` 的情况
            cleaned_llm_content = cleaned_llm_content.replace('```json', '').replace('```', '').strip()
            try:
                # 尝试解析LLM返回的JSON字符串为Python列表对象
                parsed_json_response = json.loads(cleaned_llm_content)

                # 确保解析后的结果确实是一个列表
                if isinstance(parsed_json_response, list):
                    return parsed_json_response  # <-- 直接返回解析后的列表
                else:
                    # 如果LLM没有返回列表，而是其他JSON类型（比如单个对象），可以抛出错误或根据需要处理
                    return [
                        {
                            "quotation": "",
                            "explanation": f"Error: LLM returned JSON but not a list. Content: {response.content}",
                            "verification_required": False,
                            "verification_method": "",
                            "data_needed": ""
                        }
                    ]  # 返回一个包含错误信息的列表

            except json.JSONDecodeError as json_e:
                # 如果LLM没有返回有效的JSON，捕获错误
                return [
                    {
                        "quotation": "",
                        "explanation": f"Error: LLM did not return valid JSON. Original content: {response.content[:500]}... Error: {str(json_e)}",
                        "verification_required": False,
                        "verification_method": "",
                        "data_needed": ""
                    }
                ]  # 返回一个包含错误信息的列表

        except Exception as e:
            # 捕获其他任何异常
            return [
                {
                    "quotation": "",
                    "explanation": f"An unexpected error occurred during document analysis: {str(e)}",
                    "verification_required": False,
                    "verification_method": "",
                    "data_needed": ""
                }
            ]  # 返回一个包含错误信息的列表



class NewsValidationTool(BaseTool):
    name: str = "news_validation"
    description: str = "Validates ESG claims against recent news articles from credible sources"
    company_name: str = ""

    def __init__(self, company_name: str):
        super().__init__()
        self.company_name = company_name

    def _run(self, claims: str) -> str:
        try:
            # 👇 修改：让搜索函数返回内容 + 标题
            news_content, used_titles = search_and_filter_news(self.company_name, max_articles=10)

            if not news_content:
                return "No relevant news articles found for this company"

            # ✅ 打印使用到的新闻标题
            print("[📰 使用的新闻文章]")
            for idx, title in enumerate(used_titles, start=1):
                print(f"{idx}. {title}")

            news_text = "\n\n".join(news_content)

            validation_prompt = f"""
            You are an expert ESG validation analyst.

            Your task is to assess how well each ESG claim is reflected in the following news articles.

            ---

            Instructions:
            - If the article directly supports or contradicts a claim, label it as **Supported** or **Contradicted**
            - If the article covers related topics (e.g., fossil fuel protests, ESG controversies, financing debates, policy discussions), even without explicitly restating the claim, label it as **Indicated**
            - If there's truly no connection, mark it as **Not mentioned**

            ---

            Definitions:
            - **Supported**: Clearly confirms the claim
            - **Contradicted**: Clearly denies or disproves the claim
            - **Indicated**: Topic is related, mentioned, or thematically aligned
            - **Not mentioned**: No relevant or related discussion

            ---

            Claims:
            {claims}

            News Articles:
            {news_text}

            For each claim, respond with:
            1. **Status**: Supported / Contradicted / Indicated / Not mentioned  
            2. **Reasoning**: Explain why you chose this status  
            3. **Quote(s)**: Include any relevant quotes if applicable  
            """



            response = llm.invoke([HumanMessage(content=validation_prompt)])
            return response.content

        except Exception as e:
            return f"Error in news validation: {str(e)}"



class ESGMetricsCalculatorTool(BaseTool):
    name: str = "esg_metrics_calculator"
    description: str = "Identify types of greenwashing and calculate a comprehensive greenwashing score"

    def _run(self, analysis_evidence: str) -> str:
        """Calculate ESG metrics from analysis"""
        try:
            metrics_prompt = f"""
            Based on the following Greenwashing Evidence, Analyze the types of greenwashing present in this report and assign each type of greenwashing a probability score indicating the likelihood of its presence. The higher the score, the greater the likelihood of that type of greenwashing being present. The score range is 0–10. :
            At the same time, a comprehensive greenwashing score is calculated. The score range is also 0-10, and the higher the score, the greater the likelihood of greenwashing.

            Greenwashing Evidence: {analysis_evidence}

            Five types of greenwashing:
            1. Vague or unsubstantiated claims
            2. Lack of specific metrics or targets
            3. Misleading terminology
            4. Cherry-picked data
            5. Absence of third-party verification


            Format the output strictly as JSON:
            {{
                "Vague or unsubstantiated claims": {{
                    "score": 0-10,
                }},
                "Lack of specific metrics or targets": {{
                    "score": 0-10,
                }},
                "Misleading terminology": {{
                    "score": 0-10,
                }},
                "Cherry-picked data": {{
                    "score": 0-10, 
                }},
                "Absence of third-party verification": {{
                    "score": 0-10,
                }}
                ""overall_greenwashing_score"": {{
                    "score": 0-10,
                }}
            }}


            """

            response = llm.invoke([HumanMessage(content=metrics_prompt)])
            return response.content

        except Exception as e:
            return f"Error calculating metrics: {str(e)}"
