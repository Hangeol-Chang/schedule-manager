"""
Schedule Manager API 라우터
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from models.task_models import ScheduledTask, TaskExecution, TaskStatus
from services.schedule_service import schedule_service

# 라우터 생성
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
    return schedule_service.get_all_tasks(status)

@router.post("/tasks", response_model=ScheduledTask, tags=["Tasks"])
async def create_task(task: ScheduledTask):
    """새로운 스케줄 작업 생성"""
    return schedule_service.create_task(task)

@router.get("/tasks/{task_id}", response_model=ScheduledTask, tags=["Tasks"])
async def get_task(task_id: str):
    """특정 작업 조회"""
    task = schedule_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    return task

@router.put("/tasks/{task_id}", response_model=ScheduledTask, tags=["Tasks"])
async def update_task(task_id: str, updated_task: ScheduledTask):
    """작업 정보 업데이트"""
    result = schedule_service.update_task(task_id, updated_task)
    if not result:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    return result

@router.delete("/tasks/{task_id}", tags=["Tasks"])
async def delete_task(task_id: str):
    """작업 삭제"""
    result = schedule_service.delete_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    return result

@router.post("/tasks/{task_id}/execute", tags=["Tasks"])
async def execute_task_now(task_id: str, background_tasks: BackgroundTasks):
    """작업 즉시 실행"""
    task = schedule_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    background_tasks.add_task(schedule_service.execute_task, task_id)
    return {"message": f"작업 {task_id} 실행이 시작되었습니다"}

@router.get("/executions", response_model=List[TaskExecution], tags=["Executions"])
async def get_executions(task_id: Optional[str] = None, limit: int = 50):
    """작업 실행 기록 조회"""
    return schedule_service.get_executions(task_id, limit)

@router.get("/stats", tags=["Statistics"])
async def get_statistics():
    """스케줄러 통계 정보"""
    return schedule_service.get_statistics()

@router.get("/health", tags=["Health"])
async def health_check():
    """Schedule Manager 헬스 체크"""
    return schedule_service.get_health_status()