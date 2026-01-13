from pkg.db_conn import load_db_conf, get_connection, insert_news_many
from pkg.rss_ps import run_collection
from pkg.logging_config import setup_logging
import logging
import os

logger = logging.getLogger("RSS_collector")

def main() :
    
    setup_logging()
    logger.info("main : 보안뉴스 수집 및 db 저장 시작")
    
    list_news = run_collection()
    
    if not list_news:
        logger.warning("수집된 뉴스 데이터 없습니다. 작업을 종료합니다.")
        return
    
    # 파일 경로 설정 : __file__은 현재 이 파일의 위치, os.path 사용해서 상위폴더 설정 찾기
    conf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),'.db_conn_conf.ini')
    conn = None
    
    try :
        db_config = load_db_conf(conf_path)
        conn = get_connection(db_config)
        insert_news_many(conn, list_news)
        logger.info("정상 종료")
        
    except Exception as e:
        # db연결 실패 등 모든 에러 get_connection()에서는 logger.error()
        # 여기서는 critical 로그레벨로 차이를 두어 로그 필터링 고려
        logger.critical(f"프로젝트 실행 중 오류 발생 실행 중단: {e}")
        
    finally:
        if conn:
            conn.close()
            logger.info("db연결 안전하게 닫힘")
            print("모든 작업 완료 연결 종료")
            
if __name__ == "__main__" :
    main()
