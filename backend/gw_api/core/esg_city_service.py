# backend/gw_api/core/esg_city_service.py
import os, re, json, asyncio, logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

# Optional deep search (google-genai). Safe degrade if missing.
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False
    genai = None
    types = None

load_dotenv()
logger = logging.getLogger("esg-city")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# ---------- Seed fallback so the page always shows something ----------
SEED_COMPANIES_BY_CITY: Dict[str, List[Dict[str, str]]] = {
    "london": [
        {"name": "AstraZeneca", "size": "Large", "industry": "Pharmaceuticals", "importance": "Major employer", "has_esg": "Likely"},
        {"name": "GSK (GlaxoSmithKline)", "size": "Large", "industry": "Pharmaceuticals", "importance": "Sector leader", "has_esg": "Likely"},
        {"name": "HSBC", "size": "Large", "industry": "Banking / Financial Services", "importance": "Global bank", "has_esg": "Likely"},
        {"name": "Lloyds Banking Group", "size": "Large", "industry": "Banking", "importance": "Major bank", "has_esg": "Likely"},
        {"name": "Barclays", "size": "Large", "industry": "Banking / Financial Services", "importance": "Major bank", "has_esg": "Likely"},
        {"name": "Unilever", "size": "Large", "industry": "Consumer Goods", "importance": "Global FMCG", "has_esg": "Likely"},
        {"name": "Vodafone Group", "size": "Large", "industry": "Telecommunications", "importance": "Global telecom", "has_esg": "Likely"},
        {"name": "BP", "size": "Large", "industry": "Oil and Gas", "importance": "Energy major", "has_esg": "Likely"},
        {"name": "Shell plc", "size": "Large", "industry": "Oil & Gas Producers", "importance": "Energy major", "has_esg": "Likely"},
        {"name": "Rio Tinto", "size": "Large", "industry": "Metals and Mining", "importance": "Global miner", "has_esg": "Likely"},
    ],
    "berlin": [
        {"name": "Deutsche Bahn", "size": "Large", "industry": "Transport", "importance": "National rail", "has_esg": "Likely"},
        {"name": "Zalando", "size": "Large", "industry": "E-commerce", "importance": "European leader", "has_esg": "Likely"},
        {"name": "Delivery Hero", "size": "Large", "industry": "Food Delivery", "importance": "Global platform", "has_esg": "Likely"},
        {"name": "HelloFresh", "size": "Large", "industry": "Meal Kits", "importance": "Global platform", "has_esg": "Likely"},
        {"name": "Siemens Energy", "size": "Large", "industry": "Energy Technology", "importance": "Industrial", "has_esg": "Likely"},
        {"name": "Rocket Internet", "size": "Medium", "industry": "Tech/VC", "importance": "Venture builder", "has_esg": "Unknown"},
        {"name": "Bayer Pharma (Berlin hub)", "size": "Large", "industry": "Pharma", "importance": "Major hub", "has_esg": "Likely"},
        {"name": "BASF Services (Berlin)", "size": "Large", "industry": "Chemicals / Services", "importance": "Major hub", "has_esg": "Likely"},
        {"name": "N26", "size": "Medium", "industry": "Fintech", "importance": "Challenger bank", "has_esg": "Unknown"},
        {"name": "Scout24", "size": "Medium", "industry": "Online marketplaces", "importance": "Listed company", "has_esg": "Likely"},
    ],
}

# ---------------------- Data classes ----------------------
@dataclass
class SearchResult:
    query: str
    content: str
    timestamp: datetime
    source_type: str = "web_search"
    urls: List[str] = field(default_factory=list)
    snippets: List[str] = field(default_factory=list)

@dataclass
class SustainabilityData:
    company_name: str
    sustainability_score: float
    environmental_score: float = 0
    social_score: float = 0
    governance_score: float = 0
    esg_rating: str = "N/A"
    report_url: Optional[str] = None
    key_metrics: Dict[str, Any] = None
    summary: str = ""
    last_updated: str = ""
    location: Optional[str] = None
    industry: Optional[str] = None
    key_strengths: List[str] = None
    key_risks: List[str] = None
    recommendations: List[str] = None
    data_quality: Dict[str, Any] = None
    scoring_explanations: Dict[str, Any] = None
    search_results: List[SearchResult] = None
    raw_sources: List[str] = None
    def __post_init__(self):
        self.key_metrics = self.key_metrics or {}
        self.key_strengths = self.key_strengths or []
        self.key_risks = self.key_risks or []
        self.recommendations = self.recommendations or []
        self.search_results = self.search_results or []
        self.raw_sources = self.raw_sources or []
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()

