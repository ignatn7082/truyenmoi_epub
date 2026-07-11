from services.sources.truyenmoiss import TruyenMoiSSCrawler
from services.sources.metruyenchu import MeTruyenChuCrawler

SOURCES = {
    "truyenmoiss.org": TruyenMoiSSCrawler(),
    "metruyenchuvn.com": MeTruyenChuCrawler(),
    # Thêm nguồn khác ở đây
}

def get_crawler(url: str):
    for domain, crawler in SOURCES.items():
        if domain in url.lower():
            return crawler
    return None

def get_supported_domains():
    return list(SOURCES.keys())