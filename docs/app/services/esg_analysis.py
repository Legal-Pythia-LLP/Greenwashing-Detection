from langchain.tools import BaseTool
from langchain.schema import HumanMessage, Document
from langchain_community.vectorstores import Chroma
from app.config import ANALYSIS_PROMPTS, SUPPORTED_LANGUAGES, GREENWASHING_KEYWORDS
from app.utils.language import detect_language, is_greenwashing_keyword_present, is_esg_related_multilingual
from app.utils.translation import translate_text
from app.utils.pdf_processing import create_text_splitter
from app.models.pydantic_models import ESGAnalysisState
from webscraper import bbc_search, cnn_search
import json
import logging
from typing import Any, Dict, List, Optional

# 你需要根据实际情况导入 llm、embedding_model
# from app.services.llm import llm, embedding_model
# 这里假设 llm 已经在主入口初始化并传入

class MultilingualESGDocumentAnalysisTool(BaseTool):
    name: str = "multilingual_esg_document_analysis"
    description: str = "Analyzes ESG documents for greenwashing indicators in multiple languages using vector search and semantic analysis"
    vector_store: Any = None
    language: str = 'en'
    llm: Any = None

    def __init__(self, vector_store: Chroma, language: str = 'en', llm: Any = None):
        super().__init__()
        self.vector_store = vector_store
        self.language = language
        self.llm = llm

    def _run(self, query: str) -> str:
        try:
            docs = self.vector_store.similarity_search(query, k=10)
            context = "\n\n".join([doc.page_content for doc in docs])
            analysis_template = ANALYSIS_PROMPTS.get(self.language, ANALYSIS_PROMPTS['en'])['greenwashing_analysis']
            analysis_prompt = analysis_template.format(content=context)
            language_instruction = f"Analyze in {SUPPORTED_LANGUAGES[self.language]}. "
            if self.language != 'en':
                language_instruction += f"Provide analysis in {SUPPORTED_LANGUAGES[self.language]} language. "
            full_prompt = language_instruction + analysis_prompt
            response = self.llm.invoke([HumanMessage(content=full_prompt)])
            return response.content
        except Exception as e:
            return f"Error in multilingual document analysis: {str(e)}"

class MultilingualNewsValidationTool(BaseTool):
    name: str = "multilingual_news_validation"
    description: str = "Validates ESG claims against recent news articles from credible sources in multiple languages"
    company_name: str = ""
    language: str = 'en'
    llm: Any = None

    def __init__(self, company_name: str, language: str = 'en', llm: Any = None):
        super().__init__()
        self.company_name = company_name
        self.language = language
        self.llm = llm

    def _run(self, claims: str) -> str:
        try:
            bbc_articles = bbc_search(self.company_name)
            cnn_articles = cnn_search(self.company_name)
            news_content = []
            from langchain_community.document_loaders import UnstructuredHTMLLoader
            for articles_dict in [bbc_articles, cnn_articles]:
                if articles_dict:
                    for title, file_path in articles_dict.items():
                        try:
                            loader = UnstructuredHTMLLoader(file_path)
                            docs = loader.load()
                            news_content.extend([doc.page_content for doc in docs])
                        except Exception as e:
                            print(f"Error loading article {title}: {e}")
            if not news_content:
                return self._get_no_news_message()
            news_text = "\n\n".join(news_content[:5])
            validation_prompt = self._create_validation_prompt(claims, news_text)
            response = self.llm.invoke([HumanMessage(content=validation_prompt)])
            return response.content
        except Exception as e:
            return f"Error in multilingual news validation: {str(e)}"

    def _get_no_news_message(self) -> str:
        messages = {
            'en': "No recent news articles found for validation",
            'de': "Keine aktuellen Nachrichtenartikel zur Validierung gefunden",
            'it': "Nessun articolo di notizie recenti trovato per la validazione"
        }
        return messages.get(self.language, messages['en'])

    def _create_validation_prompt(self, claims: str, news_text: str) -> str:
        prompts = {
            'en': f"""
            Validate the following ESG claims against recent news articles:
            Claims to validate: {claims}
            News articles: {news_text}
            Determine if the claims are:
            1. Supported by news evidence
            2. Contradicted by news evidence
            3. Not mentioned in news sources
            Provide specific quotes and sources where relevant.
            """,
            'de': f"""
            Validieren Sie die folgenden ESG-Behauptungen gegen aktuelle Nachrichtenartikel:
            Zu validierende Behauptungen: {claims}
            Nachrichtenartikel: {news_text}
            Bestimmen Sie, ob die Behauptungen:
            1. Durch Nachrichtenbelege gestützt werden
            2. Durch Nachrichtenbelege widerlegt werden
            3. In Nachrichtenquellen nicht erwähnt werden
            Geben Sie spezifische Zitate und Quellen an, wo relevant.
            """,
            'it': f"""
            Convalida le seguenti affermazioni ESG contro articoli di notizie recenti:
            Affermazioni da convalidare: {claims}
            Articoli di notizie: {news_text}
            Determina se le affermazioni sono:
            1. Supportate da prove giornalistiche
            2. Contraddette da prove giornalistiche
            3. Non menzionate nelle fonti di notizie
            Fornisci citazioni specifiche e fonti dove rilevante.
            """
        }
        return prompts.get(self.language, prompts['en'])

