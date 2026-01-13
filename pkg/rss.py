import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger("RSS_collector : " + __name__)

def discover_feeds(page_url: str, timeout: int = 10) :
    """
    page_url(웹페이지)에서 RSS/Atom 피드 링크를 발견해서 절대 URL 목록으로 반환.
    우선순위:
      1) <link rel="alternate" type="application/rss+xml|application/atom+xml"...>
      2) 본문 <a href="...rss|atom|feed|.xml"> 형태 휴리스틱
    """
    headers = {"User-Agent": "Mozilla/5.0 (RSS-Discovery/1.0)"}
    ## 외부 통신 부분 예외처리
    try :
        logger.info(f"피드 탐색 시도 : {page_url}")
        r = requests.get(page_url, headers=headers, timeout=timeout)
        r.raise_for_status()
    except requests.exceptions.RequestException as e :
        # 접속실패.. 프로그램 죽지 않게 하며 로그만 남김
        logger.error(f"페이지 접속 실패 ({page_url}) : {e}")
        return []
    
    soup = BeautifulSoup(r.text, "html.parser")
    feeds: list[str] = []  

    # 1) 표준 feed discovery
    for link in soup.find_all("link", attrs={"rel": re.compile(r"\balternate\b", re.I)}):
        
        typ = (link.get("type") or "").lower().strip()
        href = (link.get("href") or "").strip()
        
        if not href: 
            continue
        if typ in ("application/rss+xml", "application/atom+xml", "application/rdf+xml", "text/xml", "application/xml"):
            full_url = feeds.append(urljoin(page_url, href))   # 경로 완성
            logger.debug(f"표준 피드 발견 : {full_url}")

    # 2) 휴리스틱 (일부 사이트는 <a>로만 걸어둠)
    if not feeds:
        for a in soup.find_all("a", href=True):
            href = a["href"].strip() # href=True 조건으로 속성 없는경우 대해 이미 필터링 함.
            if not href:             # 속성에 해당하는 value없는 경우 continue 진행
                continue
            h = href.lower()
            if any(k in h for k in ("rss", "atom", "feed")) or h.endswith((".rss", ".xml")):
                full_url = feeds.append(urljoin(page_url, href))
                logger.debug(f"휴리스틱 피드 발견 : {full_url}")

    uniq = []
    seen = set()    
    for f in feeds:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    logger.info(f"피드 탐색 완료 : ({len(uniq)})개 발견")
    return uniq


if __name__ == "__main__":
    url = "https://www.boannews.com/"  # 여기에 사이트 URL 
    print(discover_feeds(url))         # ['https://www.boannews.com/custom/news_rss.asp']
