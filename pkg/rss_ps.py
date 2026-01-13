import logging
from .logging_config import setup_logging
from . import rss
import feedparser
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime # datetime 모듈 안에서 datetime 클래스만 가져옴

setup_logging() # 설정 적용
logger = logging.getLogger(__name__) # 현재 모듈에 적용할 로거 생성

def get_rss() :
    '''
    Docstring for get_rss
    [ 보안뉴스 rss안내 페이지에서 카테고리별 xml주소 리스트 생성 ]
    '''
    # 1. [ 메인에서 rss페이지 링크 검색 ] #
    url = "https://www.boannews.com/"
    
    try :
        rss_asp_list = rss.discover_feeds(url)
    
        if not rss_asp_list :
            logger.error("rss페이지 못 찾음")
            return []
    
        rss_asp = rss_asp_list[0]
        
        # 2. [ 카테고리별 xml주소와 이름 ] #
        # TODO : 예외처리(Exception Handling) 네트워크연결끊김 or 서버에러시 프로그램 중단 방지 등 try영역 실행중 에러발생시 except로 점프 
        response = rss.requests.get(rss_asp, timeout = 10)
        response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        logger.exception(f"네트워크 연결 오류 : {e}")
        return []
    
    html = response.text
    soup = rss.BeautifulSoup(html,"html.parser")    # BeautifulSoup 객체 soup 생성
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
        
            # 카테고리 이름은 같은 행(tr)의 첫 번째 칸(td)에서 가져옵니다.
            parent_tr = inp.find_parent('tr')
            category_name = parent_tr.find('td').get_text(strip=True)
        
            rss_targets.append({
                "category": category_name,
                "url": xml_url
            })
            
        logger.info("메인 카테고리 내 카테고리별 xml 리스트 추출 성공 반환 합니다")
        return rss_targets
    logger.warning("메인 카테고리 태그 찾지 못함")
    return []

def parse_feed(target) :
    '''
    Docstring for parse_feed
    :param target: run_collection()에서 전달받은 카테고리
    '''
    collected_data = []
    logger.debug(f"파싱시작 카테고리 {target['category']}")
    
    feed = feedparser.parse(target['url'])
    if not feed.entries:
        print(f"   - 해당 카테고리에 기사가 없습니다.")
        return []

    # idx 추출 -> db테이블 컬럼에 맞는 데이터 분리
    # idx 추출 , 없으면 제외
    # urllib.parse 라이브러리
    # urlparse() : url 에서 ? 뒷부분인 질의문을 문자열로 남김
    # parse_qs() : 질의문 문자열을 딕셔너리 형태로 변환

    for entry in feed.entries :
        target_link = entry.link
        target_query = urlparse(target_link).query
        target_idx = parse_qs(target_query).get('idx',[None])[0]
        
        # 날짜 시간 형식 변환
        raw_date = entry.get('published','')
        written_dt = ""
        
        if raw_date :
            try :
                # 파이썬 datetime 객체로 변환
                dt_obj = datetime.strptime(raw_date,'%a, %d, %b, %Y, %H:%M:%S %z')
                # mariadb DATETIME 형식(YYYY-MM-DD HH:MM:SS)으로 변환
                written_dt = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
            
            except Exception as e :
                logger.warning(f"날짜 변환 실패 {raw_date}:{e}")
                written_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else :
            written_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # db테이블 컬럼 구성 고려 : 배열순서 주의, 1개의 기사에 대한 컬럼 데이터를 튜플로 구성
        # 컬럼 순서 title, link, creator, written_dt, description, category, idx
        # get() : feedparser 내장 함수 ('찾는거','없을때 기본값')
        if target_idx :
            news_data_set = (
            #     entry.title.strip()                 # <title> 필수
            #     ,target_link                        # <link>  필수
            #     ,entry.get('author','보안뉴스')       # <dc:creator> 
            #     ,entry.get('published','')           # <dc:date>
            #     ,entry.get('summary','')             # <description>
            #     ,target['category']
            #     ,target_idx
            # )
            int(target_idx)                         # idx (Unique Key)
                ,entry.title.strip()                # title
                ,target_link                        # link
                ,entry.get('author','보안뉴스')      # creator
                ,written_dt                         # written_dt (변환된 날짜)
                ,entry.get('summary','')            # description
                ,target['category']                 # category
            )
            
            collected_data.append(news_data_set)
        else :
            logger.warning(f"idx 추출 실패: {target['category']} - {entry.title[:15]}")
            #print(f"{target['category']}의 {i}번째 기사 타이틀 {entry.title[:15]} idx 찾기 실패")

    return collected_data    

