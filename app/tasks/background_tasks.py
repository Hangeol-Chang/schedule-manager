"""
Schedule Manager 백그라운드 태스크
"""

import asyncio
import logging
from services.schedule_service import schedule_service

logger = logging.getLogger("schedule-tasks")

class ScheduleBackgroundTasks:
    """스케줄 관리 백그라운드 태스크 클래스"""
    
    async def task_scheduler(self):
        """작업 스케줄러 - 예정된 작업들을 실행"""
        while True:
            try:
                # 대기 중인 작업들 처리
                await schedule_service.process_pending_tasks()
                
                # 30초마다 체크
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"스케줄러 오류: {e}")
                await asyncio.sleep(60)
    
    async def cleanup_old_executions(self):
        """오래된 실행 기록 정리"""
        while True:
            try:
                # 7일 이전 실행 기록 삭제
                deleted_count = schedule_service.store.cleanup_old_executions(days=7)
                
                if deleted_count > 0:
                    logger.info(f"오래된 실행 기록 {deleted_count}개 정리됨")
                
                # 24시간마다 정리
                await asyncio.sleep(86400)
                
            except Exception as e:
                logger.error(f"실행 기록 정리 오류: {e}")
                await asyncio.sleep(3600)
    
    async def start_all_tasks(self):
        """모든 백그라운드 태스크 시작"""
        logger.info("Schedule Manager 백그라운드 태스크 시작")
        
        # 백그라운드 태스크들을 비동기로 실행
        tasks = [
            self.task_scheduler(),
            self.cleanup_old_executions()
        ]
        
        # 태스크들을 동시에 실행하되 오류가 발생해도 다른 태스크는 계속 실행
        await asyncio.gather(*tasks, return_exceptions=True)

# 전역 백그라운드 태스크 인스턴스
background_tasks = ScheduleBackgroundTasks()