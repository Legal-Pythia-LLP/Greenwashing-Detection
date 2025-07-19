import hashlib
import os
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, TypedDict
import pandas as pd
import torch
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import langdetect
from langdetect import detect
import requests
from deep_translator import GoogleTranslator
import logging
import spacy

# Updated LangChain imports - using new packages
from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents.agent_types import AgentType
from langchain.agents.initialize import initialize_agent
from langchain.chains import LLMChain
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, UnstructuredHTMLLoader
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.schema import Document, HumanMessage, SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.tools import Tool, BaseTool
from langchain_community.vectorstores import Chroma
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.summarize import load_summarize_chain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.manager import CallbackManager

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import json

# Custom imports
from webscraper import bbc_search, cnn_search

load_dotenv()

# Environment variables
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY_2 = os.getenv("AZURE_OPENAI_API_KEY_2")
AZURE_OPENAI_ENDPOINT_2 = os.getenv("AZURE_OPENAI_ENDPOINT_2")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

# Paths
BASE_PATH = Path(__file__).parent
UPLOAD_DIR = BASE_PATH / "uploads"
COMPANIES_PATH = BASE_PATH / "data_files/companies.csv"

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'de': 'German',
    'it': 'Italian'
}

# Language-specific greenwashing keywords
GREENWASHING_KEYWORDS = {
    'en': [
        'sustainable', 'green', 'eco-friendly', 'carbon neutral', 'clean energy',
        'renewable', 'environmentally responsible', 'climate-friendly', 'net-zero',
        'carbon footprint', 'biodegradable', 'organic', 'natural', 'zero waste',
        'climate action', 'sustainable development', 'environmental stewardship'
    ],
    'de': [
        'nachhaltig', 'grün', 'umweltfreundlich', 'klimaneutral', 'saubere energie',
        'erneuerbar', 'umweltverantwortlich', 'klimafreundlich', 'netto-null',
        'co2-fußabdruck', 'biologisch abbaubar', 'organisch', 'natürlich', 'null abfall',
        'klimaschutz', 'nachhaltige entwicklung', 'umweltschutz'
    ],
    'it': [
        'sostenibile', 'verde', 'eco-compatibile', 'carbon neutral', 'energia pulita',
        'rinnovabile', 'responsabile ambientale', 'climate-friendly', 'zero netto',
        'impronta carbonica', 'biodegradabile', 'organico', 'naturale', 'zero rifiuti',
        'azione climatica', 'sviluppo sostenibile', 'gestione ambientale'
    ]
}

