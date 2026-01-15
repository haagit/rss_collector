"""rss_ps 모듈 전체 실행 흐름
run_collection() 시작 -> get_rss() 호출 -> parse_feed()호출 -> 모든 데이터 하나의 리스트로 병합 -> main 반환
get_rss()            : rss모듈의 discover_feeds() 통해서 url 홈페이지 내 rss안내 페이지 url 추출 반환
parse_feed()         : idx, title, link, written_dt등 DB컬럼에 맞는 데이터 추출하여 튜플로 구성 반환

Raises: 해당 모듈 내 발생하는 모든 에러는 main으로 전파

"""

import logging
from . import rss
import feedparser
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime # datetime 모듈 안에서 datetime 클래스만 가져옴
from bs4 import BeautifulSoup

logger = logging.getLogger("RSS_collector : " + __name__) # 현재 모듈에 적용할 로거 생성

def get_rss() :
    '''
    보안뉴스 rss안내 페이지에서 카테고리별 xml주소 리스트 생성
    1. 메인에서 rss페이지 링크 검색 
    2. 카테고리별 xml주소와 이름 
    '''
    # 1.
    url = "https://www.boannews.com/"
    
    rss_asp_list = rss.discover_feeds(url) # discover_feeds()에러 발생시 바로 호출부 이동 -> rss_collection()
    if not rss_asp_list :
        # rss.py에서 에러처리 하여 error로그 찍었음. 여기서는 흐름만 기록
        logger.warning("활성화된 rss 안내 페이지 찾지 못했습니다.")
        raise Exception("홈페이지에서 RSS안내 페이지 리스트가 비어있습니다.")
    
    rss_asp = rss_asp_list[0]
    logger.debug(f"discover_feeds()결과 리스트 {rss_asp_list[0]}첫번째 요소")
        
    # 2.
    # TODO : 예외처리(Exception Handling) 네트워크연결끊김 or 서버에러시 프로그램 중단 방지 등 try영역 실행중 에러발생시 except로 점프 
    # 직접 통신부분만 예외처리 유지
    try :
        response = requests.get(rss_asp, timeout = 10)
        response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"rss안내 페이지 ({rss_asp}) 접속 실패 : {e}")
        raise e
    
    html = response.text
    soup = BeautifulSoup(html,"html.parser")          # BeautifulSoup 객체 soup 생성
    main_tag = soup.find("h1", string="메인 카테고리")  # "메인 카테고리"라는 텍스트가 들어있는 태그

    if main_tag:
        # h1 태그의 부모(td) -> 그 부모(tr)
        title_tr = main_tag.find_parent("tr")
    
        # 바로 아래에 실제 데이터가 있는 다음 줄(tr)로 이동
        data_tr = title_tr.find_next_sibling("tr")
    
        # rss 주소찾기 : input태그 중에서 rss주소 있는거
        target_inputs = data_tr.select('input[name="rss"]')
    
        rss_targets = []
        for inp in target_inputs:
            xml_url = inp.get('value')
        
            # 카테고리 이름은 같은 행(tr)의 첫 번째 칸(td)에서 가져옴.
            parent_tr = inp.find_parent('tr')
            category_name = parent_tr.find('td').get_text(strip=True)
        
            rss_targets.append({
                "category": category_name,
                "url": xml_url
            })
        # 태그는 찾았는데 결과 리스트가 비어있는 경우
        if not rss_targets :
            raise Exception("메인 카테고리 내 카테고리별 rss.xml 주소 리스트 찾지 못했습니다.")
        
        logger.info("메인 카테고리 내 카테고리별 rss.xml 주소 리스트 추출 성공 합니다")        
        return rss_targets
    # 메인 카테고리 자체를 찾지 못한 경우
    logger.error("메인 카테고리 태그 찾지 못함(사이트 구조 변경 의심)")
    raise Exception("메인 카테고리 태그를 찾을 수 없습니다.")

