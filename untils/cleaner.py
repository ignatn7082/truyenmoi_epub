import re
import os

def clean_content(content):
    for tag in content.find_all(['script', 'style', 'iframe', 'nav', 'header', 'footer']):
        tag.decompose()
    for bad in content.find_all('div', class_=re.compile(r'ad|ads|banner|footer|comment', re.I)):
        bad.decompose()
    text = content.get_text(separator='\n')
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n\n'.join(lines)