# Language-specific analysis prompts
ANALYSIS_PROMPTS = {
    'en': {
        'company_extraction': "Extract the company name from this context. Return only the company name, nothing else.",
        'greenwashing_analysis': """Analyze the following ESG document content for greenwashing indicators:

Content: {content}

Look for:
1. Vague or unsubstantiated claims
2. Lack of specific metrics or targets
3. Misleading terminology
4. Cherry-picked data
5. Absence of third-party verification

Provide specific evidence and scoring rationale.""",
        'metrics_calculation': """Based on the following ESG analysis, calculate specific greenwashing metrics:

Analysis: {analysis}

Calculate scores (0-100) for each metric:
1. Vague Language Score
2. Evidence Quality Score
3. Transparency Score
4. Measurability Score
5. Third-party Verification Score

Format as JSON with detailed evidence for each metric."""
    },
    'de': {
        'company_extraction': "Extrahieren Sie den Firmennamen aus diesem Kontext. Geben Sie nur den Firmennamen zurück, nichts anderes.",
        'greenwashing_analysis': """Analysieren Sie den folgenden ESG-Dokumentinhalt auf Greenwashing-Indikatoren:

Inhalt: {content}

Suchen Sie nach:
1. Vagen oder unbegründeten Behauptungen
2. Fehlenden spezifischen Kennzahlen oder Zielen
3. Irreführender Terminologie
4. Selektiv ausgewählten Daten
5. Fehlender Drittpartei-Verifizierung

Geben Sie spezifische Belege und Bewertungslogik an.""",
        'metrics_calculation': """Basierend auf der folgenden ESG-Analyse berechnen Sie spezifische Greenwashing-Kennzahlen:

Analyse: {analysis}

Berechnen Sie Scores (0-100) für jede Kennzahl:
1. Score für vage Sprache
2. Score für Beweisqualität
3. Transparenz-Score
4. Messbarkeits-Score
5. Drittpartei-Verifizierungs-Score

Formatieren Sie als JSON mit detaillierten Belegen für jede Kennzahl."""
    },
    'it': {
        'company_extraction': "Estrai il nome dell'azienda da questo contesto. Restituisci solo il nome dell'azienda, nient'altro.",
        'greenwashing_analysis': """Analizza il seguente contenuto del documento ESG per indicatori di greenwashing:

Contenuto: {content}

Cerca:
1. Affermazioni vaghe o non supportate
2. Mancanza di metriche o obiettivi specifici
3. Terminologia fuorviante
4. Dati selezionati ad hoc
5. Assenza di verifica da parte terza

Fornisci evidenze specifiche e razionale di valutazione.""",
        'metrics_calculation': """Basato sulla seguente analisi ESG, calcola metriche specifiche di greenwashing:

Analisi: {analysis}

Calcola punteggi (0-100) per ogni metrica:
1. Punteggio Linguaggio Vago
2. Punteggio Qualità delle Prove
3. Punteggio Trasparenza
4. Punteggio Misurabilità
5. Punteggio Verifica Terze Parti

Formatta come JSON con evidenze dettagliate per ogni metrica."""
    }
}

# Load valid companies
df = pd.read_csv(COMPANIES_PATH)
VALID_COMPANIES = [name.lower() for name in df["company_names"].to_list()]

VALID_UPLOAD_TYPES = ["application/pdf"]

# Initialize translator
# translator = Translator()

# Initialize spaCy models for each language
nlp_models = {}
try:
    nlp_models['en'] = spacy.load("en_core_web_sm")
    nlp_models['de'] = spacy.load("de_core_news_sm")
    nlp_models['it'] = spacy.load("it_core_news_sm")
except OSError as e:
    print(f"Warning: Some spaCy models are not installed. {e}")
    print("Please install with: python -m spacy download en_core_web_sm de_core_news_sm it_core_news_sm")

# Pydantic models
class ChatBaseMessage(BaseModel):
    message: str
    session_id: str

class ESGAnalysisResult(BaseModel):
    greenwashing_score: float
    confidence: float
    reasoning: str
    evidence: List[str]
    metrics: Dict[str, Any]
    detected_language: str

# Language detection and processing utilities
def detect_language(text: str) -> str:
    """Detect the language of the text"""
    try:
        detected = detect(text)
        if detected in SUPPORTED_LANGUAGES:
            return detected
        else:
            return 'en'  # Default to English
    except:
        return 'en'  # Default to English if detection fails


# 替换原来的导入
# from googletrans import Translator

# 新的导入
from deep_translator import GoogleTranslator
import logging


# 移除或注释掉原来的 translator 初始化
# translator = Translator()

def translate_text(text: str, target_lang: str, source_lang: str = 'auto') -> str:
    """使用 deep-translator 翻译文本"""
    try:
        if source_lang == target_lang:
            return text

        # 处理 'auto' 源语言
        if source_lang == 'auto':
            source_lang = 'auto'

        # 创建翻译器实例
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        result = translator.translate(text)
        return result

    except Exception as e:
        logging.warning(f"Translation error: {e}")
        # 回退策略：返回原文
        return text


# def detect_language(text: str) -> str:
#     """检测文本语言 - 使用 deep-translator 的语言检测"""
#     try:
#         from deep_translator import GoogleTranslator
#
#         # deep-translator 的语言检测方法
#         detected = GoogleTranslator(source='auto', target='en').detect(text)
#         if detected in SUPPORTED_LANGUAGES:
#             return detected
#         else:
#             return 'en'  # 默认返回英语
#     except Exception as e:
#         logging.warning(f"Language detection error: {e}")
#         # 回退到 langdetect
#         try:
#             import langdetect
#             detected = langdetect.detect(text)
#             if detected in SUPPORTED_LANGUAGES:
#                 return detected
#             else:
#                 return 'en'
#         except:
#             return 'en'  # 最终回退到英语