class MultilingualESGMetricsCalculatorTool(BaseTool):
    name: str = "multilingual_esg_metrics_calculator"
    description: str = "Calculates quantitative greenwashing metrics for visualization in multiple languages"
    language: str = 'en'
    llm: Any = None

    def __init__(self, language: str = 'en', llm: Any = None):
        super().__init__()
        self.language = language
        self.llm = llm

    def _run(self, analysis_text: str) -> str:
        try:
            metrics_template = ANALYSIS_PROMPTS.get(self.language, ANALYSIS_PROMPTS['en'])['metrics_calculation']
            metrics_prompt = metrics_template.format(analysis=analysis_text)
            language_instruction = f"Provide analysis in {SUPPORTED_LANGUAGES[self.language]}. "
            full_prompt = language_instruction + metrics_prompt
            response = self.llm.invoke([HumanMessage(content=full_prompt)])
            return response.content
        except Exception as e:
            return f"Error calculating multilingual metrics: {str(e)}"

def analyze_language_specific_greenwashing(text: str, language: str) -> Dict[str, Any]:
    patterns = {
        'en': {
            'vague_terms': ['sustainable', 'eco-friendly', 'green', 'natural', 'clean'],
            'unsubstantiated_claims': ['100% natural', 'completely sustainable', 'carbon neutral'],
            'misleading_prefixes': ['eco-', 'bio-', 'green-', 'sustainable-']
        },
        'de': {
            'vague_terms': ['nachhaltig', 'umweltfreundlich', 'grün', 'natürlich', 'sauber'],
            'unsubstantiated_claims': ['100% natürlich', 'vollständig nachhaltig', 'klimaneutral'],
            'misleading_prefixes': ['öko-', 'bio-', 'grün-', 'nachhaltig-']
        },
        'it': {
            'vague_terms': ['sostenibile', 'eco-compatibile', 'verde', 'naturale', 'pulito'],
            'unsubstantiated_claims': ['100% naturale', 'completamente sostenibile', 'carbon neutral'],
            'misleading_prefixes': ['eco-', 'bio-', 'verde-', 'sostenibile-']
        }
    }
    lang_patterns = patterns.get(language, patterns['en'])
    text_lower = text.lower()
    vague_count = sum(1 for term in lang_patterns['vague_terms'] if term in text_lower)
    unsubstantiated_count = sum(1 for claim in lang_patterns['unsubstantiated_claims'] if claim in text_lower)
    misleading_prefix_count = sum(1 for prefix in lang_patterns['misleading_prefixes'] 
                                 if any(word.startswith(prefix) for word in text_lower.split()))
    return {
        'vague_terms_count': vague_count,
        'unsubstantiated_claims_count': unsubstantiated_count,
        'misleading_prefix_count': misleading_prefix_count,
        'total_greenwashing_indicators': vague_count + unsubstantiated_count + misleading_prefix_count,
        'language': language,
        'language_name': SUPPORTED_LANGUAGES[language]
    }

