# TruyệnMoiSS → EPUB Web Downloader

Công cụ web tải truyện từ **truyenmoiss.org** sang file EPUB tiện lợi.

## Tính năng
- Giao diện web thân thiện
- Tự động quét toàn bộ mục lục
- Xử lý tốt tên chương (Chương 1 & Chương cuối)
- Tải chương song song, nhanh chóng
- Tiến trình realtime
- Tải file EPUB trực tiếp

## Cài đặt & Chạy

### 1. Cài dependencies
```bash
pip install -r requirements.txt
```

### 2. Chạy web server
```bash
python app.py
```

### 3. Truy cập
Mở trình duyệt: **http://localhost:5000**

## Cách sử dụng
1. Dán link truyện (ví dụ: `https://truyenmoiss.org/truyen/ten-truyen`)
2. Nhấn **Tạo EPUB**
3. Chờ hệ thống quét và tải (có thể mất 1-5 phút tùy số chương)
4. Tải file EPUB về máy

## Lưu ý
- Không nên chạy quá nhiều request cùng lúc để tránh bị block
- File EPUB được lưu tạm trong thư mục `generated_epubs`
- Server chạy ở chế độ debug (production nên dùng gunicorn)

## Tech Stack
- Python + Flask
- BeautifulSoup4
- ebooklib
- ThreadPoolExecutor

---
**Developed for personal use**



