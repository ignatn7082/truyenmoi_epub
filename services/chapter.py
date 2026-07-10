

from untils.cleaner import clean_content
from untils.parser import get_soup


def get_chapter_content(url, session=None):
    soup = get_soup(url, session=session)
    if not soup:
        return None
    selectors = ['div.chapter-content', 'div.read-content', 'div#content', 'article', '.entry-content']
    content = None
    for sel in selectors:
        content = soup.select_one(sel)
        if content and len(content.get_text(strip=True)) > 200:
            break
    if not content:
        content = max(soup.find_all(['div','article']), key=lambda x: len(x.get_text(strip=True)), default=None)
    return clean_content(content) if content else None