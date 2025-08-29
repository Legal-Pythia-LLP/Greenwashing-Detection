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
from .deep_research_prompt_manager import prompt_manager

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
    
    def _get_ui_texts(self, language: str) -> Dict[str, str]:
        """Get UI text translations for the discovery HTML"""
        texts = {
            "en": {
                "found_title": "🔍 Companies Found in",
                "found_text": "Found",
                "companies_text": "companies in",
                "company": "Company",
                "industry": "Industry", 
                "size": "Size",
                "esg_data": "ESG Data",
                "ready_title": "⏳ Ready to analyze these companies...",
                "ready_text": "Analysis will begin shortly. Larger companies typically have more ESG data available."
            },
            "de": {
                "found_title": "🔍 Unternehmen gefunden in",
                "found_text": "Gefunden",
                "companies_text": "Unternehmen in",
                "company": "Unternehmen",
                "industry": "Branche",
                "size": "Größe", 
                "esg_data": "ESG-Daten",
                "ready_title": "⏳ Bereit zur Analyse dieser Unternehmen...",
                "ready_text": "Analyse beginnt in Kürze. Größere Unternehmen haben typischerweise mehr ESG-Daten verfügbar."
            },
            "it": {
                "found_title": "🔍 Aziende trovate in",
                "found_text": "Trovate",
                "companies_text": "aziende in",
                "company": "Azienda",
                "industry": "Settore",
                "size": "Dimensione",
                "esg_data": "Dati ESG", 
                "ready_title": "⏳ Pronto ad analizzare queste aziende...",
                "ready_text": "L'analisi inizierà a breve. Le aziende più grandi tipicamente hanno più dati ESG disponibili."
            }
        }
        return texts.get(language, texts["en"])
    
    async def find_companies_in_city_fast(self, city: str, top_n: int = 10, language: str = "en") -> Tuple[List[Dict], str]:
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
        system_prompt = prompt_manager.get_city_discovery_prompt(language).format(
            city=city, 
            top_n=top_n
        )
        
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
                
                # Get localized UI texts
                ui_texts = self._get_ui_texts(language)
                
                # Create discovery HTML with localized text
                discovery_html = f"""
                <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 20px; border-radius: 15px; margin: 20px 0;">
                    <h3 style="color: #1565c0; margin: 0 0 15px 0;">{ui_texts['found_title']} {city}</h3>
                    <p style="color: #424242; margin: 10px 0;">
                        {ui_texts['found_text']} <strong>{len(companies_data)}</strong> {ui_texts['companies_text']} {city}
                    </p>
                    
                    <div style="background: white; padding: 15px; border-radius: 10px; margin: 15px 0;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #e3f2fd;">
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #1976d2;">#</th>
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #1976d2;">{ui_texts['company']}</th>
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #1976d2;">{ui_texts['industry']}</th>
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #1976d2;">{ui_texts['size']}</th>
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #1976d2;">{ui_texts['esg_data']}</th>
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
                
                discovery_html += f"""
                            </tbody>
                        </table>
                    </div>
                    
                    <div style="background: #fff3e0; padding: 15px; border-radius: 10px; margin: 15px 0;">
                        <p style="color: #e65100; margin: 0; font-weight: bold;">
                            {ui_texts['ready_title']}
                        </p>
                        <p style="color: #f57c00; margin: 5px 0; font-size: 14px;">
                            {ui_texts['ready_text']}
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
    
    async def analyze_discovered_companies(self, companies_data: List[Dict], city: str, language: str = "en", progress_callback=None) -> List[SustainabilityData]:
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
                batch_tasks.append(self.analyze_single_company_fast(company_name, city, language))
            
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
    
    async def analyze_single_company_fast(self, company_name: str, city: str, language: str = "en") -> SustainabilityData:
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
                company_name, content[:2], sources[:2], location=city, language=language  # Limit content for speed
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
