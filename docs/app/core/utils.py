import hashlib
from typing import Any, List, Tuple
from app.core.llm import climatebert_tokenizer, climatebert_model, llm
import re
from webscraper.bbc_search import bbc_search
from webscraper.cnn_search import cnn_search
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain.schema import HumanMessage


def hash_file(file_b) -> str:
    """Generate SHA-256 hash of file content"""
    file_hash = hashlib.sha256()
    file_hash.update(file_b)
    return file_hash.hexdigest()


def is_esg_related(text: str, threshold: float = 0.5) -> bool:
    """Use ClimateBERT to determine if text is ESG-related"""
    import torch
    if climatebert_tokenizer is None or climatebert_model is None:
        esg_keywords = ['esg', 'environment', 'sustainability', 'carbon', 'emission',
                        'governance', 'social', 'net zero', 'decarbon', 'climate', 'renewable']
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
        esg_keywords = ['esg', 'environment', 'sustainability', 'carbon', 'emission',
                        'governance', 'social', 'net zero', 'decarbon', 'climate', 'renewable']
        return any(keyword in text.lower() for keyword in esg_keywords)


def generate_company_aliases(company_name: str) -> list:
    aliases = set()
    aliases.add(company_name.strip())
    blacklist = {'co', 'inc', 'ltd', 'limited', 'corporation', 'corp',
                 'group', 'plc', 'llc', 'holdings', 'company'}
    simplified = re.sub(r'\b(?:' + '|'.join(blacklist) + r')\b\.?', '', company_name, flags=re.I)
    simplified = re.sub(r'[^a-zA-Z0-9\s]', '', simplified)
    simplified = re.sub(r'\s+', ' ', simplified).strip()
    aliases.add(simplified)
    parts = simplified.split()
    for p in parts:
        p_clean = p.strip().lower()
        if len(p_clean) < 4:
            continue
        if p_clean in blacklist:
            continue
        aliases.add(p.strip())
    risky_terms = {'chase', 'co', 'bank', 'group', 'partners'}
    aliases = {a for a in aliases if a.lower() not in risky_terms}
    return sorted(aliases)

def is_esg_related_llm(text: str) -> bool:
    """
    Use LLM to determine whether the text is related to ESG/sustainability/climate/governance topics.
    """
    prompt = f"""
    Determine whether the following article is related to ESG (Environmental, Social, and Governance), sustainability, climate change, carbon emissions, energy transition, green finance, or relevant policy issues.

    Article content:
    {text[:1200]}

    If the article is thematically related to ESG, respond with YES. Otherwise, respond with NO.
    """
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return "YES" in response.content.upper()
    except Exception as e:
        print(f"[LLM ESG classification failed]: {e}")
        return False

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


def search_and_filter_news(company_name: str, max_articles: int = 5) -> Tuple[List[str], List[str]]:
    """
    搜索相关新闻，筛选与公司和 ESG 相关的内容，返回最多 max_articles 篇
    """
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
    print(f"[DEBUG] 抓取到 BBC 文章数量: {len(bbc_articles)}")
    for title in bbc_articles:
        print(f"  [BBC] {title}")

    print(f"[DEBUG] 抓取到 CNN 文章数量: {len(cnn_articles)}")
    for title in cnn_articles:
        print(f"  [CNN] {title}")
    filtered_articles = []

    

    for title, file_path in all_articles[:100]:  # 最多评估前100篇
        try:
            loader = UnstructuredHTMLLoader(file_path)
            docs = loader.load()
            for doc in docs:
                is_company = is_article_about_company(doc.page_content, company_name, aliases)
                is_esg = is_esg_related_llm(doc.page_content)

                if is_company and is_esg:
                    print(f"[✅ 保留] {title} 👉 公司匹配: YES, ESG相关: YES")
                    filtered_articles.append((doc.page_content, title))
                else:
                    print(f"[❌ 剔除] {title} 👉 公司匹配: {'YES' if is_company else 'NO'}, ESG相关: {'YES' if is_esg else 'NO'}")

        except Exception as e:
            print(f"[⚠️ Error loading article: {title}]: {e}")

    # 只取前 N 篇用于后续分析
    top_articles = filtered_articles[:max_articles]
    news_content = [item[0] for item in top_articles]
    used_titles = [item[1] for item in top_articles]

    return news_content, used_titles

