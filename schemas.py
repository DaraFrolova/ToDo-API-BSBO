from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_important: bool
    is_urgent: bool

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_important: Optional[bool] = None
    is_urgent: Optional[bool] = None
    completed: Optional[bool] = None

class TaskResponse(TaskBase):
    id: int
    quadrant: str
    completed: bool
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
