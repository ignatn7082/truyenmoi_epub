from abc import ABC, abstractmethod

class SourceCrawler(ABC):
    domain = None
    name = "Unknown"

    @abstractmethod
    def get_all_chapter_links(self, base_url, task_id=None):
        pass

    @abstractmethod
    def get_chapter_content(self, url, session=None):
        pass

    def extract_novel_info(self, url):
        from untils.parser import get_soup
        import re
        soup = get_soup(url)
        if not soup:
            return "Truyện Không Tên", url
        title_tag = soup.find('h1') or soup.find('title')
        title = title_tag.get_text(strip=True).split('-')[0].strip() if title_tag else "Truyện"
        title = re.sub(r'\s*-\s*Trang.*$', '', title, flags=re.I)
        return title, url