def detect_language(text: str) -> str:
    """检测文本语言 - 使用 deep-translator 的语言检测"""
    try:
        from deep_translator import GoogleTranslator

        # deep-translator 的语言检测方法
        detected = GoogleTranslator(source='auto', target='en').detect(text)
        if detected in SUPPORTED_LANGUAGES:
            return detected
        else:
            return 'en'  # 默认返回英语
    except Exception as e:
        logging.warning(f"Language detection error: {e}")
        # 回退到 langdetect
        try:
            import langdetect
            detected = langdetect.detect(text)
            if detected in SUPPORTED_LANGUAGES:
                return detected
            else:
                return 'en'
        except:
            return 'en'  # 最终回退到英语


# def translate_text(text: str, target_lang: str, source_lang: str = 'auto') -> str:
#     """Translate text to target language"""
#     try:
#         if source_lang == target_lang:
#             return text
#
#         result = translator.translate(text, src=source_lang, dest=target_lang)
#         return result.text
#     except Exception as e:
#         print(f"Translation error: {e}")
#         return text
#
# def extract_entities_multilingual(text: str, language: str) -> List[str]:
#     """Extract named entities from text in multiple languages"""
#     entities = []
#
#     if language in nlp_models:
#         try:
#             doc = nlp_models[language](text)
#             entities = [ent.text for ent in doc.ents if ent.label_ in ['ORG', 'PERSON', 'GPE']]
#         except Exception as e:
#             print(f"Entity extraction error for {language}: {e}")
#
#     return entities


def translate_text(text: str, target_lang: str, source_lang: str = 'auto') -> str:
    """使用 deep-translator 翻译文本"""
    try:
        if source_lang == target_lang:
            return text

        # 处理 'auto' 源语言
        if source_lang == 'auto':
            source_lang = 'auto'

        # 创建翻译器实例
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        result = translator.translate(text)
        return result

    except Exception as e:
        logging.warning(f"Translation error: {e}")
        # 回退策略：返回原文
        return text

# 批量翻译功能
def translate_texts_batch(texts: list, target_lang: str, source_lang: str = 'auto') -> list:
    """批量翻译文本"""
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        results = []

        for text in texts:
            try:
                result = translator.translate(text)
                results.append(result)
            except Exception as e:
                logging.warning(f"Failed to translate text: {text[:50]}... Error: {e}")
                results.append(text)  # 失败时返回原文

        return results

    except Exception as e:
        logging.error(f"Batch translation error: {e}")
        return texts  # 失败时返回原文列表

def is_greenwashing_keyword_present(text: str, language: str) -> bool:
    """Check if greenwashing keywords are present in the text"""
    keywords = GREENWASHING_KEYWORDS.get(language, GREENWASHING_KEYWORDS['en'])
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in keywords)

# Enhanced LangGraph State Definition
class ESGAnalysisState(TypedDict):
    company_name: str
    vector_store: Any
    detected_language: str
    original_text: str
    translated_text: str
    initial_thoughts: List[str]
    selected_thoughts: List[str]
    document_analysis: str
    news_validation: str
    metrics: str
    final_synthesis: str
    iteration: int
    max_iterations: int
    error: Optional[str]

# Initialize LangChain components with updated parameters
llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-07-01-preview",
    azure_deployment="gpt-4o-mini",
    temperature=0.1,
    streaming=True,
    callback_manager=CallbackManager([StreamingStdOutCallbackHandler()])
)

# Updated embedding model initialization
embedding_model = AzureOpenAIEmbeddings(
    azure_endpoint=AZURE_OPENAI_ENDPOINT_2,
    api_key=AZURE_OPENAI_API_KEY_2,
    api_version="2023-05-15",
    azure_deployment="text-embedding-3-large",
    chunk_size=100
)

