from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TimingStatsResponse(BaseModel):
    completed_on_time: int = Field(
        default=0,
        description="Количество задач, завершенных в срок"
    )
    completed_late: int = Field(
        default=0,
        description="Количество задач, завершенных с нарушением сроков"
    )
    on_plan_pending: int = Field(
        default=0,
        description="Количество задач в работе, выполняемых в соответствии с планом"
    )
    overdue_pending: int = Field(
        default=0,
        description="Количество просроченных незавершенных задач"
    )

# Схема для создания задачи (POST)
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_important: bool
    deadline_at: Optional[datetime] = None  

# Схема для обновления задачи (PUT/PATCH)
class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_important: Optional[bool] = None
    deadline_at: Optional[datetime] = None  
    completed: Optional[bool] = None

# Схема для ответа (GET)
class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    is_important: bool
    is_urgent: bool
    quadrant: str
    completed: bool
    created_at: datetime
    completed_at: Optional[datetime]
    deadline_at: Optional[datetime]  
    days_until_deadline: Optional[int] = None 
    status_message: Optional[str] = None
    user_id: Optional[int] = None

    class Config:
        from_attributes = True