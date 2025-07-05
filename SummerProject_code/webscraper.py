import os
import re
import shutil
from datetime import datetime, timedelta
from typing import Dict

import requests
from bs4 import BeautifulSoup


def date_calculation(delta: int) -> datetime:
    """
    Calculates the exact time 'delta' from the current date
    Args:
        delta (int): an integer indicating the furthest amount of time the scraper should look back on
    Returns:
        from (datetime): datetime value representing the last valid date an article can be scraped
    """

    current_date = datetime.now()
    from_date = current_date - timedelta(days=delta)

    return from_date


def url_download(links: dict, directory: str = "downloads") -> Dict[str, str]:
    """
    Creates a brand new directory containing the downloaded articles in html format with the correct title that is given by the bbc_search function
    Args:
        links (dict): a dictionary containing all the urls that should be accessed and downloaded
        directory (str): predefined string with the name for the directory containing the downloaded articles
    Returns:
        downloads_dictionary: dictionary containing all the article titles and their path so it can be accessed by the llama parser
    Raises:
        RequestException: If we cannot access the file with the link provided by links
        OsError: If the files fail to download in the required directory
    """

    if os.path.isdir(directory):
        shutil.rmtree(directory)
        print(f"Directory '{directory}' has been deleted.")

    os.makedirs(directory, exist_ok=True)

    downloads_dictionary = {}

    try:
        for title, url in links.items():
            # remove special characters
            new_title = "".join(char for char in title if char.isalnum())

            path = os.path.join(directory, f"{new_title}.html")

            response = requests.get(url, timeout=10)

            with open(path, "w", encoding="utf-8") as f:
                f.write(response.text)

            downloads_dictionary[title] = path

    except requests.exceptions.RequestException as e:
        raise f"Request failed: {e}"

    except OSError as e:
        raise f"File saving error: {e}"

    return downloads_dictionary


def url_validity(url: str) -> bool:
    """
    Basic check to ensure we are scraping the correct type of url by searching for keywords in the string
    Args:
        url (str): string representing the url of the article to be checked
    Returns:
        (bool): boolean value that indicates if the url is valid
    """

    return "articles" in url or "news" in url


def date_conversion(date: str) -> datetime:
    """
    Handles the date scraped from the articles and converts them to a usable datetime value
    Args:
        date (str): date scraped that is represented in string form
    Returns:
        (datetime): datetime conversion of the equivalent date, this standardises the date when comparing with return value of date_calculation
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
    Searches BBC News for articles related to the specified keyword, and downloads articles within a certain date range.

    Args:
        name (str): The search term used to query BBC News articles.

    Returns:
        Dict[str, str]: Dictionary mapping article titles to their file paths after being downloaded as HTML.

    Raises:
        RequestException: If there are issues accessing a URL.
        OsError: If files cannot be saved in the specified directory.
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

        if page_count > 29:
            break

        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")

        promo_articles = soup.find_all("div", attrs={"data-testid": "default-promo"})

        if not promo_articles:
            break

        for article in promo_articles:
            title_struct = article.find("p")
            if not title_struct:
                continue  # Skips article if there is no title

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
                continue  # Skips the unnecessary part of the code

            size = len(web_dictionary) + 1 <= depth

            if url_validity(link) and size and date >= last_date:
                web_dictionary[title] = link
            elif not size:
                limit = True
                break

        if limit:  # Checks if we have reached the 10 page limit, speeding up runtime
            next_page = False
        else:
            page_count += 1

    local_file_dict = {}

    if len(web_dictionary) != 0:
        local_file_dict = url_download(web_dictionary)
        return local_file_dict
    else:
        return None


def cnn_search(name: str) -> Dict[str, str]:
    """
    Searches CNN News for articles related to the specified keyword, and downloads articles within a certain date range.

    Args:
        name (str): The search term used to query CNN News articles.

    Returns:
        Dict[str, str]: Dictionary mapping article titles to their file paths after being downloaded as HTML.

    Raises:
        RequestException: If there are issues accessing a URL.
        OsError: If files cannot be saved in the specified directory.
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
