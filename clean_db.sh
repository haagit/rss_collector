#!/bin/bash
# 파이썬 코드 거치지 않고 정해진 시간에 MariaDB에 직접 접속 -> Delete명령만 실행시킴
PROJECT_DIR="/home/rdbbot/rss_collector"
LOG_FILE="$PROJECT_DIR/logs/app.log"
MYSQL_BIN="/usr/bin/mysql"              # 리눅스에서 경로확인 which mysql

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [점검] 오전 9시 전 데이터 정리 (14일 경과 대상)" >> $LOG_FILE

# MariaDB 삭제 쿼리 실행
$MYSQL_BIN -e "DELETE FROM boannews_rss WHERE save_at < DATE_SUB(NOW(), INTERVAL 14 DAY);" news_hub >> $LOG_FILE 2>&1
# 리눅스 명령어 실행 실패시 종료코드 exit code = 0이 아닌 값(보통1)
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [완료] 데이터 삭제 성공 종료." >> $LOG_FILE
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [에러] 데이터 삭제 중 오류 발생 (DB연결확인필요)." >> $LOG_FILE
fi