import mariadb
import logging
import os
import configparser

logger = logging.getLogger("RSS_collector : " + __name__)

def load_db_conf(conf_path) :
    '''
    설정파일에서 DB 접속 정보 읽어와 config 객체 반환 ( 단일 책임상 get_connection()에서 분리 )
    param conf_path: main에서 설정파일 위치 경로 전달 ( 외부 의존성 주입 )
    '''
    # 설정파일 존부 체크 
    if not os.path.exists(conf_path) :
        logger.error(f"설정 파일 못찾았습니다 : {conf_path}")
        raise FileNotFoundError(f"설정파일 없음: {conf_path}")

    config = configparser.ConfigParser() # 객체 반환
    config.read(conf_path)

    # 설정 파일 내에 필요한 섹션이 있는지 검증
    if 'mariadb' not in config:
        logger.error("설정 파일에 '[mariadb]' 섹션이 없습니다.")
        raise KeyError("Missing '[mariadb]' section in config")
    
    return config



def get_connection(config):
    """
    MariaDB서버와 통신 채널 여는 기능, 파이썬-마리아디비 커넥터 mariadb 라이브러리
    connect() :MariaDB 연결 객체 반환 ( c에서 mysql_real_connect()역할 ) 
    
    config 객체에서 유저,비밀번호,호스트,포트 등 접속시 필요한 정보 추출
    
    param config : 메인에서 load_db_conf()가 반환한 config : ConfigParser 객체
    return conn : connect()결과 생성된 연결 객체
    """
    # TODO : 재시도 로직 for문, 지연시간 조절 : time.slee(2), 오류 조건부로 대응하게 설계, 상세 로그 기록
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
    

def insert_news_many(conn, data_list : list, table_name : str = "boannews_rss") :
    '''
    대량 뉴스 데이터 한번에 Mariadb서버에 저장
    conn.cursor() :
    cursor.exeutemany() : 리스트 내 여러개 데이터를 한번의 네트워크 통신으로 DB에 저장
    with - conn.commit() : 작업 종료시 커서를 자동으로 닫아 메모리 누수 방지
    conn.rollback() : 작업 실패시 이전 상태로 되돌아가 데이터 일관성 보장
    
    param conn : get_connection()으로 생성한 연결 객체
    param data_list : rss_ps모듈에 parse_feed()에서 만든 리스트[튜플묶음]
    '''
    sql: str=" "
    
    if not data_list :
        logger.warning("저장 데이터가 없음 작업 중단")
        return
    
    sql = f"""
    INSERT INTO {table_name} (
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
            cursor.executemany(sql, data_list)
            conn.commit()
            logger.info(f"DB에 데이터 저장 완료")
            
    except mariadb.Error as e:
        conn.rollback()
        logger.error(f"데이터 일괄 저장 중 오류 발생으로 rollback 수행 : {e}")
        raise e


if __name__ == "__main__" :
    try :
        current_dir_path = os.path.dirname(os.path.abspath(__file__)) # 현재파일 위치 : "/home/user/rss_collector/pkg" 
        parent_path = os.path.dirname(current_dir_path) # pkg상위 rss_collector 폴더 경로  : "/home/user/rss_collector"
        test_conf_path = os.path.join(parent_path, ".db_conn_conf.ini") # 최종 설정파일 전체 경로 : "/home/user/rss_collector/.db_conn_conf.ini"
        conf_obj = load_db_conf(test_conf_path) # 설정파일을 읽어 메모리에 올린 객체 [][] 접근가능
        conn = get_connection(conf_obj)         # 실제 MariaDB 서버와 연결된 세션 객체
        
        # 테스트 데이터 생성 [(튜플)] : idx, title, link, creator, written_dt, description, category
        test_data = [
            (999999, "테스트 제목 1", "https://t.com/1", "관리자", "2026-01-15 10:00:00", "내용1", "TEST"),
            (999998, "테스트 제목 2", "https://t.com/2", "관리자", "2026-01-15 10:00:00", "내용2", "TEST")
        ]
        # 데이터 삽입 테스트
        print("[*] 데이터 삽입 시도 중...")
        insert_news_many(conn, test_data, table_name = "test_news_tb")
        print("[+] 테스트 성공: DB를 확인해 보세요.")
    except Exception as e:
        print(f"[-] 테스트 실패: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("[*] DB 연결 종료")
