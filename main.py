from pkg import run_collection, get_connection, insert_news_many
from pkg.logging_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)

def main() :
    logger.info("main : 보안뉴스 수집 및 db 저장 시작")
    list_news = run_collection()
    
    if not list_news:
        logger.warning("수집된 뉴스 데이터 없음")
        return
    
    conn = None
    try :
        conn = get_connection()
        
        if conn is None :
            logger.error("DB연결 실패")
            print("db연결 설정 확인하세요")
            return

        insert_news_many(conn, list_news)
        logger.info("정상 종료")
        print(f"{len(list_news)}건의 뉴스가 db에 저장되었습니다")
        
    except Exception as e:
        # db연결 실패 등 모든 에러 여기서 기록 get_connection()에서 에러 올려보낸 경우
        logger.error(f"메인 실행 중 오류 발생 : {e}")
        print(f"에러 발생 {e}")
    finally:
        if conn:
            conn.close()
            logger.info("db연결 안전하게 닫힘")
            print("모든 작업 완료 연결 종료")
            
if __name__ == "__main__" :
    main()
