"""
metruyenchuvn_to_epub.py
Tải truyện từ metruyenchuvn.com (và các site dùng chung theme) thành file EPUB.

--------------------------------------------------------------------------
KHÁC BIỆT so với truyenmoi_epub gốc (viết cho truyenmoiss.org):
--------------------------------------------------------------------------
- truyenmoiss.org: mục lục chương được phân trang bằng URL thật
  (vd truyen/xxx?page=1, ?page=2 ...), nên có thể quét hết mục lục trước,
  thu thập toàn bộ link chương, rồi tải song song bằng ThreadPoolExecutor.

- metruyenchuvn.com: trang giới thiệu truyện chỉ nhúng sẵn ~100 chương đầu
  trong HTML gốc. Phần phân trang "1 2 3 › Cuối»" chỉ là nút bấm JavaScript
  gọi AJAX NGAY TẠI CÙNG MỘT ĐỊA CHỈ trang (đã kiểm chứng: gọi thêm
  ?page=2 vào URL vẫn trả về y hệt 100 chương đầu) => không có URL riêng
  cho từng trang mục lục, không thể quét đủ 1782 chương chỉ bằng cách
  request nhiều URL mục lục khác nhau như bản gốc.

  Giải pháp dùng ở đây: mỗi trang đọc chương đều có sẵn link "Chương tiếp"
  trỏ thẳng tới URL (kèm mã hash riêng) của chương kế tiếp. Chỉ cần lấy
  URL "Chương 1" từ trang giới thiệu truyện, rồi lần lượt đi theo link
  "Chương tiếp" cho tới khi hết truyện.

  Lưu ý: vì URL của chương N+1 chỉ biết được SAU KHI đã tải xong chương N,
  việc quét bắt buộc phải làm TUẦN TỰ (không thể dùng ThreadPoolExecutor
  để tải song song như bản gốc).
--------------------------------------------------------------------------

Cài đặt:
    pip install requests beautifulsoup4 ebooklib

Sử dụng:
    python metruyenchuvn_to_epub.py https://metruyenchuvn.com/ta-mo-phong-truong-sinh-lo-dich
    python metruyenchuvn_to_epub.py <link truyện> -o ten_file.epub --delay 0.5
    python metruyenchuvn_to_epub.py <link truyện> --limit 20   # test thử 20 chương
"""

import re
import time
import argparse
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup
from ebooklib import epub

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}

try:
    import lxml  # noqa: F401
    PARSER = "lxml"          # nhanh hơn đáng kể so với html.parser
except ImportError:
    PARSER = "html.parser"   # fallback nếu chưa cài lxml


def get_soup(url, session):
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return BeautifulSoup(resp.text, PARSER)


def get_book_info(book_url, session):
    """Đọc trang giới thiệu truyện: lấy tên, tác giả, ảnh bìa, link Chương 1."""
    soup = get_soup(book_url, session)

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Truyen"
    title = re.sub(r"\s*\(Full\).*$", "", title).strip()
    title = re.sub(r"\s*-\s*MeTruyenChu.*$", "", title).strip()

    author = "Không rõ"
    for li in soup.select("li"):
        text = li.get_text(" ", strip=True)
        if text.lower().startswith("tác giả"):
            a = li.find("a")
            author = a.get_text(strip=True) if a else text.split(":", 1)[-1].strip()
            break

    cover_url = None
    img = soup.select_one(".book_avatar img, .book-info img, img[src*='/media/book/']")
    if img and img.get("src"):
        cover_url = urljoin(book_url, img["src"])

    # Link "Chương 1" nằm ở khu vực "Tìm chương"
    first_chapter_url = None
    for a in soup.find_all("a", href=True):
        if a.get_text(strip=True).lower() == "chương 1":
            first_chapter_url = urljoin(book_url, a["href"])
            break

    # "Danh sách chương" trên trang giới thiệu thường đã nhúng sẵn ~100 link
    # chương đầu (kèm hash) ngay trong HTML gốc -> tận dụng để tải SONG SONG.
    # Lưu ý: trang còn có khối "Chương mới nhất được cập nhật" (chỉ 5 link,
    # KHÔNG theo thứ tự) và khối "Tìm chương" (Chương 1 / Chương cuối) cũng
    # chứa chữ "Chương N" -> không thể chỉ dò theo text, phải nhóm theo
    # container để tìm đúng khối danh sách đầy đủ, rồi sắp xếp lại theo số
    # chương cho chắc chắn đúng thứ tự.
    from collections import defaultdict
    pattern = re.compile(r"^Chương\s+(\d+)", re.IGNORECASE)
    groups = defaultdict(list)
    for a in soup.find_all("a", href=True):
        m = pattern.match(a.get_text(strip=True))
        if not m:
            continue
        anchor_container = a.find_parent(["ul", "ol"]) or a.parent
        groups[id(anchor_container)].append(
            (int(m.group(1)), a.get_text(strip=True), urljoin(book_url, a["href"]))
        )

    known_chapters = []
    if groups:
        best_group = max(groups.values(), key=len)  # khối có nhiều "Chương N" nhất = danh sách thật
        seen_nums = set()
        for num, text, url in sorted(best_group, key=lambda x: x[0]):
            if num not in seen_nums:
                seen_nums.add(num)
                known_chapters.append((text, url))

    if not first_chapter_url and known_chapters:
        first_chapter_url = known_chapters[0][1]

    if not first_chapter_url:
        raise RuntimeError("Không tìm thấy link Chương 1 trên trang truyện.")

    return {
        "title": title,
        "author": author,
        "cover_url": cover_url,
        "first_chapter_url": first_chapter_url,
        "known_chapters": known_chapters,  # list[(title, url)], đã có sẵn -> tải song song được
        "source_url": book_url,
    }


