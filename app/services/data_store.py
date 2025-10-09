"""
Schedule Manager 데이터 저장소
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from models.task_models import ScheduledTask, TaskExecution, TaskStatus, TaskType

class ScheduleDataStore:
    """스케줄 데이터 저장소 클래스"""
    
    def __init__(self):
        self.data = {
            "tasks": {},
            "executions": {},
            "stats": {
                "total_tasks": 0,
                "completed_today": 0,
                "failed_today": 0,
                "last_cleanup": datetime.now()
            }
        }
        self.load_initial_data()
    
    def add_task(self, task: ScheduledTask) -> ScheduledTask:
        """작업 추가"""
        task.id = str(uuid.uuid4())
        task.created_at = datetime.now()
        task.updated_at = datetime.now()
        
        # next_run 계산
        if task.task_type == TaskType.ONCE:
            task.next_run = task.scheduled_time
        elif task.task_type == TaskType.RECURRING and task.interval_minutes:
            task.next_run = datetime.now() + timedelta(minutes=task.interval_minutes)
        
        self.data["tasks"][task.id] = task.dict()
        self.data["stats"]["total_tasks"] += 1
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """작업 조회"""
        return self.data["tasks"].get(task_id)
    
    def get_all_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict]:
        """모든 작업 조회"""
        tasks = list(self.data["tasks"].values())
        
        if status:
            tasks = [task for task in tasks if task["status"] == status]
        
        return tasks
    
    def update_task(self, task_id: str, updated_task: ScheduledTask) -> Optional[ScheduledTask]:
        """작업 업데이트"""
        if task_id not in self.data["tasks"]:
            return None
        
        updated_task.id = task_id
        updated_task.updated_at = datetime.now()
        self.data["tasks"][task_id] = updated_task.dict()
        
        return updated_task
    
    def delete_task(self, task_id: str) -> Optional[Dict]:
        """작업 삭제"""
        if task_id not in self.data["tasks"]:
            return None
        
        return self.data["tasks"].pop(task_id)
    
    def add_execution(self, execution: TaskExecution):
        """실행 기록 추가"""
        self.data["executions"][execution.execution_id] = execution.dict()
    
    def get_executions(self, task_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """실행 기록 조회"""
        executions = list(self.data["executions"].values())
        
        if task_id:
            executions = [exe for exe in executions if exe["task_id"] == task_id]
        
        # 최신순 정렬
        executions.sort(key=lambda x: x["started_at"], reverse=True)
        return executions[:limit]
    
    def update_execution(self, execution_id: str, execution: TaskExecution):
        """실행 기록 업데이트"""
        self.data["executions"][execution_id] = execution.dict()
    
    def get_pending_tasks(self) -> List[Dict]:
        """실행 대기 중인 작업들 반환"""
        now = datetime.now()
        pending_tasks = []
        
        for task in self.data["tasks"].values():
            if (task["status"] == TaskStatus.PENDING and 
                task.get("next_run") and 
                datetime.fromisoformat(task["next_run"]) <= now):
                pending_tasks.append(task)
        
        return pending_tasks
    
    def get_next_scheduled_tasks(self, limit: int = 5) -> List[Dict]:
        """다음 실행 예정인 작업들 반환"""
        tasks_with_next_run = [
            task for task in self.data["tasks"].values()
            if task.get("next_run") and task["status"] == TaskStatus.PENDING
        ]
        
        # next_run 기준으로 정렬
        tasks_with_next_run.sort(key=lambda x: x["next_run"])
        
        return tasks_with_next_run[:limit]
    
    def get_today_stats(self) -> Dict:
        """오늘 통계 계산"""
        today = datetime.now().date()
        
        today_executions = [
            exe for exe in self.data["executions"].values()
            if datetime.fromisoformat(exe["started_at"]).date() == today
        ]
        
        completed_today = len([exe for exe in today_executions if exe["status"] == TaskStatus.COMPLETED])
        failed_today = len([exe for exe in today_executions if exe["status"] == TaskStatus.FAILED])
        
        return {
            "completed_today": completed_today,
            "failed_today": failed_today,
            "total_executions_today": len(today_executions)
        }
    
    def cleanup_old_executions(self, days: int = 7):
        """오래된 실행 기록 정리"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        to_delete = []
        for exec_id, execution in self.data["executions"].items():
            if datetime.fromisoformat(execution["started_at"]) < cutoff_date:
                to_delete.append(exec_id)
        
        for exec_id in to_delete:
            del self.data["executions"][exec_id]
        
        self.data["stats"]["last_cleanup"] = datetime.now().isoformat()
        return len(to_delete)
    
    def load_initial_data(self):
        """초기 데이터 로드"""
        initial_tasks = [
            {
                "id": str(uuid.uuid4()),
                "name": "일일 백업",
                "description": "매일 자정 데이터베이스 백업",
                "task_type": TaskType.RECURRING,
                "status": TaskStatus.PENDING,
                "scheduled_time": datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
                "next_run": (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat(),
                "interval_minutes": 1440,  # 24시간
                "command": "backup_database",
                "parameters": {"backup_type": "full"},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "주간 보고서",
                "description": "매주 월요일 주간 보고서 생성",
                "task_type": TaskType.RECURRING,
                "status": TaskStatus.PENDING,
                "scheduled_time": datetime.now().isoformat(),
                "next_run": (datetime.now() + timedelta(minutes=5)).isoformat(),  # 5분 후 테스트 실행
                "interval_minutes": 10080,  # 7일
                "command": "send_report",
                "parameters": {"report_type": "weekly"},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        
        for task in initial_tasks:
            self.data["tasks"][task["id"]] = task
        
        self.data["stats"]["total_tasks"] = len(initial_tasks)

# 전역 데이터 저장소 인스턴스
schedule_store = ScheduleDataStore()