# ---------------------- Helpers ----------------------
JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

def extract_json(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    m = JSON_BLOCK.search(text)
    if not m:
        return {}
    try:
        return json.loads(m.group())
    except Exception:
        # try to trim trailing code fences etc.
        cleaned = m.group().strip().strip("`")
        try:
            return json.loads(cleaned)
        except Exception:
            return {}

# ---------------------- Deep Search ----------------------
# --- Deep Search (safe + SDK-correct) ---------------------------------

class DeepSearchEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # allow disabling with env if key/account doesn't have Search tool
        self.disabled = os.getenv("DISABLE_DEEP_SEARCH", "0") == "1"
        self.client = genai.Client(api_key=self.api_key) if (GENAI_AVAILABLE and not self.disabled) else None
        self.cache: Dict[str, Tuple[SearchResult, datetime]] = {}
        self.cache_duration = timedelta(hours=24)
        self.semaphore = asyncio.Semaphore(3)

    async def search_with_sources(self, query: str) -> SearchResult:
        # Cache + concurrency guard
        async with self.semaphore:
            try:
                if query in self.cache:
                    cached, ts = self.cache[query]
                    if datetime.now() - ts < self.cache_duration:
                        return cached
                res = await self._perform_search_with_sources(query)
                self.cache[query] = (res, datetime.now())
                return res
            except Exception:
                # absolutely never propagate errors to the API layer
                return SearchResult(query=query, content="", timestamp=datetime.now())

    async def _perform_search_with_sources(self, query: str) -> SearchResult:
        """
        Use google.genai properly:
        - contents must be a list of Content or strings
        - generation_config goes in 'generation_config'
        """
        if not GENAI_AVAILABLE or not self.client:
            return SearchResult(query=query, content="", timestamp=datetime.now())

        try:
            prompt = (
                f"Search for: {query}\n\n"
                "Please provide:\n"
                "1) A brief result summary\n"
                "2) 5–10 source URLs\n"
                "3) 3–5 key quotes/snippets\n"
            )

            # Some accounts don’t have the Google Search tool; keep it optional.
            tools = []
            try:
                tools = [types.Tool(google_search=types.GoogleSearch())]
            except Exception:
                tools = []

            # Build a proper Content list payload
            contents = [types.Content(role="user", parts=[types.Part.from_text(prompt)])]

            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,  # <-- list of Content, never empty
                generation_config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=8192,
                    response_mime_type="text/plain",
                    tools=tools or None,  # only pass if available
                ),
            )

            text = getattr(response, "text", "") or ""
            # extract URLs/snippets defensively
            urls = re.findall(r'https?://[^\s<>"{}|\^`]+', text)
            snippets = [s.strip() for s in text.split(".") if len(s.strip()) > 20][:5]

            return SearchResult(
                query=query,
                content=text,
                timestamp=datetime.now(),
                urls=urls[:10],
                snippets=snippets[:5],
            )
        except Exception:
            # If anything goes wrong with deep search, just return empty and
            # let the LLM-only fallback proceed.
            return SearchResult(query=query, content="", timestamp=datetime.now())


