"""
services/metruyenchuvn_scraper.py

Scraper cho metruyenchuvn.com và các site cùng "theme MeTruyenChu"
(metruyenchu.com, metruyenchu.org, metruyenchu.net, metruyenchu.xyz, ...).

Khác với scraper truyenmoiss.org gốc (mục lục phân trang bằng URL thật
?page=1,2,3...), site này chỉ nhúng sẵn ~100 chương đầu trong HTML trang
giới thiệu, phần "phân trang 1 2 3 › Cuối»" chỉ là nút JS gọi AJAX cùng
một địa chỉ (không có URL riêng cho từng trang). Do đó:

  - ~100 chương đầu: đã có URL sẵn -> tải SONG SONG (ThreadPoolExecutor).
  - Các chương còn lại: không biết URL trước -> phải đi TUẦN TỰ theo link
    "Chương tiếp" nhúng trong mỗi trang đọc chương.

Mọi hàm ở đây đều nhận `on_progress(done, total_hint, title)` để routes/
có thể cập nhật tiến trình cho UI theo thời gian thực.
"""

import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from ebooklib import epub

SUPPORTED_DOMAINS = (
    "metruyenchuvn.com",
    "metruyenchu.com",
    "metruyenchu.org",
    "metruyenchu.net",
    "metruyenchu.xyz",
    "metruyenchu.com.vn",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}

try:
    import lxml  # noqa: F401
    PARSER = "lxml"
except ImportError:
    PARSER = "html.parser"


def is_supported(url: str) -> bool:
    return any(domain in url for domain in SUPPORTED_DOMAINS)


def get_soup(url, session):
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return BeautifulSoup(resp.text, PARSER)


def get_book_info(book_url, session):
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

    first_chapter_url = None
    for a in soup.find_all("a", href=True):
        if a.get_text(strip=True).lower() == "chương 1":
            first_chapter_url = urljoin(book_url, a["href"])
            break

    # Nhóm các link "Chương N" theo container chứa chúng, lấy nhóm nhiều
    # nhất (= "Danh sách chương" thật, khác khối "Chương mới nhất cập nhật"
    # chỉ có 5 link), rồi sắp xếp lại theo số chương cho chắc đúng thứ tự.
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
        best_group = max(groups.values(), key=len)
        seen_nums = set()
        for num, text, url in sorted(best_group, key=lambda x: x[0]):
            if num not in seen_nums:
                seen_nums.add(num)
                known_chapters.append((text, url))

    if not first_chapter_url and known_chapters:
        first_chapter_url = known_chapters[0][1]
    if not first_chapter_url:
        raise RuntimeError("Không tìm thấy link Chương 1 trên trang truyện.")

    total_chapters = None
    for li in soup.select("li"):
        text = li.get_text(" ", strip=True)
        if text.lower().startswith("số chương"):
            m = re.search(r"\d+", text)
            if m:
                total_chapters = int(m.group())
            break

    return {
        "title": title,
        "author": author,
        "cover_url": cover_url,
        "first_chapter_url": first_chapter_url,
        "known_chapters": known_chapters,
        "total_chapters": total_chapters,
        "source_url": book_url,
    }


def extract_chapter_title(soup, fallback):
    h2 = soup.find("h2") or soup.find("h1")
    return h2.get_text(strip=True) if h2 else fallback


def clean_text(node):
    for bad in node.select("script, style, ins, .ads, .quangcao"):
        bad.decompose()
    lines = [ln.strip() for ln in node.get_text("\n").split("\n")]
    return "\n\n".join(ln for ln in lines if ln)


def extract_chapter_content(soup):
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


def crawl_all_chapters(book_info, session, delay=0.15, workers=8, limit=None, on_progress=None):
    """
    on_progress(done, total_hint, title) được gọi sau mỗi chương tải xong,
    total_hint = tổng số chương ước tính (để routes/status.py vẽ % tiến trình).
    """
    total_hint = limit or book_info.get("total_chapters") or len(book_info.get("known_chapters") or []) or None

    chapters_by_url = {}
    ordered_urls = []

    known = book_info.get("known_chapters") or []
    if limit:
        known = known[:limit]

    done = 0

    if known:
        urls = [u for _, u in known]
        ordered_urls.extend(urls)
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
                except Exception:  # noqa: BLE001
                    failed.append((title, url))
                    continue
                chapters_by_url[url] = chapter
                done += 1
                if on_progress:
                    on_progress(done, total_hint, chapter["title"])

        for title, url in failed:
            try:
                chapter, _next_url = fetch_chapter(url, session, title, retries=6, backoff=2.0)
                chapters_by_url[url] = chapter
                done += 1
                if on_progress:
                    on_progress(done, total_hint, chapter["title"])
                time.sleep(delay)
            except Exception:  # noqa: BLE001
                ordered_urls.remove(url)

        last_url = ordered_urls[-1]
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
        done += 1
        if on_progress:
            on_progress(done, total_hint or idx, chapter["title"])
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


def download_book(book_url, output_path, delay=0.15, workers=8, limit=None, on_progress=None):
    """Hàm tiện ích gộp cả 3 bước - dùng trực tiếp từ routes/convert.py."""
    session = requests.Session()
    book_info = get_book_info(book_url, session)
    chapters = crawl_all_chapters(
        book_info, session, delay=delay, workers=workers, limit=limit, on_progress=on_progress
    )
    build_epub(book_info, chapters, output_path, session)
    return book_info, chapters
