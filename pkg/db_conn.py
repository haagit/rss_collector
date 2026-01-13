# 마리아 디비 연동
import mariadb
import logging
import os
import configparser

logger = logging.getLogger("RSS_collector")

def load_db_conf(conf_path) :
    '''
    설정파일에서 DB 접속 정보 읽어와 config 객체 반환 ( 단일 책임 )
    :param conf_path: main에서 경로 전달 외부 의존성 주입
    '''
    if not os.path.exists(conf_path) :
        logger.error(f"설정 파일 못찾았습니다 : {conf_path}")
        raise FileNotFoundError(f"설정파일 없음: {conf_path}")

    config = configparser.ConfigParser() # 객체 반환
    config.read(conf_path)

    # 설정 파일 내에 필요한 섹션이 있는지 검증하는 로직을 넣기도 좋습니다. ?
    if 'mariadb' not in config:
        logger.error("설정 파일에 'mariadb' 섹션이 없습니다.")
        raise KeyError("Missing 'mariadb' section in config")
    
    return config



def get_connection(config):
    """
    MariaDB 연결 객체 반환 : c에서 mysql_real_connect()역할 
    """
    try:
        conn = mariadb.connect(
            user=config['mariadb']['user'],
            password=config['mariadb']['password'].strip("'"), # 따옴표가 있어도 제거
            host=config['mariadb']['host'],
            port=int(config['mariadb']['port']),
            database=config['mariadb']['database'] 
        )
        return conn
    
    except mariadb.Error as e:
        logger.error(f"MariaDB 연결 실패: {e}")
        raise e
    
    except KeyError as e:
        logger.error(f"설정 파일에서 키를 찾을 수 없습니다: {e}")
        raise e
    

def insert_news_many(conn, data_list : list) :
    '''
    대량 뉴스 데이터 한번에 저장
    :param conn: get_connection()으로 생성한 연결 객체
    :param data_list: rss_ps 에서 반환하는 튜플 리스트
    '''
    sql: str=" "
    
    if not data_list :
        logger.warning("저장 데이터가 없음 작업 중단")
        return
    
    sql = """
    INSERT INTO boannews_rss (
idx, title, link, creator, written_dt, description, category
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        title = VALUES(title),
        link = VALUES(link),
        creator = VALUES(creator),
        written_dt = VALUES(written_dt),
        description = VALUES(description),
        category = VALUES(category),
        save_at = CURRENT_TIMESTAMP        
    """
    
    try :
        # with문 : 커서 생성 ~ 자동 닫기(with블록 벗어날때)
        with conn.cursor() as cursor :
            # executemany : db와 한번 통신으로 대량 데이터 저장 가능
            cursor.executemany(sql, data_list)
            conn.commit()
            logger.info(f"DB에 데이터 저장 완료")
            
    except mariadb.Error as e:
        conn.rollback()
        logger.error(f"데이터 일괄 저장 중 오류 발생으로 rollback 수행 : {e}")
        raise e


if __name__ == "__main__" :
    try :
        conn = get_connection()
        
        # 2. 테스트 데이터 생성 (튜플 리스트 형태)
        # 컬럼 순서: title, link, creator, written_dt, description, category, idx
        test_data = [
            (
                "테스트 뉴스 제목 1", 
                "https://test.com/1", 
                "관리자", 
                "2026-01-12", 
                "테스트 내용입니다.", 
                "TEST", 
                999999  # 중복되지 않을 법한 큰 숫자로 테스트
            ),
            (
                "테스트 뉴스 제목 2", 
                "https://test.com/2", 
                "관리자", 
                "2026-01-12", 
                "두 번째 테스트 내용입니다.", 
                "TEST", 
                999998
            )
        ]
        # 3. 데이터 삽입 테스트
        print("[*] 데이터 삽입 시도 중...")
        insert_news_many(conn, test_data)
        print("[+] 테스트 성공: DB를 확인해 보세요.")
    except Exception as e:
        print(f"[-] 테스트 실패: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("[*] DB 연결 종료")
