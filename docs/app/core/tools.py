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

class WikirateClient:
    """Wikirate API客户端，用于获取和验证ESG数据"""

    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://wikirate.org"
        self.api_key = api_key
        self.session = cloudscraper.create_scraper(  # ✅ 替代 requests
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
            limit = 5
            offset = 0
            max_total = 10  # 最多获取200条记录
            
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
            
            # 获取所有指标的ESG主题
            for answer in all_answers:
                metric_name = answer.metric
                if metric_name in metric_cache:
                    topics = metric_cache[metric_name]
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
                        metric_cache[metric_name] = topics
                    except Exception as e:
                        print(f"获取指标 {metric_name} 主题失败: {e}")
                        topics = []
                        metric_cache[metric_name] = topics
                
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
                        "comments": getattr(answer, 'comments', None),
                        "source": getattr(answer, 'source', None),
                        "topics": metric_cache.get(answer.metric, [])
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

            # 搜索公司
            company_data = self.wikirate_client.search_company(self.company_name)

            if company_data:
                validation_results["company_found"] = True

                # 获取公司的ESG指标
                # lqw
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

    def _run(self, query: str) -> str:
        try:
            docs = self.vector_store.similarity_search(query, k=10)
            context = "\n\n".join([doc.page_content for doc in docs])
            analysis_prompt = f"""
            Analyze the following ESG document content for greenwashing indicators:

            Content: {context}

            Query: {query}

            Look for:
            1. Vague or unsubstantiated claims
            2. Lack of specific metrics or targets
            3. Misleading terminology
            4. Cherry-picked data
            5. Absence of third-party verification

            Provide specific evidence and scoring rationale.
            """
            response = llm.invoke([HumanMessage(content=analysis_prompt)])
            return response.content
        except Exception as e:
            return f"Error in document analysis: {str(e)}"

class NewsValidationTool(BaseTool):
    name: str = "news_validation"
    description: str = "Validates ESG claims against recent news articles from credible sources"
    company_name: str = ""

    def __init__(self, company_name: str):
        super().__init__()
        self.company_name = company_name

    def _run(self, claims: str) -> str:
        try:
            bbc_articles = bbc_search(self.company_name)
            cnn_articles = cnn_search(self.company_name)
            news_content = []
            if bbc_articles:
                for title, file_path in bbc_articles.items():
                    try:
                        loader = UnstructuredHTMLLoader(file_path)
                        docs = loader.load()
                        news_content.extend([doc.page_content for doc in docs])
                    except Exception as e:
                        print(f"Error loading BBC article {title}: {e}")
            if cnn_articles:
                for title, file_path in cnn_articles.items():
                    try:
                        loader = UnstructuredHTMLLoader(file_path)
                        docs = loader.load()
                        news_content.extend([doc.page_content for doc in docs])
                    except Exception as e:
                        print(f"Error loading CNN article {title}: {e}")
            if not news_content:
                return "No recent news articles found for validation"
            news_text = "\n\n".join(news_content[:5])
            validation_prompt = f"""
            Validate the following ESG claims against recent news articles:

            Claims to validate: {claims}

            News articles: {news_text}

            Determine if the claims are:
            1. Supported by news evidence
            2. Contradicted by news evidence
            3. Not mentioned in news sources

            Provide specific quotes and sources where relevant.
            """
            response = llm.invoke([HumanMessage(content=validation_prompt)])
            return response.content
        except Exception as e:
            return f"Error in news validation: {str(e)}"

class ESGMetricsCalculatorTool(BaseTool):
    name: str = "esg_metrics_calculator"
    description: str = "Calculates quantitative greenwashing metrics for visualization"

    def _run(self, analysis_text: str) -> str:
        try:
            metrics_prompt = f"""
            Based on the following ESG analysis, calculate specific greenwashing metrics:

            Analysis: {analysis_text}

            Calculate scores (0-100) for each metric:
            1. Vague Language Score
            2. Evidence Quality Score
            3. Transparency Score
            4. Measurability Score
            5. Third-party Verification Score

            Format as JSON:
            {{
                "vague_language": {{
                    "score": 0-100,
                    "evidence": "specific examples",
                    "contains_percentages": true/false
                }},
                "evidence_quality": {{
                    "score": 0-100,
                    "evidence": "specific examples",
                    "contains_percentages": true/false
                }},
                "transparency": {{
                    "score": 0-100,
                    "evidence": "specific examples",
                    "contains_percentages": true/false
                }},
                "measurability": {{
                    "score": 0-100,
                    "evidence": "specific examples",
                    "contains_percentages": true/false
                }},
                "third_party_verification": {{
                    "score": 0-100,
                    "evidence": "specific examples",
                    "contains_percentages": true/false
                }}
            }}

            Also provide an overall greenwashing score (0-10).
            """
            response = llm.invoke([HumanMessage(content=metrics_prompt)])
            return response.content
        except Exception as e:
            return f"Error calculating metrics: {str(e)}" 