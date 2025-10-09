"""
Schedule Manager 데이터 모델
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Optional
from enum import Enum

class TaskStatus(str, Enum):
    """작업 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    """작업 유형"""
    ONCE = "once"           # 일회성
    RECURRING = "recurring" # 반복
    CRON = "cron"          # 크론 스타일

class ScheduledTask(BaseModel):
    """스케줄된 작업 모델"""
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
    """작업 실행 기록 모델"""
    task_id: str
    execution_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: TaskStatus
    result: Optional[str] = None
    error_message: Optional[str] = None