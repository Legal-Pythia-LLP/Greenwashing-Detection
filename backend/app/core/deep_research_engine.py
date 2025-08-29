"""
Deep Research Engine for City-Based ESG Analysis
Enhanced deep search with parallel processing support
"""

import os
import asyncio
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("Warning: google.genai not available. Deep search features will be limited.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@dataclass
class SearchResult:
    """Store search results with source information"""
    query: str
    content: str
    timestamp: datetime
    source_type: str = "web_search"
    urls: List[str] = field(default_factory=list)
    snippets: List[str] = field(default_factory=list)

class DeepSearchEngine:
    """Enhanced deep search with parallel processing support"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key) if GENAI_AVAILABLE else None
        self.cache = {}
        self.cache_duration = timedelta(hours=24)
        self.last_request_time = 0
        self.min_request_interval = 1  # Reduced from 2 seconds
        self.semaphore = asyncio.Semaphore(3)  # Allow 3 concurrent requests
    
    async def search_with_sources(self, query: str) -> SearchResult:
        """Search with concurrency control"""
        async with self.semaphore:  # Limit concurrent requests
            # Check cache first
            if query in self.cache:
                cached_result, timestamp = self.cache[query]
                if datetime.now() - timestamp < self.cache_duration:
                    return cached_result
            
            # Perform search
            result = await self._perform_search_with_sources(query)
            
            # Update cache
            self.cache[query] = (result, datetime.now())
            
            return result
    
    async def _perform_search_with_sources(self, query: str) -> SearchResult:
        """Perform search and extract source information"""
        if not GENAI_AVAILABLE or not self.client:
            return SearchResult(query=query, content="", timestamp=datetime.now())
        
        try:
            google_search_tool = types.Tool(google_search=types.GoogleSearch())
            
            # Enhanced prompt to extract sources
            enhanced_query = f"""
            Search for: {query}
            
            Please provide:
            1. The search results with source URLs
            2. Key quotes and snippets
            3. Data sources and their reliability
            """
            
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
                "tools": [google_search_tool]
            }
            
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=enhanced_query,
                config=generation_config
            )
            
            content = response.text
            
            # Extract URLs from content (basic pattern matching)
            urls = re.findall(r'https?://[^\s<>"{}|\\^```]+', content)

            # Extract snippets (sentences containing key information)
            snippets = []
            sentences = content.split('.')
            for sentence in sentences[:10]:  # Get first 10 sentences as snippets
                if len(sentence.strip()) > 20:
                    snippets.append(sentence.strip())
            
            return SearchResult(
                query=query,
                content=content,
                timestamp=datetime.now(),
                source_type="web_search",
                urls=urls[:10],  # Limit to 10 URLs
                snippets=snippets[:5]  # Limit to 5 snippets
            )
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return SearchResult(query=query, content="", timestamp=datetime.now())
