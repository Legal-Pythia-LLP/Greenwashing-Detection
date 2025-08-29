"""
Deep Research Prompt Manager
Handles multilingual prompts from YAML configuration
"""

import yaml
import os
from typing import Dict, Any
from pathlib import Path

class DeepResearchPromptManager:
    """Manages multilingual prompts for deep research functionality"""
    
    def __init__(self):
        self.prompts = {}
        self.supported_languages = ["en", "de", "it"]
        self.default_language = "en"
        self._load_prompts()
    
    def _load_prompts(self):
        """Load prompts from YAML file"""
        try:
            prompt_file = Path(__file__).parent / "deep_research_prompts.yaml"
            with open(prompt_file, 'r', encoding='utf-8') as file:
                self.prompts = yaml.safe_load(file)
        except Exception as e:
            print(f"Error loading prompts: {e}")
            self.prompts = {}
    
    def get_city_discovery_prompt(self, language: str = "en") -> str:
        """Get city discovery system prompt for specified language"""
        lang = self._validate_language(language)
        try:
            return self.prompts["city_discovery"][lang]["system_prompt"]
        except KeyError:
            print(f"Prompt not found for language {lang}, using English")
            return self.prompts["city_discovery"]["en"]["system_prompt"]
    
    def get_esg_analysis_prompt(self, language: str = "en") -> str:
        """Get ESG analysis system prompt for specified language"""
        lang = self._validate_language(language)
        try:
            return self.prompts["esg_analysis"][lang]["system_prompt"]
        except KeyError:
            print(f"Prompt not found for language {lang}, using English")
            return self.prompts["esg_analysis"]["en"]["system_prompt"]
    
    def _validate_language(self, language: str) -> str:
        """Validate and return language code"""
        if language in self.supported_languages:
            return language
        else:
            print(f"Language {language} not supported, using {self.default_language}")
            return self.default_language
    
    def get_supported_languages(self) -> list:
        """Get list of supported language codes"""
        return self.supported_languages.copy()
    
    def is_language_supported(self, language: str) -> bool:
        """Check if language is supported"""
        return language in self.supported_languages

# Global instance
prompt_manager = DeepResearchPromptManager()
