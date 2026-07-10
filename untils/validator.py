def is_valid_truyenmoiss_url(url):
    """Kiểm tra link có phải của truyenmoiss.org không"""
    if not url or not url.startswith(('http://', 'https://')):
        return False
    return 'truyenmoiss.org' in url.lower()