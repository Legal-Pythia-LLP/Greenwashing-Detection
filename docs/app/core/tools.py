from langchain.tools import BaseTool
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain.schema import HumanMessage
from typing import Any, Optional, Dict, List
from app.core.llm import llm
from webscraper import bbc_search, cnn_search
import json
import requests
from app.config import WIKIRATE_API_KEY

class WikirateClient:
    """Wikirate API客户端，用于获取和验证ESG数据"""

    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://wikirate.org"
        self.api_key = api_key
        self.session = requests.Session()

        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'ESG-Analysis-System/1.0',
            'Accept': 'application/json'
        })

        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })

    def search_company(self, company_name: str) -> Dict[str, Any]:
        """搜索公司信息"""
        try:
            # 清理公司名称，移除特殊字符
            clean_name = company_name.replace(" ", "_").replace(".", "").replace(",", "")

            # 尝试直接访问公司页面
            url = f"{self.base_url}/{clean_name}.json"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()

            # 如果直接访问失败，尝试搜索
            search_url = f"{self.base_url}/search.json"
            params = {
                'q': company_name,
                'type': 'Company'
            }

            response = self.session.get(search_url, params=params, timeout=10)
            if response.status_code == 200:
                search_results = response.json()
                if search_results.get('items'):
                    return search_results['items'][0]

            return {}

        except Exception as e:
            print(f"Error searching company {company_name}: {e}")
            return {}

    def get_company_metrics(self, company_name: str, metrics: List[str] = None) -> Dict[str, Any]:
        """获取公司的ESG指标数据"""
        try:
            results = {}
            company_data = self.search_company(company_name)

            if not company_data:
                return {"error": "Company not found"}

            # 获取默认ESG指标如果没有指定
            if not metrics:
                metrics = [
                    "CDP+Scope_1_Emissions",
                    "CDP+Scope_2_Emissions",
                    "CDP+Scope_3_Emissions",
                    "CDP+Total_Scope_1_and_2_Emissions",
                    "GRI+Water_Consumption",
                    "GRI+Energy_Consumption",
                    "SASB+Greenhouse_Gas_Emissions",
                    "Walk_Free+Modern_Slavery_Statement"
                ]

            for metric in metrics:
                try:
                    # 构建答案查询URL (METRIC+COMPANY+YEAR格式)
                    # 获取最近几年的数据
                    for year in [2023, 2022, 2021]:
                        metric_url = f"{self.base_url}/{metric}+{company_name}+{year}.json"
                        response = self.session.get(metric_url, timeout=10)

                        if response.status_code == 200:
                            metric_data = response.json()
                            if metric not in results:
                                results[metric] = {}
                            results[metric][str(year)] = metric_data
                            break  # 找到数据就跳出年份循环

                except Exception as e:
                    print(f"Error fetching metric {metric}: {e}")
                    continue

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