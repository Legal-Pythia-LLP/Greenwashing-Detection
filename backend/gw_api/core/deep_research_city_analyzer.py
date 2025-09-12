"""
City-Based Company Analyzer for Deep Research
Short timeouts + global RPM throttle + robust fallbacks
(Handles both 429 rate limits and 400 API key errors gracefully)
"""

import os
import re
import json
import time
import asyncio
import logging
from collections import deque
from typing import List, Dict, Any, Optional, Tuple

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage, HumanMessage

from gw_api.models.city_rankings import SustainabilityData
from .deep_research_engine import DeepSearchEngine, SearchResult
from .deep_research_analyzer import UnifiedESGAnalyzer
from .deep_research_prompt_manager import prompt_manager

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARCH_TIMEOUT_S = 6             # per deep-search call
DISCOVERY_LLM_TIMEOUT_S = 25     # discovery model
ANALYSIS_LLM_TIMEOUT_S = 45      # per-company analysis model
BATCH_SIZE = int(os.getenv("CITY_ANALYSIS_BATCH_SIZE", "2"))
COMPANY_SEARCH_QUERIES = 1       # keep calls minimal
MAX_RPM = int(os.getenv("GEMINI_RPM", "8"))  # global RPM throttle

# -----------------------------------------------------------------------------
# Catalog fallback (ensures discovery never shows empty)
# -----------------------------------------------------------------------------