# Initialize multilingual ClimateBERT models
climatebert_models = {}
climatebert_tokenizers = {}

# Try to load multilingual climate models
model_names = {
    'en': "climatebert/distilroberta-base-climate-f",
    'de': "climatebert/distilroberta-base-climate-f",  # Can be adapted for German
    'it': "climatebert/distilroberta-base-climate-f"   # Can be adapted for Italian
}

for lang, model_name in model_names.items():
    try:
        climatebert_tokenizers[lang] = AutoTokenizer.from_pretrained(
            model_name, local_files_only=False
        )
        climatebert_models[lang] = AutoModelForSequenceClassification.from_pretrained(
            model_name, local_files_only=False
        )
    except Exception as e:
        print(f"Warning: Could not load ClimateBERT model for {lang}: {e}")
        climatebert_tokenizers[lang] = None
        climatebert_models[lang] = None

# Enhanced text splitter with language support
def create_text_splitter(language: str) -> RecursiveCharacterTextSplitter:
    """Create language-specific text splitter"""
    separators = {
        'en': ["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        'de': ["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        'it': ["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    }
    
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=separators.get(language, separators['en'])
    )

# Global storage for document stores and agents
document_stores: Dict[str, Chroma] = {}
agent_executors: Dict[str, AgentExecutor] = {}
memories: Dict[str, ConversationBufferWindowMemory] = {}

# Enhanced Custom Tools with multilingual support
class MultilingualESGDocumentAnalysisTool(BaseTool):
    name: str = "multilingual_esg_document_analysis"
    description: str = "Analyzes ESG documents for greenwashing indicators in multiple languages using vector search and semantic analysis"
    vector_store: Any = None
    language: str = 'en'

    def __init__(self, vector_store: Chroma, language: str = 'en'):
        super().__init__()
        self.vector_store = vector_store
        self.language = language

    def _run(self, query: str) -> str:
        """Execute the multilingual document analysis"""
        try:
            # Semantic search for relevant documents
            docs = self.vector_store.similarity_search(query, k=10)

            # Combine document content
            context = "\n\n".join([doc.page_content for doc in docs])

            # Get language-specific analysis prompt
            analysis_template = ANALYSIS_PROMPTS.get(self.language, ANALYSIS_PROMPTS['en'])['greenwashing_analysis']
            analysis_prompt = analysis_template.format(content=context)

            # Add language-specific instruction
            language_instruction = f"Analyze in {SUPPORTED_LANGUAGES[self.language]}. "
            if self.language != 'en':
                language_instruction += f"Provide analysis in {SUPPORTED_LANGUAGES[self.language]} language. "
            
            full_prompt = language_instruction + analysis_prompt

            response = llm.invoke([HumanMessage(content=full_prompt)])
            return response.content

        except Exception as e:
            return f"Error in multilingual document analysis: {str(e)}"

class MultilingualNewsValidationTool(BaseTool):
    name: str = "multilingual_news_validation"
    description: str = "Validates ESG claims against recent news articles from credible sources in multiple languages"
    company_name: str = ""
    language: str = 'en'

    def __init__(self, company_name: str, language: str = 'en'):
        super().__init__()
        self.company_name = company_name
        self.language = language

    def _run(self, claims: str) -> str:
        """Validate claims against news sources with multilingual support"""
        try:
            # Search for news articles (existing functionality)
            bbc_articles = bbc_search(self.company_name)
            cnn_articles = cnn_search(self.company_name)

            news_content = []

            # Process articles (existing functionality)
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

            # Combine news content
            news_text = "\n\n".join(news_content[:5])

            # Create multilingual validation prompt
            validation_prompt = self._create_validation_prompt(claims, news_text)

            response = llm.invoke([HumanMessage(content=validation_prompt)])
            return response.content

        except Exception as e:
            return f"Error in multilingual news validation: {str(e)}"

    def _get_no_news_message(self) -> str:
        """Get no news message in appropriate language"""
        messages = {
            'en': "No recent news articles found for validation",
            'de': "Keine aktuellen Nachrichtenartikel zur Validierung gefunden",
            'it': "Nessun articolo di notizie recenti trovato per la validazione"
        }
        return messages.get(self.language, messages['en'])

    def _create_validation_prompt(self, claims: str, news_text: str) -> str:
        """Create language-specific validation prompt"""
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

    def __init__(self, language: str = 'en'):
        super().__init__()
        self.language = language

    def _run(self, analysis_text: str) -> str:
        """Calculate ESG metrics from analysis with multilingual support"""
        try:
            # Get language-specific metrics prompt
            metrics_template = ANALYSIS_PROMPTS.get(self.language, ANALYSIS_PROMPTS['en'])['metrics_calculation']
            metrics_prompt = metrics_template.format(analysis=analysis_text)

            # Add language-specific instruction
            language_instruction = f"Provide analysis in {SUPPORTED_LANGUAGES[self.language]}. "
            full_prompt = language_instruction + metrics_prompt

            response = llm.invoke([HumanMessage(content=full_prompt)])
            return response.content

        except Exception as e:
            return f"Error calculating multilingual metrics: {str(e)}"

# Enhanced utility functions
def is_esg_related_multilingual(text: str, language: str, threshold: float = 0.5) -> bool:
    """Use multilingual ClimateBERT to determine if text is ESG-related"""
    # First check with language-specific keywords
    if is_greenwashing_keyword_present(text, language):
        return True
    
    # Then try with model if available
    if climatebert_tokenizers.get(language) and climatebert_models.get(language):
        try:
            tokenizer = climatebert_tokenizers[language]
            model = climatebert_models[language]
            
            inputs = tokenizer(
                text, return_tensors="pt", truncation=True, padding=True, max_length=512
            )
            
            with torch.no_grad():
                outputs = model(**inputs)
            
            probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
            esg_prob = probabilities[0][1].item()
            return esg_prob >= threshold
        except Exception as e:
            print(f"Error in multilingual ESG classification: {e}")
    
    # Fallback to keyword-based classification
    return is_greenwashing_keyword_present(text, language)

def extract_company_info_multilingual(query: str, vector_store: Chroma, language: str) -> str:
    """Extract company information from vector store with multilingual support"""
    try:
        docs = vector_store.similarity_search(query, k=5)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Get language-specific company extraction prompt
        extraction_template = ANALYSIS_PROMPTS.get(language, ANALYSIS_PROMPTS['en'])['company_extraction']
        
        prompt = f"""
        {extraction_template}
        
        Context: {context}
        
        Query: {query}
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"Error extracting company info: {str(e)}"

# Enhanced document processing
async def process_pdf_document_multilingual(file_path: str) -> tuple[List[Document], str]:
    """Process PDF document with language detection and return chunks with detected language"""
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    # Detect language from first few documents
    sample_text = " ".join([doc.page_content for doc in documents[:3]])
    detected_language = detect_language(sample_text)
    
    # Filter ESG-related content using multilingual detection
    esg_documents = []
    for doc in documents:
        if is_esg_related_multilingual(doc.page_content, detected_language):
            esg_documents.append(doc)
    
    if not esg_documents:
        esg_documents = documents  # Fallback to all documents
    
    # Split documents using language-specific splitter
    text_splitter = create_text_splitter(detected_language)
    chunks = text_splitter.split_documents(esg_documents)
    
    return chunks, detected_language

# Enhanced LangGraph Node Functions
def generate_initial_thoughts_multilingual(state: ESGAnalysisState) -> ESGAnalysisState:
    """Generate multiple analytical thoughts for ESG analysis with multilingual support"""
    
    language = state.get("detected_language", "en")
    lang_name = SUPPORTED_LANGUAGES[language]
    
    thought_generation_prompt = f"""
    You are an expert ESG analyst tasked with identifying greenwashing in corporate reports.
    Analyze this document in {lang_name} language and generate 4 different analytical approaches to examine this ESG document for greenwashing indicators.
    
    Each approach should focus on a different aspect:
    1. Quantitative analysis of specific metrics and targets
    2. Qualitative analysis of language and claims
    3. Comparative analysis against industry standards
    4. Temporal analysis of commitments vs. achievements
    
    For each approach, provide:
    - A specific analytical question to investigate
    - The methodology to use
    - What evidence to look for
    - Potential red flags to identify
    
    Respond in {lang_name} language.
    Format your response as a JSON list of 4 analytical approaches.
    """
    
    try:
        response = llm.invoke([HumanMessage(content=thought_generation_prompt)])
        thoughts_text = response.content
        
        # Try to parse as JSON, fallback to splitting if needed
        try:
            thoughts = json.loads(thoughts_text)
            if isinstance(thoughts, list):
                state["initial_thoughts"] = thoughts
            else:
                state["initial_thoughts"] = thoughts_text.split('\n\n')
        except json.JSONDecodeError:
            state["initial_thoughts"] = thoughts_text.split('\n\n')
            
        return state
        
    except Exception as e:
        state["error"] = f"Error generating multilingual thoughts: {str(e)}"
        return state

# Enhanced comprehensive analysis function
async def comprehensive_esg_analysis_multilingual(
    session_id: str, 
    vector_store: Chroma, 
    company_name: str, 
    language: str
) -> Dict[str, Any]:
    """Execute comprehensive ESG analysis with multilingual support"""
    
    try:
        # Create multilingual tools
        analysis_tool = MultilingualESGDocumentAnalysisTool(vector_store, language)
        news_tool = MultilingualNewsValidationTool(company_name, language)
        metrics_tool = MultilingualESGMetricsCalculatorTool(language)
        
        # Perform document analysis
        document_analysis = analysis_tool._run(
            f"Perform detailed ESG analysis in {SUPPORTED_LANGUAGES[language]} language"
        )
        
        # Perform news validation if company is valid
        if company_name.lower() in VALID_COMPANIES:
            news_validation = news_tool._run(document_analysis)
        else:
            no_validation_msg = {
                'en': "Company name not recognized. News validation skipped.",
                'de': "Firmenname nicht erkannt. Nachrichtenvalidierung übersprungen.",
                'it': "Nome dell'azienda non riconosciuto. Validazione notizie saltata."
            }
            news_validation = no_validation_msg.get(language, no_validation_msg['en'])
        
        # Calculate metrics
        metrics_calculation = metrics_tool._run(
            f"Document Analysis: {document_analysis}\nNews Validation: {news_validation}"
        )
        
        # Create final synthesis
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

# Enhanced FastAPI endpoints
app = FastAPI(title="Multilingual ESG Greenwashing Analysis API", root_path="/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.post("/upload")
async def upload_document_multilingual(
    file: Annotated[UploadFile, File()], 
    session_id: Annotated[str, Form()]
) -> Dict[str, Any]:
    """Upload and analyze ESG document with multilingual support"""
    
    if file.content_type not in VALID_UPLOAD_TYPES:
        raise HTTPException(status_code=400, detail="Invalid content type")
    
    # Save file
    file_b = await file.read()
    file_hash = hash_file(file_b)
    
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{file_hash}.pdf"
    
    with file_path.open("wb") as f:
        f.write(file_b)
    
    try:
        # Process document with language detection
        chunks, detected_language = await process_pdf_document_multilingual(str(file_path))
        
        # Create vector store
        vector_store = Chroma.from_documents(chunks, embedding_model)
        document_stores[session_id] = vector_store
        
        # Extract company name with multilingual support
        company_query_templates = {
            'en': "What is the name of the company that published this report?",
            'de': "Wie heißt das Unternehmen, das diesen Bericht veröffentlicht hat?",
            'it': "Qual è il nome dell'azienda che ha pubblicato questo rapporto?"
        }
        
        company_query = company_query_templates.get(detected_language, company_query_templates['en'])
        company_name = extract_company_info_multilingual(company_query, vector_store, detected_language)
        
        # Execute comprehensive multilingual analysis
        analysis_results = await comprehensive_esg_analysis_multilingual(
            session_id, vector_store, company_name, detected_language
        )
        
        # Clean up
        file_path.unlink(missing_ok=True)
        
        return {
            "filename": file_path.name,
            "company_name": company_name,
            "detected_language": detected_language,
            "language_name": SUPPORTED_LANGUAGES[detected_language],
            "session_id": session_id,
            "response": analysis_results["final_synthesis"],
            "initial_analysis": analysis_results["initial_analysis"],
            "document_analysis": analysis_results["document_analysis"],
            "news_validation": analysis_results["news_validation"],
            "graphdata": analysis_results["metrics"],
            "comprehensive_analysis": analysis_results["comprehensive_analysis"],
            "validation_complete": True,
            "filenames": ["bbc_articles", "cnn_articles"] if company_name.lower() in VALID_COMPANIES else None,
            "workflow_error": analysis_results.get("error"),
            "supported_languages": SUPPORTED_LANGUAGES
        }
        
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/chat")
async def chat_with_agent_multilingual(json_data: ChatBaseMessage) -> StreamingResponse:
    """Chat with the ESG analysis agent with multilingual support"""
    
    user_message = json_data.message
    session_id = json_data.session_id
    
    # Get stored information
    vector_store = document_stores.get(session_id)
    if not vector_store:
        raise HTTPException(status_code=400, detail="No analysis session found")
    
    # Detect language of user message
    message_language = detect_language(user_message)
    
    # Get or create agent with multilingual support
    agent = agent_executors.get(session_id)
    if not agent:
        # Create new multilingual agent
        agent = create_multilingual_esg_agent(session_id, vector_store, message_language)
        agent_executors[session_id] = agent
    
    # Create streaming response
    async def generate_response():
        try:
            # Add language context to the message
            contextualized_message = f"""
            User language: {SUPPORTED_LANGUAGES.get(message_language, 'English')}
            Please respond in {SUPPORTED_LANGUAGES.get(message_language, 'English')}.
            
            User message: {user_message}
            """
            
            # Use agent to respond
            response = agent.run(contextualized_message)
            
            # Stream the response
            words = response.split()
            for i, word in enumerate(words):
                yield f"data: {word}"
                if i < len(words) - 1:
                    yield f" "
                await asyncio.sleep(0.01)  # Small delay for streaming effect
                
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    )

@app.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "supported_languages": SUPPORTED_LANGUAGES,
        "default_language": "en"
    }

@app.post("/translate")
async def translate_analysis(
    text: Annotated[str, Form()],
    target_language: Annotated[str, Form()],
    source_language: Annotated[str, Form()] = "auto"
):
    """Translate analysis results to different languages"""
    
    if target_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported target language. Supported: {list(SUPPORTED_LANGUAGES.keys())}"
        )
    
    try:
        translated_text = translate_text(text, target_language, source_language)
        return {
            "original_text": text,
            "translated_text": translated_text,
            "source_language": source_language,
            "target_language": target_language,
            "target_language_name": SUPPORTED_LANGUAGES[target_language]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")

def create_multilingual_esg_agent(session_id: str, vector_store: Chroma, language: str) -> AgentExecutor:
    """Create a multilingual ReAct agent for ESG analysis"""
    
    # Create multilingual tools
    tools = [
        MultilingualESGDocumentAnalysisTool(vector_store, language),
        MultilingualNewsValidationTool("", language),  # Company name will be set during analysis
        MultilingualESGMetricsCalculatorTool(language),
        Tool(
            name="multilingual_company_info_extractor",
            description=f"Extracts company information from documents in {SUPPORTED_LANGUAGES[language]}",
            func=lambda query: extract_company_info_multilingual(query, vector_store, language)
        ),
        Tool(
            name="multilingual_esg_classifier",
            description=f"Classifies text as ESG-related or not in {SUPPORTED_LANGUAGES[language]}",
            func=lambda text: str(is_esg_related_multilingual(text, language))
        ),
        Tool(
            name="language_detector",
            description="Detects the language of the input text",
            func=lambda text: f"Detected language: {detect_language(text)} ({SUPPORTED_LANGUAGES.get(detect_language(text), 'Unknown')})"
        ),
        Tool(
            name="text_translator",
            description="Translates text between supported languages",
            func=lambda text_and_lang: translate_text(
                text_and_lang.split('|')[0], 
                text_and_lang.split('|')[1] if '|' in text_and_lang else 'en'
            )
        )
    ]
    
    # Create memory with language context
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        k=10,
        return_messages=True
    )
    memories[session_id] = memory
    
    # Create language-specific system message
    system_messages = {
        'en': "You are an expert ESG analyst specialized in identifying greenwashing. Respond in English.",
        'de': "Sie sind ein ESG-Experte, spezialisiert auf die Identifizierung von Greenwashing. Antworten Sie auf Deutsch.",
        'it': "Sei un esperto ESG specializzato nell'identificazione del greenwashing. Rispondi in italiano."
    }
    
    system_message = system_messages.get(language, system_messages['en'])
    
    # Enhanced agent prompt with multilingual support
    agent_prompt = f"""
    {system_message}
    
    You have access to multilingual ESG analysis tools. Use them to:
    1. Analyze ESG documents for greenwashing indicators
    2. Validate claims against news sources
    3. Calculate greenwashing metrics
    4. Extract company information
    5. Classify ESG-related content
    6. Detect languages and translate when needed
    
    Always consider cultural and linguistic nuances when analyzing documents in different languages.
    Pay attention to language-specific greenwashing indicators and terminology.
    
    Current analysis language: {SUPPORTED_LANGUAGES[language]}
    """
    
    # Initialize multilingual agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory,
        verbose=True,
        max_iterations=15,
        early_stopping_method="force",
        agent_kwargs={"system_message": agent_prompt}
    )
    
    return agent

# Enhanced utility function for file hashing
def hash_file(file_b: bytes) -> str:
    """Generate SHA-256 hash of file content"""
    file_hash = hashlib.sha256()
    file_hash.update(file_b)
    return file_hash.hexdigest()

# Additional language-specific analysis functions
def analyze_language_specific_greenwashing(text: str, language: str) -> Dict[str, Any]:
    """Analyze greenwashing patterns specific to different languages"""
    
    # Language-specific greenwashing patterns
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
    
    # Count occurrences of different pattern types
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
    """Extract entities from text using language-specific NLP models"""
    
    entities = {
        'organizations': [],
        'persons': [],
        'locations': [],
        'dates': [],
        'money': []
    }
    
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
            print(f"Entity extraction error for {language}: {e}")
    
    return entities

# Add language-specific validation endpoint
@app.post("/validate_language")
async def validate_language_specific_claims(
    text: Annotated[str, Form()],
    language: Annotated[str, Form()],
    session_id: Annotated[str, Form()]
):
    """Validate language-specific greenwashing claims"""
    
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language. Supported: {list(SUPPORTED_LANGUAGES.keys())}"
        )
    
    try:
        # Analyze language-specific greenwashing patterns
        greenwashing_analysis = analyze_language_specific_greenwashing(text, language)
        
        # Extract entities
        entities = extract_multilingual_entities(text, language)
        
        # Get vector store for additional context
        vector_store = document_stores.get(session_id)
        additional_context = ""
        
        if vector_store:
            # Search for related content in the document
            related_docs = vector_store.similarity_search(text[:500], k=3)
            additional_context = "\n".join([doc.page_content for doc in related_docs])
        
        return {
            "input_text": text,
            "language": language,
            "language_name": SUPPORTED_LANGUAGES[language],
            "greenwashing_analysis": greenwashing_analysis,
            "extracted_entities": entities,
            "additional_context_found": bool(additional_context),
            "session_id": session_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")

# Import asyncio for streaming
import asyncio

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)