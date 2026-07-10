


import os



from config import UPLOAD_FOLDER, HEADERS
from untils.helpers import clean_old_files, sanitize_filename
import time
from ebooklib import epub
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.chapter import get_chapter_content
from services.progress import write_progress
from untils.helpers import normalize_chapter_title
from tqdm import tqdm
import requests

def create_epub_task(novel_title, chapters, task_id):
    """
    Hàm tạo EPUB trong background
    """
    try:
        clean_old_files()  # Dọn dẹp file cũ
        
        safe_name = sanitize_filename(novel_title)
        output_file = os.path.join(UPLOAD_FOLDER, f"{safe_name}_{task_id}.epub")
        
        print(f"[{task_id}] Bắt đầu tạo EPUB: {novel_title} ({len(chapters)} chương)")

        book = epub.EpubBook()
        book.set_identifier(f"truyenmoiss_{int(time.time())}")
        book.set_title(novel_title)
        book.set_language('vi')
        book.add_author("Tác giả không rõ")

        spine = ['nav']
        toc = []

        # Tải nội dung các chương song song
        chapter_contents = [None] * len(chapters)
        success_count = 0

        print(f"[{task_id}] Đang tải nội dung {len(chapters)} chương...")
        write_progress(task_id, 'DOWNLOAD', 55, f"Đang tải nội dung {len(chapters)} chương...", len(chapters))

        session = requests.Session()
        session.headers.update(HEADERS)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(get_chapter_content, ch['url'], session): i for i, ch in enumerate(chapters)}
            
            for future in tqdm(as_completed(futures), total=len(futures), desc=f"Task {task_id}"):
                idx = futures[future]
                try:
                    content = future.result()
                    if content and len(content.strip()) > 10:
                        chapter_contents[idx] = content
                        success_count += 1
                        progress = 55 + int((success_count / max(len(chapters), 1)) * 35)
                        write_progress(task_id, 'DOWNLOAD', progress, f"Đã tải {success_count}/{len(chapters)} chương", len(chapters))
                    else:
                        print(f"[{task_id}] Chương {idx+1}: Nội dung trống hoặc quá ngắn")
                except Exception as e:
                    print(f"[{task_id}] Lỗi chương {idx+1}: {e}")

        print(f"[{task_id}] Tải xong {success_count}/{len(chapters)} chương. Đang tạo file EPUB...")

        # Tạo các chapter trong EPUB
        for i, (ch, content) in enumerate(zip(chapters, chapter_contents)):
            if not content:
                continue

            chapter_title = normalize_chapter_title(ch['title'], ch['url'], i + 1)
            
            chapter = epub.EpubHtml(
                title=chapter_title,
                file_name=f"chap_{i+1:04d}.xhtml",
                lang='vi'
            )
            
            # Tạo nội dung HTML
            paragraphs = ''.join(f'<p>{p}</p>' for p in content.split('\n\n') if p.strip())
            chapter.content = f"""
            <h1>{chapter_title}</h1>
            <div class="chapter-content">
                {paragraphs}
            </div>
            """
            
            book.add_item(chapter)
            spine.append(chapter)
            toc.append(epub.Link(chapter.file_name, chapter_title, f"chap_{i+1}"))

        # Cấu hình EPUB
        book.toc = toc
        book.spine = spine
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Thêm CSS cơ bản
        style = epub.EpubItem(uid="style_default", file_name="style.css", media_type="text/css",
                            content="body { font-family: Arial, sans-serif; line-height: 1.6; } h1 { text-align: center; }")
        book.add_item(style)

        # Lưu file
        epub.write_epub(output_file, book)
        write_progress(task_id, 'DONE', 100, 'Hoàn thành', len(chapters))
        
        # Ghi trạng thái thành công
        with open(f"task_{task_id}.status", "w", encoding='utf-8') as f:
            f.write(f"DONE|{output_file}")
        
        print(f"[{task_id}]  Hoàn thành! File: {output_file}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"[{task_id}]  Lỗi nghiêm trọng: {error_msg}")
        with open(f"task_{task_id}.status", "w", encoding='utf-8') as f:
            f.write(f"ERROR|{error_msg}")