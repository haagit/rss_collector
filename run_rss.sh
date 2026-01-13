#! /bin/bash

# 1. 프로젝트 경로 설정 (실제 환경 확인)
PROJECT_DIR="/home/rdbbot/rss_collector"
LOG_FILE="$PROJECT_DIR/logs/app.log"

# 2. 작업 시작 알림
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === 쉘 스크립트 실행 시작 ===" >> $LOG_FILE

# 3. 가상환경 파이썬으로 main.py 실행 (조건부)
# && \ 는 앞의 명령이 성공(exit 0)했을 때만 다음 ( ) 안의 내용을 실행
$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/main.py >> $LOG_FILE 2>&1 && \
(
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [성공] 수집 완료. 14일 전 데이터 정리 시작..." >> $LOG_FILE
    # .my.cnf 에 유저계정 정보 있음 비밀번호 없이 실행됨.
    /usr/bin/mysql -e "DELETE FROM boannews_rss WHERE save_at < DATE_SUB(NOW(), INTERVAL 14 DAY);" news_hub >> $LOG_FILE 2>&1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [완료] 데이터 정리 공정 종료." >> $LOG_FILE
) || \
(
    # main.py에서 sys.exit(1)을 던지면 이쪽 ( )가 실행됩니다.
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [중단] 파이썬 에러 감지! 데이터 보호를 위해 삭제 공정을 건너뜁니다." >> $LOG_FILE
)

# 4. 전체 작업 종료 로그
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === 모든 스케줄 종료 ===" >> $LOG_FILE
echo "--------------------------------------------------" >> $LOG_FILE