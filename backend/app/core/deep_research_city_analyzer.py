"""
City-Based Company Analyzer for Deep Research
Enhanced city analyzer with two-step process
"""

import os
import asyncio
import json
import re
from typing import List, Dict, Any, Optional, Tuple
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv

from .deep_research_engine import DeepSearchEngine, SearchResult
from app.models.city_rankings import SustainabilityData
from .deep_research_analyzer import UnifiedESGAnalyzer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CityCompanyAnalyzer:
    """Enhanced city analyzer with two-step process"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.api_key,
            temperature=0.3
        )
        self.deep_search = DeepSearchEngine(self.api_key)
        self.esg_analyzer = UnifiedESGAnalyzer(self.api_key)
        self.discovered_companies = []  # Store for two-step process
    
    async def find_companies_in_city_fast(self, city: str, top_n: int = 10) -> Tuple[List[Dict], str]:
        """FAST company discovery - focus on well-known companies"""
        
        # Prioritize well-known companies with simpler, faster queries
        queries = [
            f'largest companies headquartered in "{city}"',
            f'Fortune 500 companies in "{city}"',
            f'major corporations "{city}" headquarters',
            f'biggest employers in "{city}"'
        ]
        
        # Parallel search for speed
        search_tasks = []
        for query in queries:
            search_tasks.append(self.deep_search.search_with_sources(query))
        
        # Execute all searches in parallel
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        all_content = []
        for result in search_results:
            if isinstance(result, SearchResult) and result.content:
                all_content.append(result.content)
        
        # Faster, focused extraction
        system_prompt = f"""Extract WELL-KNOWN companies from {city}.
        
        RULES:
        1. Focus on LARGE, ESTABLISHED companies first
        2. Must be headquartered or have major operations IN {city}
        3. Prioritize companies with public ESG reports
        4. Include company size/importance indicator
        
        Return JSON:
        {{
            "companies": [
                {{
                    "name": "Company Name",
                    "size": "Large/Medium/Small",
                    "industry": "Industry",
                    "importance": "Major employer/Regional leader/Local business",
                    "has_esg": "Likely/Unknown"
                }}
            ]
        }}
        
        Return up to {top_n} companies, prioritizing larger companies."""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content="\n".join(all_content)[:10000])  # Reduced content for speed
            ]
            response = await self.llm.ainvoke(messages)
            
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                companies_data = data.get("companies", [])[:top_n]
                
                # Create discovery HTML
                discovery_html = f"""
                <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 20px; border-radius: 15px; margin: 20px 0;">
                    <h3 style="color: #1565c0; margin: 0 0 15px 0;">🔍 Companies Found in {city}</h3>
                    <p style="color: #424242; margin: 10px 0;">
                        Found <strong>{len(companies_data)}</strong> companies in {city}
                    </p>
                    
                    <div style="background: white; padding: 15px; border-radius: 10px; margin: 15px 0;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #e3f2fd;">
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #1976d2;">#</th>
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #1976d2;">Company</th>
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #1976d2;">Industry</th>
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #1976d2;">Size</th>
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #1976d2;">ESG Data</th>
                                </tr>
                            </thead>
                            <tbody>
                """
                
                for i, comp in enumerate(companies_data, 1):
                    size_color = {"Large": "#4caf50", "Medium": "#ff9800", "Small": "#9e9e9e"}.get(comp.get("size", "Unknown"), "#9e9e9e")
                    esg_color = {"Likely": "#4caf50", "Unknown": "#ff9800"}.get(comp.get("has_esg", "Unknown"), "#ff9800")
                    
                    discovery_html += f"""
                        <tr style="border-bottom: 1px solid #e0e0e0;">
                            <td style="padding: 10px;">{i}</td>
                            <td style="padding: 10px; font-weight: bold; color: #1976d2;">{comp.get("name", "Unknown")}</td>
                            <td style="padding: 10px;">{comp.get("industry", "Unknown")}</td>
                            <td style="padding: 10px;">
                                <span style="background: {size_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">
                                    {comp.get("size", "Unknown")}
                                </span>
                            </td>
                            <td style="padding: 10px;">
                                <span style="background: {esg_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">
                                    {comp.get("has_esg", "Unknown")}
                                </span>
                            </td>
                        </tr>
                    """
                
                discovery_html += """
                            </tbody>
                        </table>
                    </div>
                    
                    <div style="background: #fff3e0; padding: 15px; border-radius: 10px; margin: 15px 0;">
                        <p style="color: #e65100; margin: 0; font-weight: bold;">
                            ⏳ Ready to analyze these companies...
                        </p>
                        <p style="color: #f57c00; margin: 5px 0; font-size: 14px;">
                            Analysis will begin shortly. Larger companies typically have more ESG data available.
                        </p>
                    </div>
                </div>
                """
                
                # Store for later use
                self.discovered_companies = companies_data
                
                return companies_data, discovery_html
            else:
                return [], f"<div style='color: red;'>No companies found in {city}</div>"
                
        except Exception as e:
            logger.error(f"Error extracting companies: {str(e)}")
            return [], f"<div style='color: red;'>Error: {str(e)}</div>"
    
    async def analyze_discovered_companies(self, companies_data: List[Dict], city: str, progress_callback=None) -> List[SustainabilityData]:
        """Analyze previously discovered companies - FASTER with parallel processing"""
        
        results = []
        total = len(companies_data)
        
        # Process in batches for speed
        batch_size = 3  # Process 3 companies at a time
        
        for i in range(0, total, batch_size):
            batch = companies_data[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            if progress_callback:
                progress_callback((batch_num / total_batches), f"Analyzing batch {batch_num}/{total_batches}...")
            
            # Parallel analysis for batch
            batch_tasks = []
            for comp in batch:
                company_name = comp.get("name", "Unknown")
                batch_tasks.append(self.analyze_single_company_fast(company_name, city))
            
            # Execute batch in parallel
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, SustainabilityData):
                    results.append(result)
                else:
                    logger.error(f"Error in batch analysis: {result}")
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        # Sort by sustainability score
        results.sort(key=lambda x: x.sustainability_score, reverse=True)
        return results
    
    async def analyze_single_company_fast(self, company_name: str, city: str) -> SustainabilityData:
        """Fast single company analysis with reduced searches"""
        try:
            # Simplified search - just 2 queries instead of 6
            queries = [
                f'"{company_name}" ESG sustainability report score',
                f'"{company_name}" environmental social governance {city}'
            ]
            
            search_tasks = []
            for query in queries:
                search_tasks.append(self.deep_search.search_with_sources(query))
            
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            content = []
            sources = []
            for result in search_results:
                if isinstance(result, SearchResult) and result.content:
                    content.append(result.content)
                    sources.append(result)
            
            # Faster analysis with shorter content
            company_data = await self.esg_analyzer.analyze_with_explainable_ai(
                company_name, content[:2], sources[:2], location=city  # Limit content for speed
            )
            
            return company_data
            
        except Exception as e:
            logger.error(f"Error analyzing {company_name}: {str(e)}")
            return SustainabilityData(
                company_name=company_name,
                sustainability_score=0,
                location=city,
                summary=f"Analysis failed: {str(e)}"
            )
