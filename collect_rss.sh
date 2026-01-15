#!/bin/bash

# 경로 설정 (리눅스에서 확인 필요)
PROJECT_DIR="/home/rdbbot/rss_collector"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python3"
LOG_FILE="$PROJECT_DIR/logs/app.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === 수집 프로세스 시작 ===" >> $LOG_FILE

# 파이썬 실행 : 로그파일 열기 -> 가상환경 파이썬 활성화 -> main.py를 파이썬 실행기에 -> 실행 및 기록 -> 종료시 종료코드를 쉘에 남김 if구문으로 연결
# 에러메세지(2:stderr)도 > &정상메세지(1:stdout)에 합쳐 보냄 (&:파일디스크립터 의미 기호)
#   ㄴ 붙이지 않으면 정상 메세지만 로그파일에 찍히고 에러 메세지는 찾기 어려워짐
$PYTHON_BIN $PROJECT_DIR/main.py >> $LOG_FILE 2>&1

# 실행 결과 확인 (Exit Code)
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [성공] 수집 및 DB 저장 완료." >> $LOG_FILE
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [실패] collect_db.sh 오류 발생. 로그를 확인하세요." >> $LOG_FILE
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === 수집 프로세스 종료 ===" >> $LOG_FILE