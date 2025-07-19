import logging
from langdetect import detect
from app.config import SUPPORTED_LANGUAGES, GREENWASHING_KEYWORDS

def detect_language(text: str) -> str:
    """
    检测文本语言，优先用 langdetect，失败回退英文。
    """
    try:
        detected = detect(text)
        if detected in SUPPORTED_LANGUAGES:
            return detected
        else:
            return 'en'
    except Exception as e:
        logging.warning(f"Language detection error: {e}")
        return 'en'

def is_greenwashing_keyword_present(text: str, language: str) -> bool:
    """
    判断文本中是否包含绿洗关键词。
    """
    keywords = GREENWASHING_KEYWORDS.get(language, GREENWASHING_KEYWORDS['en'])
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in keywords)

def analyze_language_specific_greenwashing(text: str, language: str) -> dict:
    """
    语言特定绿洗分析，统计模糊词、无依据声明、误导前缀等出现次数。
    """
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

def extract_multilingual_entities(text: str, language: str) -> dict:
    """
    多语言实体抽取，返回组织、人名、地名、时间、金额等。
    """
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
        nlp_models['en'] = spacy.load("en_core_web_sm")
        nlp_models['de'] = spacy.load("de_core_news_sm")
        nlp_models['it'] = spacy.load("it_core_news_sm")
    except OSError as e:
        logging.warning(f"spaCy models not installed: {e}")
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

def is_esg_related_multilingual(text: str, language: str, threshold: float = 0.5) -> bool:
    """
    判断文本是否与ESG相关，先关键词，后可扩展模型。
    """
    # 这里只实现关键词判别，后续可在服务层扩展BERT模型
    return is_greenwashing_keyword_present(text, language) 