# ---------------------- ESG Analyzer ----------------------
class UnifiedESGAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            # Don’t crash the API; log and continue with zeros so UI still works.
            logger.error("GOOGLE_API_KEY not found – analysis will use fallbacks only.")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", google_api_key=self.api_key, temperature=0.1
        )
        self.deep_search = DeepSearchEngine(self.api_key or "")

    async def search_esg_data_with_sources(
        self, company_name: str, location: Optional[str] = None
    ) -> Tuple[List[str], List[SearchResult]]:
        queries: List[str] = []
        if location:
            queries += [
                f'"{company_name}" "{location}" ESG sustainability report',
                f'"{company_name}" headquarters "{location}" environmental social governance',
                f'"{company_name}" based in "{location}" sustainability initiatives',
                f'"{company_name}" "{location}" office carbon emissions climate',
            ]
        queries += [
            f'"{company_name}" ESG report sustainability score rating 2023 2024',
            f'"{company_name}" carbon emissions environmental impact',
            f'"{company_name}" employee diversity social responsibility',
            f'"{company_name}" corporate governance transparency',
        ]

        all_content, all_sources = [], []
        for q in queries:
            try:
                r = await self.deep_search.search_with_sources(q)
                if r.content.strip():
                    all_content.append(r.content)
                    all_sources.append(r)
            except Exception as e:
                logger.warning(f"Search error for '{q}': {e}")
        return all_content, all_sources

    async def analyze_with_explainable_ai(
        self, company_name: str, content: List[str], sources: List[SearchResult], location: Optional[str] = None
    ) -> SustainabilityData:
        source_info = "\n\n".join(
            [
                f"Source {i+1} (Query: {s.query})\nURLs: {', '.join(s.urls[:3]) if s.urls else 'None'}\nSnippets: {' | '.join(s.snippets[:2]) if s.snippets else 'None'}"
                for i, s in enumerate(sources[:5])
            ]
        )
        joined_content = "\n\n".join(content) if content else ""
        truncated = joined_content[:20000]

        system_prompt = (
            "You are an expert ESG analyst. Return a transparent, evidence-backed JSON with keys: "
            "sustainability_score, environmental_score, social_score, governance_score, esg_rating, "
            "industry, location, key_strengths, key_risks, summary, recommendations, "
            "scoring_explanations, data_quality."
        )
        human = (
            f"Company: {company_name}\n"
            f"Location: {location or 'Not specified'}\n\n"
            f"SOURCE INFORMATION:\n{source_info}\n\n"
            f"CONTENT TO ANALYZE:\n{truncated}\n\n"
            "Return ONLY a JSON object with the specified keys."
        )

        analysis: Dict[str, Any] = {}
        try:
            resp = await self.llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=human)])
            analysis = extract_json(resp.content)
        except Exception as e:
            logger.warning(f"LLM analysis failed for {company_name}: {e}")

        if not analysis:
            analysis = {
                "sustainability_score": 0, "environmental_score": 0, "social_score": 0,
                "governance_score": 0, "esg_rating": "N/A",
                "summary": f"Unable to analyze {company_name}.", "key_strengths": [],
                "key_risks": ["Data unavailable"], "recommendations": ["Improve ESG reporting"],
                "scoring_explanations": {"overall_reasoning": "No data"},
                "data_quality": {"information_completeness": "Insufficient", "confidence_score": 0},
                "industry": "Unknown", "location": location,
            }

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
            raw_sources=[s.query for s in sources],
        )

