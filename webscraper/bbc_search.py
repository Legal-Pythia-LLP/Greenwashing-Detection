import os
import shutil
import hashlib
from datetime import datetime, timedelta
from typing import Dict
import requests
from bs4 import BeautifulSoup


def date_calculation(delta: int) -> datetime:
    """
    计算距离当前日期 delta 天的日期，用于新闻爬虫的时间范围。
    """
    current_date = datetime.now()
    from_date = current_date - timedelta(days=delta)
    return from_date


def url_download(links: dict, directory: str = "downloads") -> Dict[str, str]:
    """
    下载所有链接到本地目录，返回标题到本地文件路径的映射。
    会自动处理文件名重复、非法字符问题，避免每次清空目录。
    """
    os.makedirs(directory, exist_ok=True)
    downloads_dictionary = {}

    try:
        for title, url in links.items():
            # 标题转安全文件名 + 唯一哈希
            safe_title = "".join(char for char in title if char.isalnum())
            if not safe_title:
                safe_title = "article"
            title_hash = hashlib.md5(title.encode("utf-8")).hexdigest()[:8]
            filename = f"{safe_title[:50]}_{title_hash}.html"
            path = os.path.join(directory, filename)

            # 避免重复下载
            if os.path.exists(path):
                downloads_dictionary[title] = path
                continue

            response = requests.get(url, timeout=10)
            with open(path, "w", encoding="utf-8") as f:
                f.write(response.text)

            downloads_dictionary[title] = path

    except requests.exceptions.RequestException as e:
        raise Exception(f"Request failed: {e}")
    except OSError as e:
        raise Exception(f"File saving error: {e}")

    return downloads_dictionary


def url_validity(url: str) -> bool:
    """
    判断URL是否为新闻/文章类型。
    """
    return "articles" in url or "news" in url


def date_conversion(date: str) -> datetime:
    """
    将爬取到的日期字符串转换为 datetime 类型。
    """
    components = date.split(" ")
    if len(components) == 3 and components[2] == "ago":  # e.g. ['8','hours','ago]
        if components[1] == "hours":
            return datetime.now() - timedelta(hours=int(components[0]))
        else:
            return datetime.now() - timedelta(hours=int(components[0]))
    else:
        month = datetime.strptime(components[1], "%B").month
        if len(components) == 2:  # e.g. ['30','October']
            return datetime(datetime.now().year, month, int(components[0]))
        else:  # e.g. #['30','October','2021']
            return datetime(int(components[2]), month, int(components[0]))


def bbc_search(name: str) -> Dict[str, str]:
    """
    BBC 新闻爬虫，搜索与 name 相关的新闻，下载并返回本地路径。
    """
    depth = 10
    delta = 365 * 2
    last_date = date_calculation(delta)
    web_dictionary = {}
    page_count = 1
    next_page = True
    limit = False

    while next_page:
        source = f"https://www.bbc.co.uk/search?q={name}&d=NEWS_PS&page={page_count}"
        response = requests.get(source)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        promo_articles = soup.find_all("div", attrs={"data-testid": "default-promo"})

        if not promo_articles:
            break

        for article in promo_articles:
            title_struct = article.find("p")
            if not title_struct:
                continue
            title = title_struct.get_text(strip=True)
            a_tag = article.find("a")
            if not a_tag:
                continue
            link = a_tag.get("href")
            if not link:
                continue
            container = article.find("ul")
            if not container:
                continue
            article_date = container.find("span").text
            if not article_date:
                continue

            try:
                date = date_conversion(article_date)
            except:
                continue

            size = len(web_dictionary) + 1 <= depth
            if url_validity(link) and size and date >= last_date:
                web_dictionary[title] = link
            elif not size:
                limit = True
                break

        if limit:
            next_page = False
        else:
            page_count += 1
   
            if page_count > 10:
                break

    if len(web_dictionary) != 0:
        return url_download(web_dictionary)
    else:
        return None
