import hashlib
from typing import Any
from app.core.llm import climatebert_tokenizer, climatebert_model

# 一段文本是否与esg相关

def hash_file(file_b) -> str:
    """Generate SHA-256 hash of file content"""
    file_hash = hashlib.sha256()
    file_hash.update(file_b)
    return file_hash.hexdigest()

# is_esg_related 依赖 climatebert_tokenizer, climatebert_model, torch
# 需要在主程序中 import 这几个变量

def is_esg_related(text: str, threshold: float = 0.5) -> bool:
    """Use ClimateBERT to determine if text is ESG-related"""
    import torch
    if climatebert_tokenizer is None or climatebert_model is None:
        esg_keywords = ['esg', 'environment', 'sustainability', 'carbon', 'emission', 'governance', 'social']
        return any(keyword in text.lower() for keyword in esg_keywords)
    try:
        inputs = climatebert_tokenizer(
            text, return_tensors="pt", truncation=True, padding=True, max_length=512
        )
        with torch.no_grad():
            outputs = climatebert_model(**inputs)
        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
        esg_prob = probabilities[0][1].item()
        return esg_prob >= threshold
    except Exception as e:
        print(f"Error in ESG classification: {e}")
        esg_keywords = ['esg', 'environment', 'sustainability', 'carbon', 'emission', 'governance', 'social']
        return any(keyword in text.lower() for keyword in esg_keywords) 