KNOWN_COMPANIES_BY_CITY: Dict[str, List[Dict[str, str]]] = {
    "munich": [
        {"name": "BMW AG (BMW Group)", "size": "Large", "industry": "Automotive", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Allianz SE", "size": "Large", "industry": "Insurance, Asset Management", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Siemens AG", "size": "Large", "industry": "Conglomerate (Electronics, Engineering, Automation)", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Munich Re", "size": "Large", "industry": "Reinsurance", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Infineon Technologies AG", "size": "Large", "industry": "Semiconductor Manufacturing", "importance": "Regional leader", "has_esg": "Likely"},
    ],
    "london": [
        {"name": "HSBC Holdings", "size": "Large", "industry": "Banking & Financial Services", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "BP plc", "size": "Large", "industry": "Energy", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Unilever plc", "size": "Large", "industry": "Consumer Goods", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Barclays", "size": "Large", "industry": "Banking", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Diageo plc", "size": "Large", "industry": "Beverages", "importance": "Regional leader", "has_esg": "Likely"},
    ],
    "san francisco": [
        {"name": "Salesforce", "size": "Large", "industry": "Software (SaaS)", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Uber", "size": "Large", "industry": "Mobility / Tech", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "DoorDash", "size": "Large", "industry": "Logistics / Delivery", "importance": "Regional leader", "has_esg": "Likely"},
        {"name": "Visa Inc.", "size": "Large", "industry": "Payments", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Airbnb", "size": "Large", "industry": "Travel / Tech", "importance": "Regional leader", "has_esg": "Likely"},
    ],
    "tokyo": [
        {"name": "Sony Group Corporation", "size": "Large", "industry": "Electronics, Entertainment, Finance", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Honda Motor Co., Ltd.", "size": "Large", "industry": "Automotive", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Mitsubishi Corporation", "size": "Large", "industry": "Trading, Diversified", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "SoftBank Group Corp.", "size": "Large", "industry": "Telecommunications, Investment", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Hitachi, Ltd.", "size": "Large", "industry": "IT, Power, Infrastructure", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Canon Inc.", "size": "Large", "industry": "Imaging, Optical products", "importance": "Regional leader", "has_esg": "Likely"},
        {"name": "Fast Retailing Co., Ltd. (Uniqlo)", "size": "Large", "industry": "Apparel Retail", "importance": "Regional leader", "has_esg": "Likely"},
        {"name": "Rakuten Group, Inc.", "size": "Large", "industry": "E-commerce, Fintech, Telecom", "importance": "Regional leader", "has_esg": "Likely"},
        {"name": "Nippon Telegraph and Telephone Corporation (NTT)", "size": "Large", "industry": "Telecommunications", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Seven & i Holdings Co., Ltd.", "size": "Large", "industry": "Retail / Convenience Stores", "importance": "Regional leader", "has_esg": "Likely"},
    ],
    "copenhagen": [
        {"name": "A.P. Møller – Mærsk A/S (Maersk)", "size": "Large", "industry": "Shipping & Logistics", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Novo Nordisk", "size": "Large", "industry": "Pharmaceuticals", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Danske Bank", "size": "Large", "industry": "Financial Services (Banking)", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Carlsberg Group", "size": "Large", "industry": "Beverages (Brewing)", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Ørsted", "size": "Large", "industry": "Renewable Energy", "importance": "Regional leader", "has_esg": "Likely"},
        {"name": "DSV", "size": "Large", "industry": "Logistics & Transport", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "ISS A/S", "size": "Large", "industry": "Facility Services", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "Pandora", "size": "Large", "industry": "Jewelry Manufacturing & Retail", "importance": "Regional leader", "has_esg": "Likely"},
        {"name": "Genmab", "size": "Large", "industry": "Biotechnology/Pharmaceuticals", "importance": "Regional leader", "has_esg": "Likely"},
        {"name": "Novozymes", "size": "Large", "industry": "Industrial Biotechnology/Enzymes", "importance": "Regional leader", "has_esg": "Likely"},
    ],
}

CITY_ALIASES: Dict[str, str] = {
    "muenchen": "munich", "münchen": "munich", "munchen": "munich",
    "tokio": "tokyo",
    "københavn": "copenhagen", "kobenhavn": "copenhagen", "kopenhagen": "copenhagen",
}

def _normalize_city_key(city: str) -> str:
    key = city.strip().lower()
    return CITY_ALIASES.get(key, key)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
JSON_ANY   = re.compile(r"\{.*\}", re.DOTALL)

def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    m = JSON_BLOCK.search(text)
    if not m:
        m = JSON_ANY.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1) if JSON_BLOCK.search(text) else m.group(0))
    except Exception:
        return None

def _looks_like_429(err: Exception) -> bool:
    s = str(err).lower()
    return "resourceexhausted" in s or "resource_exhausted" in s or "429" in s

def _looks_like_auth(err: Exception) -> bool:
    s = str(err).lower()
    return ("api key" in s) or ("api_key_invalid" in s) or ("key expired" in s) or ("401" in s) or ("invalid_argument" in s)

def _placeholder(company_name: str, city: str, reason: str) -> SustainabilityData:
    return SustainabilityData(
        company_name=company_name,
        sustainability_score=0.0,
        environmental_score=0.0,
        social_score=0.0,
        governance_score=0.0,
        esg_rating="N/A",
        location=city,
        industry=None,
        key_strengths=[],
        key_risks=[],
        recommendations=[],
        summary=f"Analysis skipped: {reason}.",
        data_quality={"status": "unavailable", "reason": reason},
        scoring_explanations=None,
        last_updated=""
    )

class _Throttle:
    """Simple global RPM limiter for Gemini calls."""
    def __init__(self, rpm: int):
        self.rpm = rpm
        self._times = deque()
        self._lock = asyncio.Lock()

    async def sleep_if_needed(self):
        if self.rpm <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            while self._times and now - self._times[0] > 60.0:
                self._times.popleft()
            if len(self._times) >= self.rpm:
                to_sleep = 60.0 - (now - self._times[0]) + 0.05
                await asyncio.sleep(max(0.05, to_sleep))
                now = time.monotonic()
                while self._times and now - self._times[0] > 60.0:
                    self._times.popleft()
            self._times.append(time.monotonic())

# -----------------------------------------------------------------------------
# Analyzer
# -----------------------------------------------------------------------------

class CityCompanyAnalyzer:
    """Lean discovery -> analysis pipeline with graceful degradation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.auth_ok = bool(self.api_key)

        # Gemini client with retries disabled (avoid long backoffs)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.api_key,
            temperature=0.3,
            max_retries=0,
        )

        self.deep_search = DeepSearchEngine(self.api_key)
        self.esg_analyzer = UnifiedESGAnalyzer(self.api_key)
        try:
            if hasattr(self.esg_analyzer, "llm") and hasattr(self.esg_analyzer.llm, "max_retries"):
                self.esg_analyzer.llm.max_retries = 0
        except Exception:
            pass

        self.discovered_companies: List[Dict[str, Any]] = []
        self._throttle = _Throttle(MAX_RPM)

        if not self.auth_ok:
            logger.warning("GOOGLE_API_KEY is missing; LLM features will be disabled and fallbacks used.")

    # ---- UI text ----
    def _get_ui_texts(self, language: str) -> Dict[str, str]:
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
                "ready_text": "Analysis will begin shortly. Larger companies typically have more ESG data available.",
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
                "ready_text": "Analyse beginnt in Kürze. Größere Unternehmen haben typischerweise mehr ESG-Daten verfügbar.",
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
                "ready_text": "L'analisi inizierà a breve. Le aziende più grandi tipicamente hanno più dati ESG disponibili.",
            },
        }
        return texts.get(language, texts["en"])

    # ---- Discovery ----
    async def find_companies_in_city_fast(
        self, city: str, top_n: int = 10, language: str = "en"
    ) -> Tuple[List[Dict[str, Any]], str]:

        city_norm = city.strip()
        city_key = _normalize_city_key(city_norm)
        queries = [
            f'largest companies headquartered in "{city_norm}"',
            f'Fortune 500 companies in "{city_norm}"',
            f'major corporations "{city_norm}" headquarters',
            f'biggest employers in "{city_norm}"',
        ]

        combined_search_text = ""
        if self.auth_ok:
            try:
                async def _one(q: str):
                    await self._throttle.sleep_if_needed()
                    return await asyncio.wait_for(self.deep_search.search_with_sources(q), timeout=SEARCH_TIMEOUT_S)

                results = await asyncio.gather(*[_one(q) for q in queries], return_exceptions=True)
                parts: List[str] = []
                for r in results:
                    if isinstance(r, SearchResult) and r.content and r.content.strip():
                        parts.append(r.content)
                    elif isinstance(r, Exception):
                        # If auth issue detected, disable LLM for the rest of this request
                        if _looks_like_auth(r):
                            self.auth_ok = False
                            logger.warning("Deep search auth error; switching to catalog fallback.")
                        logger.warning("Deep search error: %s", r)
                combined_search_text = "\n".join(parts)
            except Exception as e:
                if _looks_like_auth(e):
                    self.auth_ok = False
                    logger.warning("Deep search auth error; switching to catalog fallback.")
                else:
                    logger.warning("Deep search batch failed: %s", e)

        system_prompt = (
            prompt_manager.get_city_discovery_prompt(language).format(city=city_norm, top_n=top_n)
            if hasattr(prompt_manager, "get_city_discovery_prompt")
            else (
                f"Extract WELL-KNOWN companies from {city_norm}.\n"
                f"Return STRICT JSON only with at most {top_n} items, schema:\n"
                r'{"companies":[{"name":"","size":"Large|Medium|Small","industry":"","importance":"","has_esg":"Likely|Unknown"}]}'
            )
        )

        companies_data: List[Dict[str, Any]] = []
        if self.auth_ok:
            human_content = (
                combined_search_text[:10000]
                if combined_search_text.strip()
                else (
                    "No external search results are available (rate-limited, overloaded, or empty). "
                    f"Based on general knowledge only, list up to {top_n} well-known companies "
                    f"headquartered in or with major operations in {city_norm}. "
                    "Prefer companies that likely publish ESG reports. "
                    "Respond with STRICT JSON only using exactly this schema: "
                    r'{"companies":[{"name":"","size":"Large|Medium|Small","industry":"","importance":"","has_esg":"Likely|Unknown"}]}'
                )
            )
            try:
                async def _invoke():
                    await self._throttle.sleep_if_needed()
                    return await self.llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=human_content)])

                resp = await asyncio.wait_for(_invoke(), timeout=DISCOVERY_LLM_TIMEOUT_S)
                data = _extract_json(getattr(resp, "content", "") or "")
                if data:
                    companies_data = list(data.get("companies", []))[:top_n]
                else:
                    logger.warning("City discovery: no JSON object found in model output.")
            except Exception as e:
                if _looks_like_auth(e):
                    self.auth_ok = False
                    logger.warning("Discovery LLM auth error; will use catalog.")
                elif _looks_like_429(e):
                    logger.warning("Discovery LLM rate-limited; will use catalog.")
                else:
                    logger.warning("Discovery LLM failed: %s", e)

        # Catalog fallback (also used if auth disabled)
        if not companies_data and city_key in KNOWN_COMPANIES_BY_CITY:
            logger.info("Using catalog fallback for city=%s", city_norm)
            companies_data = KNOWN_COMPANIES_BY_CITY[city_key][:top_n]

        # Build discovery HTML
        ui = self._get_ui_texts(language)
        if companies_data:
            rows = []
            for i, comp in enumerate(companies_data, 1):
                size = comp.get("size", "Unknown")
                esg = comp.get("has_esg", "Unknown")
                size_color = {"Large": "#4caf50", "Medium": "#ff9800", "Small": "#9e9e9e"}.get(size, "#9e9e9e")
                esg_color = {"Likely": "#4caf50", "Unknown": "#ff9800"}.get(esg, "#ff9800")
                rows.append(
                    f"""
                    <tr style="border-bottom:1px solid #e0e0e0;">
                        <td style="padding:10px;">{i}</td>
                        <td style="padding:10px;font-weight:bold;color:#1976d2;">{comp.get("name","Unknown")}</td>
                        <td style="padding:10px;">{comp.get("industry","Unknown")}</td>
                        <td style="padding:10px;">
                            <span style="background:{size_color};color:white;padding:2px 8px;border-radius:10px;font-size:12px;">
                                {size}
                            </span>
                        </td>
                        <td style="padding:10px;">
                            <span style="background:{esg_color};color:white;padding:2px 8px;border-radius:10px;font-size:12px;">
                                {esg}
                            </span>
                        </td>
                    </tr>
                    """
                )

            discovery_html = f"""
            <div style="background:linear-gradient(135deg,#e3f2fd 0%,#bbdefb 100%);padding:20px;border-radius:15px;margin:20px 0;">
                <h3 style="color:#1565c0;margin:0 0 15px 0;">{ui['found_title']} {city_norm}</h3>
                <p style="color:#424242;margin:10px 0;">
                    {ui['found_text']} <strong>{len(companies_data)}</strong> {ui['companies_text']} {city_norm}
                </p>
                <div style="background:white;padding:15px;border-radius:10px;margin:15px 0;">
                    <table style="width:100%;border-collapse:collapse;">
                        <thead>
                            <tr style="background:#e3f2fd;">
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #1976d2;">#</th>
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #1976d2;">{ui['company']}</th>
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #1976d2;">{ui['industry']}</th>
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #1976d2;">{ui['size']}</th>
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #1976d2;">{ui['esg_data']}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(rows)}
                        </tbody>
                    </table>
                </div>
                <div style="background:#fff3e0;padding:15px;border-radius:10px;margin:15px 0;">
                    <p style="color:#e65100;margin:0;font-weight:bold;">{ui['ready_title']}</p>
                    <p style="color:#f57c00;margin:5px 0;font-size:14px;">{ui['ready_text']}</p>
                </div>
            </div>
            """
        else:
            discovery_html = f"<div style='color:red;'>No companies found in {city_norm}</div>"

        self.discovered_companies = companies_data
        return companies_data, discovery_html

    # ---- Analysis ----
    async def analyze_discovered_companies(
        self,
        companies_data: List[Dict[str, Any]],
        city: str,
        language: str = "en",
        progress_callback=None,
    ) -> List[SustainabilityData]:

        results: List[SustainabilityData] = []
        total = len(companies_data)
        if total == 0:
            return results

        # If auth is broken, skip LLM and return placeholders quickly
        if not self.auth_ok:
            return [
                _placeholder(c.get("name", "Unknown"), city, "API key invalid/expired or not configured")
                for c in companies_data
            ]

        for i in range(0, total, BATCH_SIZE):
            batch = companies_data[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

            if progress_callback:
                progress_callback((batch_num / total_batches), f"Analyzing batch {batch_num}/{total_batches}...")

            async def _safe(company_name: str):
                try:
                    await self._throttle.sleep_if_needed()
                    return await asyncio.wait_for(
                        self.analyze_single_company_fast(company_name, city, language),
                        timeout=ANALYSIS_LLM_TIMEOUT_S,
                    )
                except Exception as e:
                    if _looks_like_auth(e):
                        self.auth_ok = False
                        logger.warning("Auth error during analysis; remaining companies will be placeholders.")
                        return _placeholder(company_name, city, "API key invalid/expired")
                    if _looks_like_429(e):
                        logger.warning("Rate-limited while analyzing %s; returning placeholder.", company_name)
                        return _placeholder(company_name, city, "API rate limit")
                    logger.warning("Analysis hard-failed for %s: %s", company_name, e)
                    return _placeholder(company_name, city, "Analysis failed")

            results.extend(await asyncio.gather(*[_safe(c.get("name", "Unknown")) for c in batch]))
            await asyncio.sleep(0.25)  # tiny spacing to reduce bursts

        results.sort(key=lambda x: x.sustainability_score, reverse=True)
        return results

    async def analyze_single_company_fast(
        self, company_name: str, city: str, language: str = "en"
    ) -> SustainabilityData:
        """Fast single-company analysis with short search timeouts and fallback."""
        if not self.auth_ok:
            return _placeholder(company_name, city, "API key invalid/expired")

        try:
            base_queries = [
                f'"{company_name}" ESG sustainability report',
                f'"{company_name}" environmental social governance {city}',
            ]
            queries = base_queries[:COMPANY_SEARCH_QUERIES]

            async def _one(q: str):
                await self._throttle.sleep_if_needed()
                return await asyncio.wait_for(self.deep_search.search_with_sources(q), timeout=SEARCH_TIMEOUT_S)

            results = await asyncio.gather(*[_one(q) for q in queries], return_exceptions=True)

            content: List[str] = []
            sources: List[SearchResult] = []
            for r in results:
                if isinstance(r, SearchResult) and r.content:
                    content.append(r.content)
                    sources.append(r)
                elif isinstance(r, Exception):
                    if _looks_like_auth(r):
                        self.auth_ok = False
                        return _placeholder(company_name, city, "API key invalid/expired")

            if not content:
                content = [f"General knowledge analysis for {company_name} in {city}. Provide transparent, evidence-seeking reasoning even if sources are limited."]

            async def _analyze():
                await self._throttle.sleep_if_needed()
                return await self.esg_analyzer.analyze_with_explainable_ai(
                    company_name, content[:2], sources[:2], location=city, language=language
                )

            try:
                return await asyncio.wait_for(_analyze(), timeout=ANALYSIS_LLM_TIMEOUT_S)
            except Exception as e:
                if _looks_like_auth(e):
                    self.auth_ok = False
                    return _placeholder(company_name, city, "API key invalid/expired")
                if _looks_like_429(e):
                    return _placeholder(company_name, city, "API rate limit")
                # one lightweight retry
                await asyncio.sleep(1.0)
                try:
                    await self._throttle.sleep_if_needed()
                    return await asyncio.wait_for(_analyze(), timeout=ANALYSIS_LLM_TIMEOUT_S)
                except Exception as e2:
                    if _looks_like_auth(e2):
                        self.auth_ok = False
                        return _placeholder(company_name, city, "API key invalid/expired")
                    if _looks_like_429(e2):
                        return _placeholder(company_name, city, "API rate limit")
                    return _placeholder(company_name, city, "Analysis failed")

        except Exception as e:
            if _looks_like_auth(e):
                self.auth_ok = False
                return _placeholder(company_name, city, "API key invalid/expired")
            if _looks_like_429(e):
                return _placeholder(company_name, city, "API rate limit")
            return _placeholder(company_name, city, "Analysis failed")
