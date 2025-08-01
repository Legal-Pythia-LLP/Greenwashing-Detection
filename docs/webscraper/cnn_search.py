import os
import re
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


def cnn_search(name: str) -> Dict[str, str]:
    """
    CNN 新闻爬虫，搜索与 name 相关的新闻，下载并返回本地路径。
    """
    depth = 10
    delta = 365 * 2
    last_date = date_calculation(delta)
    web_dictionary = {}
    page_count = 1
    next_page = True
    limit = False
    while next_page:
        source = f"https://www.cnn.com/search?q={name}&size=10&page={page_count}"
        response = requests.get(source)
        if page_count > 29:
            break
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all(
            "div",
            attrs={"data-uri": re.compile(r"^/_components/card/instances/search-")},
        )
        if not articles:
            break
        for article in articles:
            title_struct = article.find("span", class_="container__headline-text")
            if not title_struct:
                continue
            title = title_struct.get_text(strip=True)
            a_tag = article.find("a")
            if not a_tag:
                continue
            link = a_tag.get("href")
            if not link:
                continue
            date_struct = article.find("div", class_="container__date")
            if not date_struct:
                continue
            article_date = date_struct.get_text(strip=True)
            if not article_date:
                continue
            try:
                date = date_conversion(article_date)
            except:
                continue  # Skips the unnecessary part of the code
            size = len(web_dictionary) + 1 <= depth
            if url_validity(link) and size and date >= last_date:
                web_dictionary[title] = link
            elif not size:
                limit = True
                break
        if limit:  # checks if we have reached the 10 page limit, speeding up runtime
            next_page = False
        else:
            page_count += 1
    local_file_dict = {}
    if len(web_dictionary) != 0:
        local_file_dict = url_download(web_dictionary)
        return local_file_dict
    else:
        return None 