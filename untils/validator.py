from services.sources.registry import get_supported_domains

def is_valid_url(url):
    if not url or not url.startswith(('http://', 'https://')):
        return False
    return any(domain in url.lower() for domain in get_supported_domains())