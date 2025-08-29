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
    
    async def analyze_with_explainable_ai(self, company_name: str, content: List[str], sources: List[SearchResult], location: str = None) -> SustainabilityData:
        """Enhanced analysis with detailed explainable AI and source attribution"""
        
        # Prepare source information for the prompt
        source_info = "\n\n".join([
            f"Source {i+1} (Query: {src.query}):\n"
            f"URLs found: {', '.join(src.urls[:3]) if src.urls else 'No URLs'}\n"
            f"Key snippets: {' | '.join(src.snippets[:2]) if src.snippets else 'No snippets'}"
            for i, src in enumerate(sources[:5])
        ])
        
        system_prompt = """You are an expert ESG analyst providing transparent, explainable assessments with source attribution.
        
        CRITICAL: For EVERY score you assign, you MUST provide:
        1. The exact reasoning why you chose that specific number
        2. Which specific information from the sources influenced the score
        3. What information was missing that prevented a higher score
        4. Direct quotes from sources when available
        
        Analyze the content and provide a comprehensive JSON response with:
        {
            "sustainability_score": <0-100>,
            "environmental_score": <0-100>,
            "social_score": <0-100>,
            "governance_score": <0-100>,
            "esg_rating": "<A+/A/B+/B/C+/C/D>",
            "industry": "<detected industry>",
            "location": "<detected location or provided>",
            "key_strengths": ["strength1 with evidence", "strength2 with evidence"],
            "key_risks": ["risk1 with explanation", "risk2 with explanation"],
            "summary": "Comprehensive summary with specific data points",
            "recommendations": ["specific rec1", "specific rec2"],
            "sustainability_initiatives": ["initiative1 with details", "initiative2 with details"],
            "scoring_explanations": {
                "overall_reasoning": "Detailed explanation of why the overall score is X, not higher or lower",
                "environmental_explanation": {
                    "score_rationale": "Detailed explanation: I gave X/100 because [specific reasons]",
                    "scoring_breakdown": "Points awarded: +X for renewable energy, -Y for emissions, +Z for targets",
                    "positive_factors": ["factor1 (+X points): evidence", "factor2 (+Y points): evidence"],
                    "negative_factors": ["factor1 (-X points): evidence", "factor2 (-Y points): evidence"],
                    "evidence_found": ["specific data point 1", "specific data point 2"],
                    "source_quotes": ["exact quote 1 from sources", "exact quote 2 from sources"],
                    "missing_data": ["what data would improve score", "what wasn't found"],
                    "confidence_level": "High/Medium/Low - explanation why"
                },
                "social_explanation": {
                    "score_rationale": "Detailed explanation: I gave X/100 because [specific reasons]",
                    "scoring_breakdown": "Points awarded: +X for diversity, -Y for controversies, +Z for benefits",
                    "positive_factors": ["factor1 (+X points): evidence", "factor2 (+Y points): evidence"],
                    "negative_factors": ["factor1 (-X points): evidence", "factor2 (-Y points): evidence"],
                    "evidence_found": ["specific data point 1", "specific data point 2"],
                    "source_quotes": ["exact quote 1 from sources", "exact quote 2 from sources"],
                    "missing_data": ["what data would improve score", "what wasn't found"],
                    "confidence_level": "High/Medium/Low - explanation why"
                },
                "governance_explanation": {
                    "score_rationale": "Detailed explanation: I gave X/100 because [specific reasons]",
                    "scoring_breakdown": "Points awarded: +X for transparency, -Y for issues, +Z for policies",
                    "positive_factors": ["factor1 (+X points): evidence", "factor2 (+Y points): evidence"],
                    "negative_factors": ["factor1 (-X points): evidence", "factor2 (-Y points): evidence"],
                    "evidence_found": ["specific data point 1", "specific data point 2"],
                    "source_quotes": ["exact quote 1 from sources", "exact quote 2 from sources"],
                    "missing_data": ["what data would improve score", "what wasn't found"],
                    "confidence_level": "High/Medium/Low - explanation why"
                },
                "ranking_justification": "Why this company ranks where it does compared to industry peers"
            },
            "data_quality": {
                "information_completeness": "Comprehensive/Adequate/Limited/Insufficient",
                "source_reliability": "High/Medium/Low",
                "data_freshness": "Current (2024)/Recent (2023)/Outdated (pre-2023)",
                "sources_used": ["source1", "source2"],
                "missing_information": ["missing1", "missing2"],
                "confidence_score": <0-100>
            },
            "source_attribution": {
                "primary_sources": ["source1 with URL", "source2 with URL"],
                "data_points_source_mapping": {
                    "emissions_data": "source X",
                    "diversity_data": "source Y",
                    "governance_data": "source Z"
                }
            }
        }
        
        BE SPECIFIC AND TRANSPARENT IN YOUR SCORING!"""
        
        combined_content = "\n\n".join(content) if content else "No data available"
        human_prompt = f"""Company: {company_name}
Location: {location if location else 'Not specified'}

SOURCE INFORMATION:
{source_info}

CONTENT TO ANALYZE:
{combined_content[:20000]}

Remember: Explain EXACTLY why each score is what it is, with specific evidence."""
        
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
