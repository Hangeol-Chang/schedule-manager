from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date, time
import uuid

router = APIRouter()

# 데이터 모델
class Schedule(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    category: str = "기타"
    priority: str = "medium"  # "low", "medium", "high"
    completed: bool = False

class Task(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: str = "medium"
    completed: bool = False
    category: str = "일반"

# 메모리 저장소 (실제로는 데이터베이스 사용)
schedules_db = []
tasks_db = []

# 일정 API
@router.get("/schedules", response_model=List[Schedule])
async def get_schedules(date_from: Optional[str] = None, date_to: Optional[str] = None):
    """일정 목록 조회"""
    result = schedules_db
    
    if date_from:
        result = [s for s in result if s["start_date"] >= date_from]
    if date_to:
        result = [s for s in result if s["start_date"] <= date_to]
    
    return result

@router.post("/schedules", response_model=Schedule)
async def create_schedule(schedule: Schedule):
    """일정 생성"""
    schedule.id = str(uuid.uuid4())
    schedules_db.append(schedule.dict())
    return schedule

@router.put("/schedules/{schedule_id}", response_model=Schedule)
async def update_schedule(schedule_id: str, schedule: Schedule):
    """일정 수정"""
    for i, s in enumerate(schedules_db):
        if s["id"] == schedule_id:
            schedule.id = schedule_id
            schedules_db[i] = schedule.dict()
            return schedule
    raise HTTPException(status_code=404, detail="Schedule not found")

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """일정 삭제"""
    for i, s in enumerate(schedules_db):
        if s["id"] == schedule_id:
            del schedules_db[i]
            return {"message": "Schedule deleted"}
    raise HTTPException(status_code=404, detail="Schedule not found")

# 할일 API
@router.get("/tasks", response_model=List[Task])
async def get_tasks(completed: Optional[bool] = None):
    """할일 목록 조회"""
    result = tasks_db
    
    if completed is not None:
        result = [t for t in result if t["completed"] == completed]
    
    return result

@router.post("/tasks", response_model=Task)
async def create_task(task: Task):
    """할일 생성"""
    task.id = str(uuid.uuid4())
    tasks_db.append(task.dict())
    return task

@router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task: Task):
    """할일 수정"""
    for i, t in enumerate(tasks_db):
        if t["id"] == task_id:
            task.id = task_id
            tasks_db[i] = task.dict()
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@router.patch("/tasks/{task_id}/complete")
async def toggle_task_completion(task_id: str):
    """할일 완료 상태 토글"""
    for i, t in enumerate(tasks_db):
        if t["id"] == task_id:
            tasks_db[i]["completed"] = not tasks_db[i]["completed"]
            return {"message": "Task completion toggled", "completed": tasks_db[i]["completed"]}
    raise HTTPException(status_code=404, detail="Task not found")

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """할일 삭제"""
    for i, t in enumerate(tasks_db):
        if t["id"] == task_id:
            del tasks_db[i]
            return {"message": "Task deleted"}
    raise HTTPException(status_code=404, detail="Task not found")

# 통계 API
@router.get("/stats/summary")
async def get_summary():
    """요약 통계"""
    total_schedules = len(schedules_db)
    completed_schedules = len([s for s in schedules_db if s.get("completed", False)])
    
    total_tasks = len(tasks_db)
    completed_tasks = len([t for t in tasks_db if t["completed"]])
    pending_tasks = total_tasks - completed_tasks
    
    # 오늘 일정
    today = date.today().isoformat()
    today_schedules = len([s for s in schedules_db if s["start_date"] == today])
    
    return {
        "total_schedules": total_schedules,
        "completed_schedules": completed_schedules,
        "today_schedules": today_schedules,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks
    }

@router.get("/today")
async def get_today_items():
    """오늘 일정과 할일"""
    today = date.today().isoformat()
    
    today_schedules = [s for s in schedules_db if s["start_date"] == today]
    pending_tasks = [t for t in tasks_db if not t["completed"]]
    
    return {
        "date": today,
        "schedules": today_schedules,
        "tasks": pending_tasks[:10]  # 상위 10개만
    }

@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "module": "schedule-manager",
        "schedules": len(schedules_db),
        "tasks": len(tasks_db)
    }