def extract_chapter_title(soup, fallback):
    h2 = soup.find("h2") or soup.find("h1")
    if h2:
        return h2.get_text(strip=True)
    return fallback


def clean_text(node):
    for bad in node.select("script, style, ins, .ads, .quangcao"):
        bad.decompose()
    lines = [ln.strip() for ln in node.get_text("\n").split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n\n".join(lines)


def extract_chapter_content(soup):
    """Nội dung chương nằm trong khối text lớn giữa tiêu đề và nav 'Chương tiếp'."""
    candidates = [
        soup.select_one("#chapter-c"),
        soup.select_one(".chapter-c"),
        soup.select_one("#chapter-content"),
        soup.select_one(".chapter-content"),
        soup.select_one("article"),
    ]
    for node in candidates:
        if node and len(node.get_text(strip=True)) > 200:
            return clean_text(node)

    # fallback: chọn div có nhiều chữ nhất, không phải khung layout ngoài cùng
    best, best_len = None, 0
    for div in soup.find_all("div"):
        if div.find(["nav", "header", "footer"]):
            continue
        text_len = len(div.get_text(strip=True))
        if best_len < text_len < 200000:
            best, best_len = div, text_len
    if best and best_len > 200:
        return clean_text(best)

    raise RuntimeError("Không trích xuất được nội dung chương.")


def find_next_chapter_url(soup, current_url):
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        if "chương tiếp" in text or "chuong tiep" in text:
            href = a["href"]
            if href in ("#", "javascript:;", "javascript:void(0);"):
                return None
            return urljoin(current_url, href)
    next_link = soup.find("a", rel="next")
    if next_link and next_link.get("href"):
        return urljoin(current_url, next_link["href"])
    return None


def fetch_chapter(url, session, fallback_title, retries=4, backoff=1.5):
    """Tải 1 chương, tự thử lại nếu gặp lỗi mạng/500 tạm thời (thường do quá tải khi tải song song)."""
    last_err = None
    for attempt in range(retries):
        try:
            soup = get_soup(url, session)
            title = extract_chapter_title(soup, fallback_title)
            content = extract_chapter_content(soup)
            next_url = find_next_chapter_url(soup, url)
            return {"title": title, "content": content, "url": url}, next_url
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"Lỗi tải {url} sau {retries} lần thử: {last_err}")


