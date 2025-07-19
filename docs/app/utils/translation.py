import logging
from deep_translator import GoogleTranslator
from app.config import SUPPORTED_LANGUAGES

def translate_text(text: str, target_lang: str, source_lang: str = 'auto') -> str:
    """
    使用 deep-translator 翻译文本。
    """
    try:
        if source_lang == target_lang:
            return text
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        return translator.translate(text)
    except Exception as e:
        logging.warning(f"Translation error: {e}")
        return text

def translate_texts_batch(texts: list, target_lang: str, source_lang: str = 'auto') -> list:
    """
    批量翻译文本。
    """
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        results = []
        for text in texts:
            try:
                result = translator.translate(text)
                results.append(result)
            except Exception as e:
                logging.warning(f"Failed to translate text: {text[:50]}... Error: {e}")
                results.append(text)
        return results
    except Exception as e:
        logging.error(f"Batch translation error: {e}")
        return texts 