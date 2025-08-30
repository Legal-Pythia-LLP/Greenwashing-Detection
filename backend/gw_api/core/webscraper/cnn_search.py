import os
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict
from app.config import DOWNLOADS_PATH

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests


def date_calculation(delta: int) -> datetime:
    current_date = datetime.now()
    return current_date - timedelta(days=delta)


def url_validity(url: str) -> bool:
    return not any(x in url for x in ["videos", "live", "shows"])


def date_conversion(date: str) -> datetime:
    components = date.split(" ")
    if len(components) == 3 and components[2] == "ago":
        return datetime.now() - timedelta(hours=int(components[0]))
    else:
        month = datetime.strptime(components[1], "%B").month
        if len(components) == 2:
            return datetime(datetime.now().year, month, int(components[0]))
        else:
            return datetime(int(components[2]), month, int(components[0]))


def url_download(links: dict, directory: str = "downloads") -> Dict[str, str]:
    os.makedirs(directory, exist_ok=True)
    downloads_dictionary = {}

    for title, url in links.items():
        safe_title = "".join(char for char in title if char.isalnum()) or "article"
        title_hash = hashlib.md5(title.encode("utf-8")).hexdigest()[:8]
        filename = f"{safe_title[:50]}_{title_hash}.html"
        path = os.path.join(directory, filename)

        if os.path.exists(path):
            downloads_dictionary[title] = path
            continue

        try:
            response = requests.get(url, timeout=10)
            with open(path, "w", encoding="utf-8") as f:
                f.write(response.text)
            downloads_dictionary[title] = path
        except Exception as e:
            print(f"[ERROR] Failed to download {url}: {e}")

    return downloads_dictionary


def cnn_search(name: str) -> Dict[str, str]:
    """
    Use Selenium to crawl CNN search results, download, and return local paths.
    """
    depth = 20
    delta = 365 * 2
    last_date = date_calculation(delta)
    web_dictionary = {}
    page_count = 1

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    while True:
        url = f"https://www.cnn.com/search?q={name}&size=10&page={page_count}"
        driver.get(url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.container__headline"))
            )
        except:
            print(f"[DEBUG] No articles on CNN page {page_count}, ending")
            break

        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select("div.container__headline")

        if not cards:
            print(f"[DEBUG] No articles on CNN page {page_count}, ending")
            break

        for card in cards:
            a_tag = card.find("a")
            title = a_tag.get_text(strip=True) if a_tag else None
            link = a_tag["href"] if a_tag and a_tag.has_attr("href") else None

            date_tag = card.find_next("div", class_="container__date")
            article_date = date_tag.get_text(strip=True) if date_tag else None

            if not title or not link or not article_date:
                continue

            try:
                date = date_conversion(article_date)
            except:
                continue

            if url_validity(link) and len(web_dictionary) < depth and date >= last_date:
                if link.startswith("/"):
                    link = "https://www.cnn.com" + link
                web_dictionary[title] = link

            if len(web_dictionary) >= depth:
                break

        if len(web_dictionary) >= depth or page_count >= 20:
            break
        page_count += 1

    driver.quit()

    if web_dictionary:
        print(f"[DEBUG] Number of CNN articles crawled: {len(web_dictionary)}")
        for i, title in enumerate(web_dictionary.keys(), 1):
            print(f"  [CNN] {title}")
        return url_download(web_dictionary, DOWNLOADS_PATH)
    else:
        print("[DEBUG] No qualifying CNN articles found")
        return None
