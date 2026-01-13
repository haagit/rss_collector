import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

def discover_feeds(page_url: str, timeout: int = 10) :
    """
    page_url(웹페이지)에서 RSS/Atom 피드 링크를 발견해서 절대 URL 목록으로 반환.
    우선순위:
      1) <link rel="alternate" type="application/rss+xml|application/atom+xml"...>
      2) 본문 <a href="...rss|atom|feed|.xml"> 형태 휴리스틱
    """
    headers = {"User-Agent": "Mozilla/5.0 (RSS-Discovery/1.0)"}
    r = requests.get(page_url, headers=headers, timeout=timeout)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    feeds: list[str] = []  

    # 1) 표준 feed discovery
    for link in soup.find_all("link", attrs={"rel": re.compile(r"\balternate\b", re.I)}):
        
        typ = (link.get("type") or "").lower().strip()
        href = (link.get("href") or "").strip()
        
        if not href: 
            continue
        if typ in ("application/rss+xml", "application/atom+xml", "application/rdf+xml", "text/xml", "application/xml"):
            feeds.append(urljoin(page_url, href))   # 경로 완성

    # 2) 휴리스틱 (일부 사이트는 <a>로만 걸어둠)
    if not feeds:
        for a in soup.find_all("a", href=True):
            
            href = a["href"].strip() # href=True 조건으로 속성 없는경우 대해 이미 필터링 함.
            if not href:             # 속성에 해당하는 value없는 경우 continue 진행
                continue
            h = href.lower()
            if any(k in h for k in ("rss", "atom", "feed")) or h.endswith((".rss", ".xml")):
                feeds.append(urljoin(page_url, href))

    uniq = []
    seen = set()    
    
    for f in feeds:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


if __name__ == "__main__":
    url = "https://www.boannews.com/"  # 여기에 사이트 URL 
    print(discover_feeds(url))         # ['https://www.boannews.com/custom/news_rss.asp']
