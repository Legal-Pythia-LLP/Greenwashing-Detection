from langchain.tools import BaseTool
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain.schema import HumanMessage
from typing import Any
from app.core.llm import llm
from webscraper import bbc_search, cnn_search

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