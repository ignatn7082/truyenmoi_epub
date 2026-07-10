from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
import requests

from config import HEADERS
from untils.helpers import normalize_chapter_title
from untils.parser import get_soup
from services.progress import write_progress


def parse_chapter_links(soup, all_chapters):
    if not soup:
        return 0

    new_count = 0
    for a in soup.find_all('a', href=True):
        if re.search(r'/chuong-\d+', a['href']):
            full_url = a['href'] if a['href'].startswith('http') else 'https://truyenmoiss.org' + a['href']
            if full_url not in all_chapters:
                title = normalize_chapter_title(a.get_text().strip(), full_url, len(all_chapters) + 1, fetch_page_title=False)
                all_chapters[full_url] = {'url': full_url, 'title': title}
                new_count += 1
    return new_count


def get_all_chapter_links(base_url, task_id=None):
    """Quét mục lục với tiến trình"""
    all_chapters = {}
    max_pages = 300
    consecutive_empty = 0
    scanned_pages = 0
    total_estimated = 50  # Ước lượng ban đầu

    print(f"[{task_id}] 🔍 Bắt đầu quét mục lục...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_page = {}
        page = 1

        while page <= max_pages:
            # Submit batch 8 trang
            for _ in range(8):
                if page > max_pages:
                    break
                page_url = base_url.rstrip('/') if page == 1 else f"{base_url.rstrip('/')}/trang-{page}"
                future_to_page[executor.submit(get_soup, page_url)] = page
                page += 1

            # Xử lý kết quả
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

                    # Cập nhật tiến trình (ghi file tạm)
                    if task_id and scanned_pages % 3 == 0:  # Cập nhật mỗi 3 trang
                        progress = min(int((scanned_pages / 40) * 45), 45)  # Max 45% cho giai đoạn quét
                        with open(f"task_{task_id}.progress", "w", encoding='utf-8') as f:
                            f.write(f"SCAN|{progress}|Đang quét trang {scanned_pages}... Tìm thấy {len(all_chapters)} chương")

                    if consecutive_empty >= 3:
                        break

            time.sleep(0.15)  # Tốc độ cao

    # Sắp xếp
    def get_num(ch):
        m = re.search(r'/chuong-(\d+)', ch['url'])
        return int(m.group(1)) if m else 999999

    chapters = sorted(all_chapters.values(), key=get_num)
    
    # Hoàn thành quét
    if task_id:
        with open(f"task_{task_id}.progress", "w", encoding='utf-8') as f:
            f.write(f"SCAN|50|Đã quét xong {len(chapters)} chương")
    
    print(f"[{task_id}] ✅ Hoàn thành quét: {len(chapters)} chương")
    return chapters