import hashlib
from typing import Any
from app.core.llm import climatebert_tokenizer, climatebert_model
from typing import List, Dict
from app.core.llm import llm
import re
from webscraper.bbc_search import bbc_search
from webscraper.cnn_search import cnn_search
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain.schema import HumanMessage



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
    
def search_and_filter_news(company_name: str, max_articles: int = 5) -> List[str]:
    """
    根据公司名搜索相关新闻（使用别名），并过滤掉不相关内容。

    返回：过滤后的新闻文本列表
    """
    def generate_company_aliases(company_name: str) -> list:
        """
        给定正式公司名，生成安全、相关的别名组合，用于搜索新闻时避免误匹配。
        """
        aliases = set()
        aliases.add(company_name.strip())

        # 常见无意义后缀词，全部剔除
        blacklist = {'co', 'inc', 'ltd', 'limited', 'corporation', 'corp', 'group', 'plc', 'llc', 'holdings', 'company'}

        # 去掉标点和后缀
        simplified = re.sub(r'\b(?:' + '|'.join(blacklist) + r')\b\.?', '', company_name, flags=re.I)
        simplified = re.sub(r'[^a-zA-Z0-9\s]', '', simplified)  # 去标点
        simplified = re.sub(r'\s+', ' ', simplified).strip()
        aliases.add(simplified)

        # 拆分词组并做长度/黑名单过滤
        parts = simplified.split()
        for p in parts:
            p_clean = p.strip().lower()
            if len(p_clean) < 4:  # 太短的词排除
                continue
            if p_clean in blacklist:
                continue
            aliases.add(p.strip())

        # 排除太泛的词
        risky_terms = {'chase', 'co', 'bank', 'group', 'partners'}
        aliases = {a for a in aliases if a.lower() not in risky_terms}

        return sorted(aliases)

    def is_article_about_company(text: str, company_name: str, aliases: list) -> bool:
        prompt = f"""
        判断以下文章是否与公司 "{company_name}" 或其别名 {aliases} 有直接关系。

        文章内容：
        {text[:1200]}

        请只回答 YES 或 NO。
        """
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            return "YES" in response.content.upper()
        except Exception as e:
            print(f"[LLM error when checking article relevance]: {e}")
            return False

    aliases = generate_company_aliases(company_name)
    print(f"[DEBUG] 使用以下别名搜索新闻: {aliases}")

    bbc_articles, cnn_articles = {}, {}

    for alias in aliases:
        try:
            results = bbc_search(alias)
            if results:
                bbc_articles.update(results)
        except Exception as e:
            print(f"[BBC error with alias '{alias}']: {e}")
        try:
            results = cnn_search(alias)
            if results:
                cnn_articles.update(results)
        except Exception as e:
            print(f"[CNN error with alias '{alias}']: {e}")

    all_articles = list((bbc_articles or {}).items()) + list((cnn_articles or {}).items())
    news_content = []

    for title, file_path in all_articles:
        try:
            loader = UnstructuredHTMLLoader(file_path)
            docs = loader.load()
            for doc in docs:
                if is_article_about_company(doc.page_content, company_name, aliases):
                    news_content.append(doc.page_content)
                    if len(news_content) >= max_articles:
                        return news_content
        except Exception as e:
            print(f"[Error loading article {title}]: {e}")

    return news_content