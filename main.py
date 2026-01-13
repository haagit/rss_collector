from pkg import run_collection, get_connection, insert_news_many
from pkg.logging_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)

def main() :
    logger.info("main : 보안뉴스 수집 및 db 저장 시작")
    list_news = run_collection()
    
    if not list_news:
        logger.warning("수집된 뉴스 데이터 없습니다. 작업을 종료합니다.")
        return
    
    conn = None
    try :
        # if conn is None: 삭제해 가독성 향상
        conn = get_connection()
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