def extract_multilingual_entities(text: str, language: str) -> Dict[str, List[str]]:
    import spacy
    entities = {
        'organizations': [],
        'persons': [],
        'locations': [],
        'dates': [],
        'money': []
    }
    nlp_models = {}
    try:
        if language == 'en':
            nlp_models['en'] = spacy.load("en_core_web_sm")
        elif language == 'de':
            nlp_models['de'] = spacy.load("de_core_news_sm")
        elif language == 'it':
            nlp_models['it'] = spacy.load("it_core_news_sm")
    except Exception as e:
        logging.warning(f"spaCy model not loaded: {e}")
        return entities
    if language in nlp_models:
        try:
            doc = nlp_models[language](text)
            for ent in doc.ents:
                if ent.label_ in ['ORG', 'ORGANIZATION']:
                    entities['organizations'].append(ent.text)
                elif ent.label_ in ['PERSON', 'PER']:
                    entities['persons'].append(ent.text)
                elif ent.label_ in ['GPE', 'LOC', 'LOCATION']:
                    entities['locations'].append(ent.text)
                elif ent.label_ in ['DATE', 'TIME']:
                    entities['dates'].append(ent.text)
                elif ent.label_ in ['MONEY', 'MONETARY']:
                    entities['money'].append(ent.text)
        except Exception as e:
            logging.warning(f"Entity extraction error for {language}: {e}")
    return entities

def comprehensive_esg_analysis_multilingual(session_id: str, vector_store: Chroma, company_name: str, language: str, llm: Any) -> Dict[str, Any]:
    try:
        analysis_tool = MultilingualESGDocumentAnalysisTool(vector_store, language, llm)
        news_tool = MultilingualNewsValidationTool(company_name, language, llm)
        metrics_tool = MultilingualESGMetricsCalculatorTool(language, llm)
        document_analysis = analysis_tool._run(f"Perform detailed ESG analysis in {SUPPORTED_LANGUAGES[language]} language")
        if company_name and company_name.lower() != "unknown":
            news_validation = news_tool._run(document_analysis)
        else:
            no_validation_msg = {
                'en': "Company name not recognized. News validation skipped.",
                'de': "Firmenname nicht erkannt. Nachrichtenvalidierung übersprungen.",
                'it': "Nome dell'azienda non riconosciuto. Validazione notizie saltata."
            }
            news_validation = no_validation_msg.get(language, no_validation_msg['en'])
        metrics_calculation = metrics_tool._run(f"Document Analysis: {document_analysis}\nNews Validation: {news_validation}")
        synthesis_prompts = {
            'en': f"""Create a comprehensive ESG greenwashing assessment report in English...""",
            'de': f"""Erstellen Sie einen umfassenden ESG-Greenwashing-Bewertungsbericht auf Deutsch...""",
            'it': f"""Crea un rapporto completo di valutazione del greenwashing ESG in italiano..."""
        }
        synthesis_prompt = synthesis_prompts.get(language, synthesis_prompts['en'])
        final_response = llm.invoke([HumanMessage(content=synthesis_prompt)])
        final_synthesis = final_response.content
        return {
            "initial_analysis": f"Multilingual analysis completed in {SUPPORTED_LANGUAGES[language]}",
            "document_analysis": document_analysis,
            "news_validation": news_validation,
            "metrics": metrics_calculation,
            "final_synthesis": final_synthesis,
            "detected_language": language,
            "comprehensive_analysis": f"""
            Language: {SUPPORTED_LANGUAGES[language]}
            Document Analysis: {document_analysis}
            News Validation: {news_validation}
            Metrics: {metrics_calculation}
            """,
            "error": None
        }
    except Exception as e:
        return {
            "error": f"Error in multilingual comprehensive analysis: {str(e)}",
            "detected_language": language
        } 