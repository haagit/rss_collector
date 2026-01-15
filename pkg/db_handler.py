"""
기존 db_conn.py의 함수들을 MariaDBHandler 클래스화
기능 확장시 코드 재사용성, DB연결,해제,삽입,설정로드 등 응집 측면에서 유용함

"""

import mariadb
import logging
import os
import time

