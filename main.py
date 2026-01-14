from pkg.db_conn import load_db_conf, get_connection, insert_news_many
from pkg.rss_ps import run_collection
from pkg.logging_config import setup_logging
import logging
import os
import sys  # 시스템 종료 코드 보냄

logger = logging.getLogger("RSS_collector : " + __name__)

def main() :
    
    setup_logging()
    logger.info("main : 보안뉴스 수집 및 db 저장 시작")
    
    # 파일 경로 설정 : __file__은 현재 이 파일의 위치, os.path 사용해서 상위폴더 경로 찾기
    # conf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),'.db_conn_conf.ini')
    # os.path.dirname(os.path.dirname(__file__)) : /home/rdbbot -> db연동 정보 못찾아서 에러남
    # os.path.dirname(__file__): /home/rdbbot/rss_collector  설정파일 여기있음
    # __file__ : /home/rdbbot/rss_collector/main.py
    conf_path = os.path.join(os.path.dirname(__file__), '.db_conn_conf.ini')
    
    conn = None
    
    try :
        list_news = run_collection()
        if not list_news:
            logger.warning("수집된 뉴스 데이터 없습니다. 작업을 종료합니다.")
            return  # 에러아님 정상종료(exit 0), 삭제로직 실행가능
        
        # DB 작업
        db_config = load_db_conf(conf_path)
        conn = get_connection(db_config)
        insert_news_many(conn, list_news)
        logger.info("정상 종료")
        
    except Exception as e:
        # 수집,db연결 실패 등 모든 에러 모임
        # get_connection()에서는 logger.error() 여기서는 critical 로그레벨로 차이를 두어 로그 필터링 고려
        logger.critical(f"프로젝트 실행 중 오류 발생 실행 중단: {e}")
        # 연결이 제되로 안되는등 비정상 종료시 데이터 삭제 방지위한 신호 보냄
        sys.exit(1)
        
    finally:
        if conn:
            conn.close()
            logger.info("db연결 안전하게 닫힘")
            
if __name__ == "__main__" :
    main()
