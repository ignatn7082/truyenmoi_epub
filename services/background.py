from services.epub_service import create_epub_task
from services.progress import write_progress

def scan_and_create_epub(novel_title, base_url, task_id, crawler):
    try:
        chapters = crawler.get_all_chapter_links(base_url, task_id)
        if not chapters:
            # error handling...
            return
        create_epub_task(novel_title, chapters, task_id)
    except Exception as e:
        with open(f"task_{task_id}.status", "w", encoding='utf-8') as f:
            f.write(f"ERROR|{str(e)}")