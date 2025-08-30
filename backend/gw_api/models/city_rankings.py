"""
Data Models for City Rankings Deep Research
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class SustainabilityData:
    """Unified data class for sustainability information"""
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
    search_results: List[Any] = None  # Will be List[SearchResult] but avoid circular import
    raw_sources: List[str] = None

    def __post_init__(self):
        if self.key_metrics is None:
            self.key_metrics = {}
        if self.key_strengths is None:
            self.key_strengths = []
        if self.key_risks is None:
            self.key_risks = []
        if self.recommendations is None:
            self.recommendations = []
        if self.search_results is None:
            self.search_results = []
        if self.raw_sources is None:
            self.raw_sources = []
        if self.last_updated == "":
            self.last_updated = datetime.now().isoformat()
