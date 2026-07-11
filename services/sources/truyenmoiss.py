from services.sources.base import SourceCrawler
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from untils.helpers import normalize_chapter_title
from untils.parser import get_soup
from services.progress import write_progress
import time

class TruyenMoiSSCrawler(SourceCrawler):
    domain = "truyenmoiss.org"
    name = "TruyenMoiSS"

    def get_all_chapter_links(self, base_url, task_id=None):
        # Giữ nguyên logic cũ của bạn (copy từ crawler.py cũ)
        all_chapters = {}
        max_pages = 300
        consecutive_empty = 0
        scanned_pages = 0

        print(f"[{task_id}] 🔍 Bắt đầu quét mục lục {self.name}...")

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_page = {}
            page = 1
            while page <= max_pages:
                for _ in range(8):
                    if page > max_pages:
                        break
                    page_url = base_url.rstrip('/') if page == 1 else f"{base_url.rstrip('/')}/trang-{page}"
                    future_to_page[executor.submit(get_soup, page_url)] = page
                    page += 1

                for future in list(future_to_page.keys()):
                    if future.done():
                        p = future_to_page.pop(future)
                        scanned_pages += 1
                        soup = future.result()
                        if soup:
                            count = 0
                            for a in soup.find_all('a', href=True):
                                if re.search(r'/chuong-\d+', a['href']):
                                    full_url = a['href'] if a['href'].startswith('http') else 'https://truyenmoiss.org' + a['href']
                                    if full_url not in all_chapters:
                                        title = normalize_chapter_title(a.get_text().strip(), full_url, len(all_chapters) + 1)
                                        all_chapters[full_url] = {'url': full_url, 'title': title}
                                        count += 1
                            if count == 0:
                                consecutive_empty += 1
                            else:
                                consecutive_empty = 0

                        if task_id and scanned_pages % 3 == 0:
                            progress = min(int((scanned_pages / 40) * 45), 45)
                            with open(f"task_{task_id}.progress", "w", encoding='utf-8') as f:
                                f.write(f"SCAN|{progress}|Đang quét {self.name}... Tìm thấy {len(all_chapters)} chương")

                        if consecutive_empty >= 3:
                            break
                time.sleep(0.15)

        # Sắp xếp
        def get_num(ch):
            m = re.search(r'/chuong-(\d+)', ch['url'])
            return int(m.group(1)) if m else 999999
        chapters = sorted(all_chapters.values(), key=get_num)

        if task_id:
            with open(f"task_{task_id}.progress", "w", encoding='utf-8') as f:
                f.write(f"SCAN|50|Đã quét xong {len(chapters)} chương từ {self.name}")
        return chapters

    def get_chapter_content(self, url, session=None):
        from services.chapter import get_chapter_content as old_get
        return old_get(url, session)  # reuse tạm