def run_collection():
    """
    3단계: 전체 수집 프로세스.
    """
    logger.info("보안뉴스 RSS 수집 run_collect() 시작")
    all_collected_data = []
    
    # RSS 대상 목록 가져오기
    targets = get_rss()
    
    # 각 대상별로 기사 파싱
    for target in targets:
        print(f"[*] 카테고리 수집 중: {target['category']}")
        category_news = parse_feed(target)
        all_collected_data.extend(category_news) # 리스트 합치기
        
    logger.info(f"수집 완료: 총 {len(all_collected_data)}건")
    return all_collected_data


if __name__ == "__main__":
    test_result = run_collection()
    
    if test_result :
        print(f"{len(test_result)} 수집 성공")
        logger.info(f"샘플 데이터 {test_result[0]}")




# def run_collection() :
#     # 1. [ 메인에서 rss페이지 링크 검색 ] #
#     url = "https://www.boannews.com/"
#     rss_asp_list = rss.discover_feeds(url)
    
#     if not rss_asp_list :
#         #logger.error("rss페이지 못 찾음")
#         return 
    
#     rss_asp = rss_asp_list[0]
#     #logger.info("rss안내 페이지 :",rss_asp)
#     # print(rss_asp_list) # ['https://www.boannews.com/custom/news_rss.asp'] 리스트


#     # 2. [ 카테고리별 xml주소와 이름 ] #
#     # TODO : 예외처리(Exception Handling) 네트워크연결끊김 or 서버에러시 프로그램 중단 방지 등 try영역 실행중 에러발생시 except로 점프
#     # try  : 
#     response = rss.requests.get(rss_asp, timeout = 10)
#     response.raise_for_status()
#     html = response.text
    
#     # BeautifulSoup 객체 soup 생성
#     soup = rss.BeautifulSoup(html,"html.parser")

#     # "메인 카테고리"라는 텍스트가 들어있는 태그
#     main_tag = soup.find("h1", string="메인 카테고리")

#     if main_tag:
#         # h1 태그의 부모(td) -> 그 부모(tr)
#         title_tr = main_tag.find_parent("tr")
    
#         # 바로 아래에 실제 데이터가 있는 다음 줄(tr)로 이동
#         data_tr = title_tr.find_next_sibling("tr")
    
#         # rss 주소찾기 : input태그 중에서 rss주소 있는거
#         target_inputs = data_tr.select('input[name="rss"]')
    
#         rss_targets = []
#         for inp in target_inputs:
#             xml_url = inp.get('value')
        
#             # 카테고리 이름은 같은 행(tr)의 첫 번째 칸(td)에서 가져옵니다.
#             parent_tr = inp.find_parent('tr')
#             category_name = parent_tr.find('td').get_text(strip=True)
        
#             rss_targets.append({
#                 "category": category_name,
#                 "url": xml_url
#             })
                            
#     # 3. [ 파싱 작업 ]
#         collected_data = []
    
#         for target in rss_targets:
#             print(f" 카테고리 [{target['category']}]")
            
#             feed = feedparser.parse(target['url'])
#             if not feed.entries:
#                 print(f"   - 해당 카테고리에 기사가 없습니다.")
#                 continue

#             # idx 추출 -> db테이블 컬럼에 맞는 데이터 분리
#             # idx 추출 , 없으면 제외
#             # urllib.parse 라이브러리
#             # urlparse() : url 에서 ? 뒷부분인 질의문을 문자열로 남김
#             # parse_qs() : 질의문 문자열을 딕셔너리 형태로 변환

#             for i, entry in enumerate(feed.entries, start=1) :
#                 target_link = entry.link
#                 target_query = urlparse(target_link).query
#                 target_idx = parse_qs(target_query).get('idx',[None])[0]
            
#             # db테이블 컬럼 구성 고려 : 배열순서 주의, 1개의 기사에 대한 컬럼 데이터를 튜플로 구성
#             # 컬럼 순서 title, link, creator, written_dt, description, category, idx
#             # get() : feedparser 내장 함수 ('찾는거','없을때 기본값')
#                 if target_idx :
#                     news_data_set = (
#                         entry.title.strip() # <title> 필수
#                         ,target_link        # <link>  필수
#                         ,entry.get('author','보안뉴스')       # <dc:creator> 
#                         ,entry.get('published','')          # <dc:date>
#                         ,entry.get('summary','')            # <description>
#                         ,target['category']
#                         ,target_idx
#                     )
                
#                     collected_data.append(news_data_set)

#                 else :
#                     print(f"{target['category']}의 {i}번째 기사 타이틀 {entry.title[:15]} idx 찾기 실패")

#         return collected_data

#             # # 각 카테고리별로 상위 5개 기사 프린트 테스트
#             # for i, entry in enumerate(feed.entries[:5], start=1):
#             #     clean_title = entry.title.strip()
#             #     print(f"   {str(i).rjust(2)}) {clean_title}")
#             # print("-" * 50)
