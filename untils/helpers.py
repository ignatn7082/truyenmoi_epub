

import re
from datetime import datetime, timedelta
import os
from untils.parser import get_soup
from config import UPLOAD_FOLDER
import unicodedata

def normalize_chapter_title(title, url=None, fallback_num=None, fetch_page_title=False):
    title = (title or "").strip()
    m = re.search(r'/chuong-(\d+)', url or '')
    chapter_num = m.group(1) if m else None

    generic_titles = {
        'đọc từ đầu', 'doc tu dau', 'đọc mới nhất', 'doc moi nhat',
        'chương mới nhất', 'chuong moi nhat', 'mới nhất', 'moi nhat',
        'đọc tiếp', 'doc tiep', 'đọc tiếp chương', 'doc tiep chuong',
        'chương cuối', 'chuong cuoi'
    }

    # Ưu tiên lấy title từ trang chương
    page_title = None
    if url and fetch_page_title:
        soup = get_soup(url)
        if soup:
            title_tag = soup.find('h1') or soup.find('title')
            if title_tag:
                page_title = title_tag.get_text(" ", strip=True)
                page_title = re.sub(r'\s*-\s*Trang.*$', '', page_title, flags=re.I)
                page_title = re.sub(r'^Chương\s*\d+\s*[:\-]?\s*', '', page_title, flags=re.I).strip()

    if page_title and page_title.lower() not in generic_titles:
        if chapter_num and not re.search(r'^Chương\s*\d+', page_title, re.I):
            return f"Chương {chapter_num}: {page_title}"
        return page_title

    if not title or title.lower() in generic_titles:
        if chapter_num:
            return f"Chương {chapter_num}"
        if fallback_num is not None:
            return f"Chương {fallback_num}"
        return "Chương"

    if chapter_num and re.search(r'^Chương\s*1$', title, re.I):
        return f"Chương {chapter_num}"

    return title



def sanitize_filename(text):
    text = (text or "novel").strip()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace('đ', 'd').replace('Đ', 'D')
    text = re.sub(r'[^A-Za-z0-9\s\-_]+', '', text)
    text = re.sub(r'[\s\-]+', '_', text).strip('._-')
    return (text[:80] or 'novel').lower()




def clean_old_files():
    """Dọn dẹp file cũ hơn 2 giờ"""
    try:
        now = datetime.now()
        for f in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, f)
            if os.path.isfile(path) and now - datetime.fromtimestamp(os.path.getmtime(path)) > timedelta(hours=2):
                os.remove(path)
    except:
        pass


def get_soup_from_text(html_text):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html_text, 'lxml')