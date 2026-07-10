

from services.crawler import get_all_chapter_links
from services.epub_service import create_epub_task
from services.progress import write_progress


def scan_and_create_epub(novel_title, base_url, task_id):
    try:
        # Giai đoạn 1: Quét mục lục
        chapters = get_all_chapter_links(base_url, task_id)
        
        if not chapters:
            write_progress(
                task_id,
                phase='ERROR',
                progress=0,
                message='Không tìm thấy chương nào',
                total_chapters=0,
                completed_chapters=0,
                extra={'phase': 'SCAN'}
            )
            with open(f"task_{task_id}.status", "w", encoding='utf-8') as f:
                f.write("ERROR|Không tìm thấy chương nào")
            return

        # Giai đoạn 2: Tạo EPUB
        create_epub_task(novel_title, chapters, task_id)
        
    except Exception as e:
        with open(f"task_{task_id}.status", "w", encoding='utf-8') as f:
            f.write(f"ERROR|{str(e)}")