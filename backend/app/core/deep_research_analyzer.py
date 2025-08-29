"""
Unified ESG Analyzer for Deep Research
Enhanced analyzer with source tracking and explainable AI
"""

import os
import asyncio
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv

from .deep_research_engine import DeepSearchEngine, SearchResult
from app.models.city_rankings import SustainabilityData
from .deep_research_prompt_manager import prompt_manager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedESGAnalyzer:
    """Enhanced analyzer with source tracking and explainable AI"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key required. Set GOOGLE_API_KEY environment variable.")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.api_key,
            temperature=0.1
        )
        
        self.deep_search = DeepSearchEngine(self.api_key)
    
    async def search_esg_data_with_sources(self, company_name: str, location: str = None) -> Tuple[List[str], List[SearchResult]]:
        """Search for ESG data and return both content and sources"""
        queries = []

        # Lokasyon varsa daha spesifik sorgular
        if location:
            queries.extend([
                f'"{company_name}" "{location}" ESG sustainability report',
                f'"{company_name}" headquarters "{location}" environmental social governance',
                f'"{company_name}" based in "{location}" sustainability initiatives',
                f'"{company_name}" "{location}" office carbon emissions climate'
            ])
    
        # Genel sorgular
        queries.extend([
            f'"{company_name}" ESG report sustainability score rating 2023 2024',
            f'"{company_name}" carbon emissions environmental impact',
            f'"{company_name}" employee diversity social responsibility',
            f'"{company_name}" corporate governance transparency'
        ])
        
        all_content = []
        all_sources = []
        
        for query in queries:
            try:
                result = await self.deep_search.search_with_sources(query)
                if result.content and len(result.content.strip()) > 200:
                    all_content.append(result.content)
                    all_sources.append(result)
                
                # Only sleep if we made a live request
                if query not in self.deep_search.cache:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Search error for {query[:50]}...: {str(e)}")
        
        return all_content, all_sources
    
    async def analyze_with_explainable_ai(self, company_name: str, content: List[str], sources: List[SearchResult], location: str = None, language: str = "en") -> SustainabilityData:
        """Enhanced analysis with detailed explainable AI and source attribution"""
        
        # Prepare source information for the prompt
        source_info = "\n\n".join([
            f"Source {i+1} (Query: {src.query}):\n"
            f"URLs found: {', '.join(src.urls[:3]) if src.urls else 'No URLs'}\n"
            f"Key snippets: {' | '.join(src.snippets[:2]) if src.snippets else 'No snippets'}"
            for i, src in enumerate(sources[:5])
        ])
        
        system_prompt = prompt_manager.get_esg_analysis_prompt(language)
        
        # Language mapping for human prompt
        language_instructions = {
            "en": "Respond entirely in English.",
            "de": "Antworten Sie ausschließlich auf Deutsch.",
            "it": "Risponda interamente in italiano."
        }
        
        language_instruction = language_instructions.get(language, language_instructions["en"])
        
        combined_content = "\n\n".join(content) if content else "No data available"
        human_prompt = f"""{language_instruction}

Company: {company_name}
Location: {location if location else 'Not specified'}

SOURCE INFORMATION:
{source_info}

CONTENT TO ANALYZE:
{combined_content[:20000]}

Remember: Explain EXACTLY why each score is what it is, with specific evidence. ALL content must be in the requested language."""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            response = await self.llm.ainvoke(messages)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON in response")
                
        except Exception as e:
            logger.error(f"Analysis error for {company_name}: {str(e)}")
            analysis = self._get_default_analysis(company_name)
        
        # Create SustainabilityData object with sources
        return SustainabilityData(
            company_name=company_name,
            sustainability_score=analysis.get("sustainability_score", 0),
            environmental_score=analysis.get("environmental_score", 0),
            social_score=analysis.get("social_score", 0),
            governance_score=analysis.get("governance_score", 0),
            esg_rating=analysis.get("esg_rating", "N/A"),
            location=analysis.get("location", location),
            industry=analysis.get("industry", "Unknown"),
            key_metrics=analysis,
            summary=analysis.get("summary", ""),
            key_strengths=analysis.get("key_strengths", []),
            key_risks=analysis.get("key_risks", []),
            recommendations=analysis.get("recommendations", []),
            data_quality=analysis.get("data_quality", {}),
            scoring_explanations=analysis.get("scoring_explanations", {}),
            search_results=sources,
            raw_sources=[src.query for src in sources]
        )
    
    def _get_default_analysis(self, company_name: str) -> Dict:
        """Return default analysis structure when analysis fails"""
        return {
            "sustainability_score": 0,
            "environmental_score": 0,
            "social_score": 0,
            "governance_score": 0,
            "esg_rating": "N/A",
            "summary": f"Unable to analyze {company_name}. Insufficient data available.",
            "key_strengths": [],
            "key_risks": ["Data unavailable"],
            "recommendations": ["Improve ESG reporting and transparency"],
            "scoring_explanations": {
                "overall_reasoning": "No data available for scoring",
                "environmental_explanation": {
                    "score_rationale": "No environmental data found",
                    "confidence_level": "Low"
                },
                "social_explanation": {
                    "score_rationale": "No social data found",
                    "confidence_level": "Low"
                },
                "governance_explanation": {
                    "score_rationale": "No governance data found",
                    "confidence_level": "Low"
                }
            },
            "data_quality": {
                "information_completeness": "Insufficient",
                "source_reliability": "Low",
                "data_freshness": "Unknown",
                "confidence_score": 0
            }
        }