# ---------------------- City Analyzer ----------------------
class CityCompanyAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or ""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", google_api_key=self.api_key, temperature=0.3
        )
        self.deep_search = DeepSearchEngine(self.api_key)
        self.esg_analyzer = UnifiedESGAnalyzer(self.api_key)

    async def find_companies_in_city_fast(self, city: str, top_n: int = 10) -> Tuple[List[Dict], str]:
        """Return up to top_n well-known companies for the city with robust fallbacks."""
        city_norm = (city or "").strip()
        queries = [
            f'largest companies headquartered in "{city_norm}"',
            f'Fortune 500 companies in "{city_norm}"',
            f'major corporations "{city_norm}" headquarters',
            f'biggest employers in "{city_norm}"',
        ]
        # Run deep search in parallel (best-effort)
        content = ""
        try:
            results = await asyncio.gather(*[self.deep_search.search_with_sources(q) for q in queries], return_exceptions=True)
            content = "\n".join([r.content for r in results if isinstance(r, SearchResult) and r.content])[:10000]
        except Exception as e:
            logger.warning(f"Deep search batch failed for city {city_norm}: {e}")

        # Ask LLM to extract company list
        sys = (
            f"Extract WELL-KNOWN companies headquartered in or with major operations in {city_norm}. "
            f"Prioritize large, established firms that publish ESG reports. "
            f"Return STRICT JSON only, max {top_n} items, in this schema:\n"
            '{{"companies":[{{"name":"","size":"Large|Medium|Small","industry":"","importance":"","has_esg":"Likely|Unknown"}}]}}'
        )
        human = content if content else f"No external search content available. Use general knowledge of {city_norm}."

        companies: List[Dict] = []
        try:
            resp = await self.llm.ainvoke([SystemMessage(content=sys), HumanMessage(content=human)])
            data = extract_json(resp.content)
            companies = (data.get("companies") or [])[:top_n]
        except Exception as e:
            logger.warning(f"LLM discovery failed for {city_norm}: {e}")

        # Fallback to seeds if nothing found
        if not companies:
            seed = SEED_COMPANIES_BY_CITY.get(city_norm.lower(), [])
            if seed:
                logger.info(f"Using seed list for city '{city_norm}' (fallback).")
                companies = seed[:top_n]

        # Simple discovery HTML
        html = f"<h3>Companies found in {city_norm}</h3>"
        if companies:
            html += "<ul>" + "".join(
                [f"<li><b>{c.get('name','Unknown')}</b> — {c.get('industry','')} ({c.get('size','')})</li>" for c in companies]
            ) + "</ul>"
        else:
            html += "<p>No companies found.</p>"

        return companies, html

    async def analyze_discovered_companies(self, comps: List[Dict], city: str) -> List[SustainabilityData]:
        tasks = [self.analyze_single_company_fast(c.get("name", "Unknown"), city) for c in comps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        cleaned = [r for r in results if isinstance(r, SustainabilityData)]
        cleaned.sort(key=lambda x: x.sustainability_score, reverse=True)
        return cleaned

    async def analyze_single_company_fast(self, name: str, city: str) -> SustainabilityData:
        queries = [
            f'"{name}" ESG sustainability report score',
            f'"{name}" environmental social governance {city}',
        ]
        res = await asyncio.gather(*[self.deep_search.search_with_sources(q) for q in queries], return_exceptions=True)
        content, sources = [], []
        for r in res:
            if isinstance(r, SearchResult) and r.content:
                content.append(r.content)
                sources.append(r)
        return await self.esg_analyzer.analyze_with_explainable_ai(name, content[:2], sources[:2], location=city)

# ---------------------- Result formatting ----------------------
class ResultFormatter:
    @staticmethod
    def format_multi_company_results(companies: List[SustainabilityData], title: str, discovery_html: str = "") -> str:
        html = f"<h2>{title}</h2>"
        if discovery_html:
            html += discovery_html
        for i, c in enumerate(companies, 1):
            html += "<div style='margin:10px 0;padding:10px;border:1px solid #ddd;border-radius:8px'>"
            html += f"<h3>#{i} {c.company_name} — {c.sustainability_score:.0f}/100</h3>"
            html += f"<p><b>Env/Soc/Gov:</b> {c.environmental_score:.0f} / {c.social_score:.0f} / {c.governance_score:.0f}</p>"
            summary = (c.summary or "")
            short = summary[:220] + ("..." if len(summary) > 220 else "")
            html += f"<p><b>Summary:</b> {short}</p></div>"
        return html

    @staticmethod
    def create_comparison_dataframe(companies: List[SustainabilityData]) -> pd.DataFrame:
        rows = []
        for i, c in enumerate(companies, 1):
            rows.append({
                "Rank": i,
                "Company": c.company_name,
                "Location": c.location or "N/A",
                "Industry": c.industry or "N/A",
                "Overall Score": f"{c.sustainability_score:.1f}",
                "Environmental": f"{c.environmental_score:.0f}",
                "Social": f"{c.social_score:.0f}",
                "Governance": f"{c.governance_score:.0f}",
                "ESG Rating": c.esg_rating,
                "Confidence %": f"{c.data_quality.get('confidence_score', 0) if c.data_quality else 0}",
            })
        return pd.DataFrame(rows)

# ---------------------- Orchestration used by API ----------------------
async def analyze_city_to_payload(city: str, top_n: int = 10) -> Dict[str, Any]:
    analyzer = CityCompanyAnalyzer()
    comps, discovery_html = await analyzer.find_companies_in_city_fast(city, top_n)

    # If still empty after all fallbacks, return no_companies (UI shows banner)
    if not comps:
        logger.info(f"No companies discovered for '{city}'.")
        return {"status": "no_companies", "discovery_html": discovery_html, "report_html": "", "table": []}

    results = await analyzer.analyze_discovered_companies(comps, city)
    if not results:
        logger.info(f"No analysis results for '{city}'.")
        return {"status": "no_companies", "discovery_html": discovery_html, "report_html": "", "table": []}

    report_html = ResultFormatter.format_multi_company_results(results, f"Top {len(results)} Sustainable Companies in {city}", discovery_html)
    df = ResultFormatter.create_comparison_dataframe(results)
    return {"status": "ok", "discovery_html": discovery_html, "report_html": report_html, "table": df.to_dict(orient="records")}
