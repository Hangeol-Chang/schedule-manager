"""
Schedule Manager 서브모듈 엔트리 포인트
리팩토링된 모듈형 구조
"""

import logging
import sys
import os

# 현재 모듈 경로를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 로컬 모듈 import
from api.schedule_router import router
from tasks.background_tasks import background_tasks

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("schedule-manager")

def get_router():
    """라우터 반환"""
    logger.info("Schedule Manager 라우터 로드 완료")
    return router

async def start_background_tasks():
    """백그라운드 태스크 시작"""
    await background_tasks.start_all_tasks()

# 모듈 초기화
logger.info("Schedule Manager 모듈 초기화 완료")