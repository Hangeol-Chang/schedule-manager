"""
Schedule Manager 서브모듈
일정 관리 및 작업 스케줄링 기능을 제공하는 FastAPI 라우터와 백그라운드 태스크
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import json
import os
from enum import Enum
import uuid

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("schedule-manager")

# 데이터 모델
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    ONCE = "once"           # 일회성
    RECURRING = "recurring" # 반복
    CRON = "cron"          # 크론 스타일

class ScheduledTask(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    scheduled_time: datetime
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    cron_expression: Optional[str] = None  # "0 9 * * 1-5" (평일 9시)
    interval_minutes: Optional[int] = None  # 반복 간격 (분)
    command: str  # 실행할 명령어 또는 함수명
    parameters: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class TaskExecution(BaseModel):
    task_id: str
    execution_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: TaskStatus
    result: Optional[str] = None
    error_message: Optional[str] = None

# 메모리 데이터 저장소 (실제로는 DB 연결 필요)
schedule_data = {
    "tasks": {},
    "executions": {},
    "stats": {
        "total_tasks": 0,
        "completed_today": 0,
        "failed_today": 0,
        "last_cleanup": datetime.now()
    }
}

# FastAPI 라우터 생성
router = APIRouter()

@router.get("/", tags=["Schedule Manager"])
async def schedule_manager_root():
    """Schedule Manager 루트 엔드포인트"""
    return {
        "service": "Schedule Manager",
        "version": "1.0.0",
        "description": "일정 관리 및 작업 스케줄링 서비스",
        "endpoints": {
            "tasks": "/schedule-manager/tasks",
            "create_task": "/schedule-manager/tasks (POST)",
            "executions": "/schedule-manager/executions",
            "stats": "/schedule-manager/stats"
        }
    }

@router.get("/tasks", response_model=List[ScheduledTask], tags=["Tasks"])
async def get_tasks(status: Optional[TaskStatus] = None):
    """스케줄된 작업 목록 조회"""
    tasks = list(schedule_data["tasks"].values())
    
    if status:
        tasks = [task for task in tasks if task["status"] == status]
    
    return [ScheduledTask(**task) for task in tasks]

@router.post("/tasks", response_model=ScheduledTask, tags=["Tasks"])
async def create_task(task: ScheduledTask):
    """새로운 스케줄 작업 생성"""
    # ID 생성
    task.id = str(uuid.uuid4())
    task.created_at = datetime.now()
    task.updated_at = datetime.now()
    
    # next_run 계산
    if task.task_type == TaskType.ONCE:
        task.next_run = task.scheduled_time
    elif task.task_type == TaskType.RECURRING and task.interval_minutes:
        task.next_run = datetime.now() + timedelta(minutes=task.interval_minutes)
    
    # 작업 저장
    schedule_data["tasks"][task.id] = task.dict()
    schedule_data["stats"]["total_tasks"] += 1
    
    logger.info(f"새 스케줄 작업 생성됨: {task.name} (ID: {task.id})")
    return task

@router.get("/tasks/{task_id}", response_model=ScheduledTask, tags=["Tasks"])
async def get_task(task_id: str):
    """특정 작업 조회"""
    if task_id not in schedule_data["tasks"]:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    return ScheduledTask(**schedule_data["tasks"][task_id])

@router.put("/tasks/{task_id}", response_model=ScheduledTask, tags=["Tasks"])
async def update_task(task_id: str, updated_task: ScheduledTask):
    """작업 정보 업데이트"""
    if task_id not in schedule_data["tasks"]:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    updated_task.id = task_id
    updated_task.updated_at = datetime.now()
    schedule_data["tasks"][task_id] = updated_task.dict()
    
    logger.info(f"작업 업데이트됨: {task_id}")
    return updated_task

@router.delete("/tasks/{task_id}", tags=["Tasks"])
async def delete_task(task_id: str):
    """작업 삭제"""
    if task_id not in schedule_data["tasks"]:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    deleted_task = schedule_data["tasks"].pop(task_id)
    logger.info(f"작업 삭제됨: {task_id}")
    return {"message": f"작업 {task_id}가 삭제되었습니다", "deleted_task": deleted_task}

@router.post("/tasks/{task_id}/execute", tags=["Tasks"])
async def execute_task_now(task_id: str, background_tasks: BackgroundTasks):
    """작업 즉시 실행"""
    if task_id not in schedule_data["tasks"]:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    background_tasks.add_task(execute_task, task_id)
    return {"message": f"작업 {task_id} 실행이 시작되었습니다"}

@router.get("/executions", response_model=List[TaskExecution], tags=["Executions"])
async def get_executions(task_id: Optional[str] = None, limit: int = 50):
    """작업 실행 기록 조회"""
    executions = list(schedule_data["executions"].values())
    
    if task_id:
        executions = [exe for exe in executions if exe["task_id"] == task_id]
    
    # 최신순 정렬
    executions.sort(key=lambda x: x["started_at"], reverse=True)
    executions = executions[:limit]
    
    return [TaskExecution(**exe) for exe in executions]

@router.get("/stats", tags=["Statistics"])
async def get_statistics():
    """스케줄러 통계 정보"""
    today = datetime.now().date()
    
    # 오늘 실행된 작업 통계 계산
    today_executions = [
        exe for exe in schedule_data["executions"].values()
        if datetime.fromisoformat(exe["started_at"]).date() == today
    ]
    
    completed_today = len([exe for exe in today_executions if exe["status"] == TaskStatus.COMPLETED])
    failed_today = len([exe for exe in today_executions if exe["status"] == TaskStatus.FAILED])
    
    # 상태별 작업 수
    status_counts = {}
    for status in TaskStatus:
        count = len([task for task in schedule_data["tasks"].values() if task["status"] == status])
        status_counts[status] = count
    
    return {
        "total_tasks": len(schedule_data["tasks"]),
        "completed_today": completed_today,
        "failed_today": failed_today,
        "total_executions": len(schedule_data["executions"]),
        "status_breakdown": status_counts,
        "next_scheduled_tasks": get_next_scheduled_tasks()
    }

@router.get("/health", tags=["Health"])
async def health_check():
    """Schedule Manager 헬스 체크"""
    return {
        "status": "healthy",
        "service": "schedule-manager",
        "total_tasks": len(schedule_data["tasks"]),
        "running_tasks": len([t for t in schedule_data["tasks"].values() if t["status"] == TaskStatus.RUNNING]),
        "scheduler_active": True
    }

# 헬퍼 함수들
def get_next_scheduled_tasks(limit: int = 5) -> List[Dict]:
    """다음 실행 예정인 작업들 반환"""
    tasks_with_next_run = [
        task for task in schedule_data["tasks"].values()
        if task.get("next_run") and task["status"] == TaskStatus.PENDING
    ]
    
    # next_run 기준으로 정렬
    tasks_with_next_run.sort(key=lambda x: x["next_run"])
    
    return tasks_with_next_run[:limit]

async def execute_task(task_id: str):
    """작업 실행"""
    if task_id not in schedule_data["tasks"]:
        logger.error(f"작업 {task_id}를 찾을 수 없습니다")
        return
    
    task = schedule_data["tasks"][task_id]
    execution_id = str(uuid.uuid4())
    
    # 실행 기록 생성
    execution = {
        "task_id": task_id,
        "execution_id": execution_id,
        "started_at": datetime.now().isoformat(),
        "status": TaskStatus.RUNNING,
        "result": None,
        "error_message": None
    }
    
    schedule_data["executions"][execution_id] = execution
    schedule_data["tasks"][task_id]["status"] = TaskStatus.RUNNING
    schedule_data["tasks"][task_id]["last_run"] = datetime.now().isoformat()
    
    logger.info(f"작업 실행 시작: {task['name']} (ID: {task_id})")
    
    try:
        # 실제 작업 실행 (여기서는 모의 실행)
        result = await execute_command(task["command"], task.get("parameters", {}))
        
        # 성공 처리
        execution["completed_at"] = datetime.now().isoformat()
        execution["status"] = TaskStatus.COMPLETED
        execution["result"] = result
        schedule_data["tasks"][task_id]["status"] = TaskStatus.COMPLETED
        
        # 반복 작업인 경우 다음 실행 시간 설정
        if task["task_type"] == TaskType.RECURRING and task.get("interval_minutes"):
            next_run = datetime.now() + timedelta(minutes=task["interval_minutes"])
            schedule_data["tasks"][task_id]["next_run"] = next_run.isoformat()
            schedule_data["tasks"][task_id]["status"] = TaskStatus.PENDING
        
        logger.info(f"작업 실행 완료: {task['name']} - {result}")
        
    except Exception as e:
        # 실패 처리
        execution["completed_at"] = datetime.now().isoformat()
        execution["status"] = TaskStatus.FAILED
        execution["error_message"] = str(e)
        schedule_data["tasks"][task_id]["status"] = TaskStatus.FAILED
        
        logger.error(f"작업 실행 실패: {task['name']} - {e}")
    
    # 실행 기록 업데이트
    schedule_data["executions"][execution_id] = execution

async def execute_command(command: str, parameters: Dict) -> str:
    """명령어 실행 (모의)"""
    # 실제로는 여기서 다양한 작업을 수행
    # 예: 데이터베이스 백업, 이메일 발송, API 호출 등
    
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

# 백그라운드 태스크들
async def task_scheduler():
    """작업 스케줄러 - 예정된 작업들을 실행"""
    while True:
        try:
            now = datetime.now()
            
            # 실행할 작업들 찾기
            for task_id, task in schedule_data["tasks"].items():
                if (task["status"] == TaskStatus.PENDING and 
                    task.get("next_run") and 
                    datetime.fromisoformat(task["next_run"]) <= now):
                    
                    # 작업 실행
                    await execute_task(task_id)
            
            # 30초마다 체크
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"스케줄러 오류: {e}")
            await asyncio.sleep(60)

async def cleanup_old_executions():
    """오래된 실행 기록 정리"""
    while True:
        try:
            # 7일 이전 실행 기록 삭제
            cutoff_date = datetime.now() - timedelta(days=7)
            
            to_delete = []
            for exec_id, execution in schedule_data["executions"].items():
                if datetime.fromisoformat(execution["started_at"]) < cutoff_date:
                    to_delete.append(exec_id)
            
            for exec_id in to_delete:
                del schedule_data["executions"][exec_id]
            
            if to_delete:
                logger.info(f"오래된 실행 기록 {len(to_delete)}개 정리됨")
            
            schedule_data["stats"]["last_cleanup"] = datetime.now().isoformat()
            
            # 24시간마다 정리
            await asyncio.sleep(86400)
            
        except Exception as e:
            logger.error(f"실행 기록 정리 오류: {e}")
            await asyncio.sleep(3600)

# 모듈 인터페이스 함수들
def get_router():
    """라우터 반환"""
    return router

async def start_background_tasks():
    """백그라운드 태스크 시작"""
    logger.info("Schedule Manager 백그라운드 태스크 시작")
    
    # 백그라운드 태스크들을 비동기로 실행
    tasks = [
        task_scheduler(),
        cleanup_old_executions()
    ]
    
    # 태스크들을 동시에 실행하되 오류가 발생해도 다른 태스크는 계속 실행
    await asyncio.gather(*tasks, return_exceptions=True)

# 초기 데이터 로드
def load_initial_data():
    """초기 스케줄 작업 데이터 로드 (예제)"""
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
        schedule_data["tasks"][task["id"]] = task
    
    schedule_data["stats"]["total_tasks"] = len(initial_tasks)
    logger.info("초기 스케줄 데이터 로드 완료")

# 모듈 초기화
load_initial_data()