def parse_feed(target) :
    '''
    1. feedparser.parse() : 세부 카테고리의 url에 네트워크 통신접속 xml 데이터 다운로드 파이썬 객체로 파싱, 규격화된 구조 -> feedparser 사용
    2. 규격화된 rss/atom피드 전용 태그들 파싱
        2-1. urllib.parse 라이브러리 urlparse(),parse_qs() : db테이블 컬럼에 맞는 데이터 분리
        2-2. datetime 라이브러리 strptime() : datetime 객체로 반환 , 날짜 시간 형식 변환 
    3. return : 1개의 기사에 대한 컬럼 데이터 튜플들의 리스트로 구성(없으면 [])  -> run_collection()
                튜플 구조 (idx(int), title(str), link(str), creator(str), written_dt(str), description(str), category(str))
    param target : run_collection()에서 전달받은 카테고리 security, it, safety, SecurityWorld 순서로 {'category': 'IT', 'url': '...'} 형태
    '''
    collected_data = []
    logger.debug(f"파싱시작 카테고리 {target['category']}")
    
    # 1. rss 데이터 로드
    feed = feedparser.parse(target['url'])  # feedparser 내부적으로 네트워크 연결 실패시 빈 feed객체 반환
    if not feed.entries:
        logger.info(f"해당 [{target['category']}]에 새로운 기사가 없습니다.")
        return []
    
    # 2. 기사 순회 ( 각 기사별 예외 처리 )
    for entry in feed.entries : # feed.entries 리스트 하나씩 순회하며 개별 기사 접근
        try :
            target_link = entry.link
            logger.debug(f"접근 대상 기사 : {target_link}")
            # urllib.parse 라이브러리 : urlparse(), parse_qs() -> url내 ?idx=123 값을 찾아옴
            # urlparse() : url 에서 ? 뒷부분 질의문을 문자열로 남김
            target_query = urlparse(target_link).query
            # parse_qs() : 질의문 문자열을 딕트[list]로 변환, get(key) : key의 value        
            # get() : idx 키의 value 추출, 없으면 None 비어있으면 '' 반환 
            target_idx = parse_qs(target_query).get('idx',[None])[0] 
            if not target_idx :
                # None,'',0 등 false -> db저장 불가 해당 기사 건너뛰기
                logger.warning(f"idx 추출 실패: {target['category']} - {entry.title[:15]}")
                continue
            # 날짜 변환 (실패시 현재 시간 대체)
            raw_date = entry.get('published','')
            written_dt = ""
            if raw_date :
                try :
                    dt_obj = datetime.strptime(raw_date,'%a, %d, %b, %Y, %H:%M:%S %z')
                    # strftime() : datetime으로 포맷한 객체를 Mariadb DATETIME 형식(YYYY-MM-DD HH:MM:SS)으로 변환 후 문자열로 반환
                    written_dt = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e :
                    logger.warning(f"날짜 변환 실패 {raw_date}:{e}로 현재시간 대체")
                    written_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else :
                written_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
            news_data_set = (
            int(target_idx)                         # idx (Unique Key)
                ,entry.title.strip()                # title
                ,target_link                        # link
                ,entry.get('author','보안뉴스')      # creator
                ,written_dt                         # written_dt (변환된 날짜)
                ,entry.get('summary','')            # description
                ,target['category']                 # category
            )
            collected_data.append(news_data_set)
        except Exception as e :
            # 기사 한건마다 처리 중 발생하는 모든 예상치 못한 에러에 대해 전체 수집과정 멈추지 않고 지속.
            logger.error(f"기사 처리 중 예외 발생하여 해당 기사 건너뜁니다: {e}")
            continue
        
    return collected_data    

def run_collection():
    """
    전체 수집 프로세스
    1. get_rss() : rss 목록 리스트 가져오기
    2. parse_feed() : 각 카테고리 대상별 기사 파싱
    3. return : 최종 리스트 -> main
    """
    logger.info("보안뉴스 RSS 수집 run_collect() 시작")
    all_collected_data = []
    
    # 1. 
    # get_rss() 에러 발생시 여기서 바로 main.py로 향함 아래 for문 실행x
    targets = get_rss()
    
    # 2.
    for target in targets:
        logger.info(f"[*] 카테고리 수집 중: {target['category']}")
        category_news = parse_feed(target)
        all_collected_data.extend(category_news) # 리스트 합치기
        
    logger.info(f"수집 완료: 총 {len(all_collected_data)}건")
    return all_collected_data


if __name__ == "__main__":
    test_result = run_collection()
    
    if test_result :
        print(f"{len(test_result)} 수집 성공")
        logger.info(f"샘플 데이터 {test_result[0]}")