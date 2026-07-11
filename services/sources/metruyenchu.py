from services.sources.base import SourceCrawler
import re
import time
import requests
from bs4 import BeautifulSoup
from untils.helpers import normalize_chapter_title
from untils.parser import get_soup
from services.progress import write_progress

class MeTruyenChuCrawler(SourceCrawler):
    domain = "metruyenchuvn.com"
    name = "MeTruyenChu"

    def get_all_chapter_links(self, base_url, task_id=None):
        all_chapters = {}
        print(f"[{task_id}] 🔍 Quét tất cả chương MeTruyenChu...")

        # Lấy story_id
        soup = get_soup(base_url)
        story_id = None
        if soup:
            match = re.search(r'page\((\d+)', str(soup))
            if match:
                story_id = match.group(1)

        if story_id:
            print(f"Story ID tìm thấy: {story_id}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': base_url
            }

            for page in range(1, 60):
                try:
                    resp = requests.get(
                        f"https://metruyenchuvn.com/ajax/story/{story_id}/chapters?page={page}",
                        headers=headers,
                        timeout=15
                    )

                    if resp.status_code != 200 or len(resp.text) < 100:
                        break

                    page_soup = BeautifulSoup(resp.text, 'lxml')
                    added = 0

                    for a in page_soup.find_all('a', href=True):
                        href = a.get('href', '')
                        if '/chuong-' in href:
                            full_url = 'https://metruyenchuvn.com' + href if not href.startswith('http') else href
                            if full_url not in all_chapters:
                                title = normalize_chapter_title(a.get_text().strip(), full_url, len(all_chapters) + 1)
                                all_chapters[full_url] = {'url': full_url, 'title': title}
                                added += 1

                    print(f"Trang {page}: +{added} chương | Tổng: {len(all_chapters)}")

                    if task_id:
                        progress = min(45, int(page * 0.8))
                        with open(f"task_{task_id}.progress", "w", encoding='utf-8') as f:
                            f.write(f"SCAN|{progress}|Trang {page} - {len(all_chapters)} chương")

                    if added == 0 and page > 5:
                        break

                    time.sleep(1.0)
                except Exception as e:
                    print(f"Lỗi trang {page}: {e}")
                    break

        # Fallback nếu AJAX không lấy đủ
        if len(all_chapters) < 300:
            print("Fallback scrape trang chính...")
            all_chapters.update(self._scrape_single_page(base_url))

        chapters = sorted(all_chapters.values(), key=self._get_chapter_num)
        print(f"[{task_id}] Hoàn thành: {len(chapters)} chương")

        if task_id:
            with open(f"task_{task_id}.progress", "w", encoding='utf-8') as f:
                f.write(f"SCAN|50|Đã quét {len(chapters)} chương")

        return chapters

    def _scrape_single_page(self, base_url):
        all_chapters = {}
        soup = get_soup(base_url)
        if not soup:
            return all_chapters

        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if '/chuong-' in href and re.search(r'/chuong-\d+', href):
                full_url = 'https://metruyenchuvn.com' + href if not href.startswith('http') else href
                if full_url not in all_chapters:
                    title = normalize_chapter_title(a.get_text().strip(), full_url, len(all_chapters) + 1)
                    all_chapters[full_url] = {'url': full_url, 'title': title}
        return all_chapters

    def _get_chapter_num(self, ch):
        m = re.search(r'/chuong-(\d+)', ch['url'])
        return int(m.group(1)) if m else 999999

    def get_chapter_content(self, url, session=None):
        soup = get_soup(url, session=session)
        if not soup:
            return None
        selectors = ['div.chapter-content', '.reading-content', '#chapter', 'article']
        content = None
        for sel in selectors:
            content = soup.select_one(sel)
            if content and len(content.get_text(strip=True)) > 150:
                break
        if not content:
            content = max(soup.find_all(['div', 'article']), key=lambda x: len(x.get_text(strip=True)), default=None)
        from untils.cleaner import clean_content
        return clean_content(content) if content else None