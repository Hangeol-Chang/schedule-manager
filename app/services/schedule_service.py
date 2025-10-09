"""
스케줄 관리 서비스
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from models.task_models import ScheduledTask, TaskExecution, TaskStatus, TaskType
from services.data_store import schedule_store

logger = logging.getLogger("schedule-service")

class ScheduleService:
    """스케줄 관리 서비스"""
    
    def __init__(self):
        self.store = schedule_store
    
    def create_task(self, task: ScheduledTask) -> ScheduledTask:
        """새로운 스케줄 작업 생성"""
        created_task = self.store.add_task(task)
        logger.info(f"새 스케줄 작업 생성됨: {task.name} (ID: {created_task.id})")
        return created_task
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """특정 작업 조회"""
        task_data = self.store.get_task(task_id)
        if task_data:
            return ScheduledTask(**task_data)
        return None
    
    def get_all_tasks(self, status: Optional[TaskStatus] = None) -> List[ScheduledTask]:
        """스케줄된 작업 목록 조회"""
        tasks_data = self.store.get_all_tasks(status)
        return [ScheduledTask(**task) for task in tasks_data]
    
    def update_task(self, task_id: str, updated_task: ScheduledTask) -> Optional[ScheduledTask]:
        """작업 정보 업데이트"""
        result = self.store.update_task(task_id, updated_task)
        if result:
            logger.info(f"작업 업데이트됨: {task_id}")
            return result
        return None
    
    def delete_task(self, task_id: str) -> Optional[Dict]:
        """작업 삭제"""
        deleted_task = self.store.delete_task(task_id)
        if deleted_task:
            logger.info(f"작업 삭제됨: {task_id}")
            return {"message": f"작업 {task_id}가 삭제되었습니다", "deleted_task": deleted_task}
        return None
    
    async def execute_task(self, task_id: str):
        """작업 즉시 실행"""
        task_data = self.store.get_task(task_id)
        if not task_data:
            logger.error(f"작업 {task_id}를 찾을 수 없습니다")
            return
        
        await self._execute_task_internal(task_id, task_data)
    
    async def _execute_task_internal(self, task_id: str, task_data: Dict):
        """내부 작업 실행 로직"""
        execution_id = str(uuid.uuid4())
        
        # 실행 기록 생성
        execution = TaskExecution(
            task_id=task_id,
            execution_id=execution_id,
            started_at=datetime.now(),
            status=TaskStatus.RUNNING
        )
        
        self.store.add_execution(execution)
        
        # 작업 상태 업데이트
        task_data["status"] = TaskStatus.RUNNING
        task_data["last_run"] = datetime.now().isoformat()
        self.store.data["tasks"][task_id] = task_data
        
        logger.info(f"작업 실행 시작: {task_data['name']} (ID: {task_id})")
        
        try:
            # 실제 작업 실행
            result = await self._execute_command(task_data["command"], task_data.get("parameters", {}))
            
            # 성공 처리
            execution.completed_at = datetime.now()
            execution.status = TaskStatus.COMPLETED
            execution.result = result
            task_data["status"] = TaskStatus.COMPLETED
            
            # 반복 작업인 경우 다음 실행 시간 설정
            if task_data["task_type"] == TaskType.RECURRING and task_data.get("interval_minutes"):
                next_run = datetime.now() + timedelta(minutes=task_data["interval_minutes"])
                task_data["next_run"] = next_run.isoformat()
                task_data["status"] = TaskStatus.PENDING
            
            logger.info(f"작업 실행 완료: {task_data['name']} - {result}")
            
        except Exception as e:
            # 실패 처리
            execution.completed_at = datetime.now()
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)
            task_data["status"] = TaskStatus.FAILED
            
            logger.error(f"작업 실행 실패: {task_data['name']} - {e}")
        
        # 실행 기록 업데이트
        self.store.update_execution(execution_id, execution)
        self.store.data["tasks"][task_id] = task_data
    
    async def _execute_command(self, command: str, parameters: Dict) -> str:
        """명령어 실행"""
        if command == "backup_database":
            await asyncio.sleep(2)  # 모의 백업 시간
            return "데이터베이스 백업 완료"
        
        elif command == "send_report":
            await asyncio.sleep(1)
            return f"보고서 전송 완료: {parameters.get('report_type', 'default')}"
        
        elif command == "cleanup_logs":
            await asyncio.sleep(0.5)
            return "로그 파일 정리 완료"
        
        elif command == "sync_external_data":
            await asyncio.sleep(3)
            return "외부 데이터 동기화 완료"
        
        else:
            # 기본 명령어 실행
            await asyncio.sleep(1)
            return f"명령어 '{command}' 실행 완료"
    
    def get_executions(self, task_id: Optional[str] = None, limit: int = 50) -> List[TaskExecution]:
        """작업 실행 기록 조회"""
        executions_data = self.store.get_executions(task_id, limit)
        return [TaskExecution(**exe) for exe in executions_data]
    
    def get_statistics(self) -> Dict:
        """스케줄러 통계 정보"""
        today_stats = self.store.get_today_stats()
        
        # 상태별 작업 수
        status_counts = {}
        for status in TaskStatus:
            count = len([task for task in self.store.data["tasks"].values() if task["status"] == status])
            status_counts[status] = count
        
        return {
            "total_tasks": len(self.store.data["tasks"]),
            "completed_today": today_stats["completed_today"],
            "failed_today": today_stats["failed_today"],
            "total_executions": len(self.store.data["executions"]),
            "status_breakdown": status_counts,
            "next_scheduled_tasks": self.store.get_next_scheduled_tasks()
        }
    
    def get_health_status(self) -> Dict:
        """헬스 상태 조회"""
        return {
            "status": "healthy",
            "service": "schedule-manager",
            "total_tasks": len(self.store.data["tasks"]),
            "running_tasks": len([t for t in self.store.data["tasks"].values() if t["status"] == TaskStatus.RUNNING]),
            "scheduler_active": True
        }
    
    async def process_pending_tasks(self):
        """대기 중인 작업들 처리"""
        pending_tasks = self.store.get_pending_tasks()
        
        for task_data in pending_tasks:
            await self._execute_task_internal(task_data["id"], task_data)

# 전역 서비스 인스턴스
schedule_service = ScheduleService()