def crawl_all_chapters(book_info, session, delay=0.15, workers=10, limit=None, on_progress=None):
    """
    Quét toàn bộ chương, tối ưu tốc độ theo 2 giai đoạn:

    Giai đoạn 1 (SONG SONG): các chương đã có sẵn URL trong 'known_chapters'
    (lấy từ trang giới thiệu truyện) được tải cùng lúc bằng ThreadPoolExecutor.

    Giai đoạn 2 (TUẦN TỰ, nhanh): từ chương cuối cùng đã biết, tiếp tục đi
    theo link 'Chương tiếp' cho tới hết truyện - bắt buộc tuần tự vì URL
    chương kế tiếp chỉ lộ ra sau khi đã tải xong chương hiện tại.
    """
    chapters_by_url = {}
    ordered_urls = []

    known = book_info.get("known_chapters") or []
    if limit:
        known = known[:limit]

    if known:
        urls = [u for _, u in known]
        ordered_urls.extend(urls)
        done = 0
        failed = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(fetch_chapter, url, session, title): (url, title)
                for title, url in known
            }
            for fut in futures:
                url, title = futures[fut]
                try:
                    chapter, _next_url = fut.result()
                except Exception as e:  # noqa: BLE001
                    print(f"  [Lỗi] {title} ({url}): {e} -> sẽ thử lại tuần tự")
                    failed.append((title, url))
                    continue
                chapters_by_url[url] = chapter
                done += 1
                if on_progress:
                    on_progress(done, chapter["title"])

        # thử lại tuần tự (chậm nhưng ổn định hơn) các chương bị lỗi khi tải song song
        for title, url in failed:
            try:
                chapter, _next_url = fetch_chapter(url, session, title, retries=6, backoff=2.0)
                chapters_by_url[url] = chapter
                done += 1
                if on_progress:
                    on_progress(done, chapter["title"])
                time.sleep(delay)
            except Exception as e:  # noqa: BLE001
                print(f"  [Bỏ qua] Không tải được {title} ({url}): {e}")
                ordered_urls.remove(url)

        last_url = ordered_urls[-1]
        # cần next_url của chương cuối cùng đã biết -> lấy lại từ soup đã tải
        _, next_url = fetch_chapter(last_url, session, "")
    else:
        next_url = book_info["first_chapter_url"]

    idx = len(ordered_urls)
    seen = set(ordered_urls)
    url = None if (limit and idx >= limit) else next_url
    while url and url not in seen:
        seen.add(url)
        chapter, next_url = fetch_chapter(url, session, f"Chương {idx + 1}")
        chapters_by_url[url] = chapter
        ordered_urls.append(url)
        idx += 1
        if on_progress:
            on_progress(idx, chapter["title"])
        if limit and idx >= limit:
            break
        url = next_url
        time.sleep(delay)

    return [chapters_by_url[u] for u in ordered_urls if u in chapters_by_url]


def build_epub(book_info, chapters, output_path, session):
    book = epub.EpubBook()
    book.set_identifier(book_info["source_url"])
    book.set_title(book_info["title"])
    book.set_language("vi")
    book.add_author(book_info["author"])

    if book_info.get("cover_url"):
        try:
            img_resp = session.get(book_info["cover_url"], headers=HEADERS, timeout=30)
            if img_resp.ok:
                book.set_cover("cover.jpg", img_resp.content)
        except requests.RequestException:
            pass

    epub_chapters = []
    for i, ch in enumerate(chapters, start=1):
        c = epub.EpubHtml(title=ch["title"], file_name=f"chap_{i:05d}.xhtml", lang="vi")
        body = "".join(f"<p>{p}</p>" for p in ch["content"].split("\n\n"))
        c.content = f"<h2>{ch['title']}</h2>{body}"
        book.add_item(c)
        epub_chapters.append(c)

    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + epub_chapters

    epub.write_epub(output_path, book)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Tải truyện từ metruyenchuvn.com sang EPUB")
    parser.add_argument("url", help="Link trang giới thiệu truyện, vd: https://metruyenchuvn.com/ten-truyen")
    parser.add_argument("-o", "--output", default=None, help="Đường dẫn file epub xuất ra")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số chương (dùng để test)")
    parser.add_argument("--delay", type=float, default=0.15,
                         help="Độ trễ (giây) giữa các request tuần tự (phần chương chưa biết URL trước)")
    parser.add_argument("--workers", type=int, default=8,
                         help="Số luồng tải song song cho phần chương đã biết URL sẵn (giảm nếu bị lỗi 500)")
    args = parser.parse_args()

    session = requests.Session()
    print(f"Đang đọc thông tin truyện: {args.url}")
    book_info = get_book_info(args.url, session)
    print(f"Truyện: {book_info['title']} - Tác giả: {book_info['author']}")
    print(f"Số chương đã biết sẵn URL (tải song song): {len(book_info['known_chapters'])}")

    def progress(idx, title):
        print(f"  [{idx}] {title}")

    chapters = crawl_all_chapters(
        book_info, session,
        delay=args.delay, workers=args.workers, limit=args.limit, on_progress=progress,
    )
    print(f"Đã quét được {len(chapters)} chương.")

    output_path = args.output or f"{re.sub(r'[^a-zA-Z0-9]+', '_', book_info['title']).strip('_')}.epub"
    build_epub(book_info, chapters, output_path, session)
    print(f"Đã tạo file: {output_path}")


if __name__ == "__main__":
    main()