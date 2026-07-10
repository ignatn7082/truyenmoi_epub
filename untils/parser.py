

import time

from bs4 import BeautifulSoup
import requests

from config import HEADERS
import re

def get_soup(url, session=None):
    max_retries = 3
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            if session is None:
                resp = requests.get(url, headers=HEADERS, timeout=20)
            else:
                resp = session.get(url, timeout=20)
            if resp.status_code == 429:
                wait_time = retry_delay * (2 ** attempt)
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            return BeautifulSoup(resp.text, 'lxml')
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))
            else:
                return None
    return None

def extract_novel_info(url):
    soup = get_soup(url)
    if not soup:
        return "Truyện Không Tên", url
    title_tag = soup.find('h1') or soup.find('title')
    novel_title = title_tag.get_text(strip=True).split('-')[0].strip() if title_tag else "Truyện"
    novel_title = re.sub(r'\s*-\s*Trang.*$', '', novel_title, flags=re.I)
    return novel_title, url
