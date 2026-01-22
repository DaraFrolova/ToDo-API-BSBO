from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime

from database import get_async_session
from models import Task
from schemas import TaskCreate, TaskUpdate, TaskResponse
from utils import calculate_urgency, determine_quadrant, calculate_days_until_deadline

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"]
)

@router.get("", response_model=List[TaskResponse])
async def get_all_tasks(
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Task))
    return result.scalars().all()

@router.get("/quadrant/{quadrant}", response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session)
):
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(400, "Неверный квадрант")

    result = await db.execute(
        select(Task).where(Task.quadrant == quadrant)
    )
    return result.scalars().all()

@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session)
):
    keyword = f"%{q.lower()}%"
    result = await db.execute(
        select(Task).where(
            Task.title.ilike(keyword) |
            Task.description.ilike(keyword)
        )
    )
    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(404, "Ничего не найдено")

    return tasks

@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(
    status: str,
    db: AsyncSession = Depends(get_async_session)
):
    if status not in ["completed", "pending"]:
        raise HTTPException(404, "Недопустимый статус")

    is_completed = status == "completed"
    result = await db.execute(
        select(Task).where(Task.completed == is_completed)
    )
    return result.scalars().all()

@router.get("/today", response_model=list[TaskResponse])
async def get_tasks_due_today(
    db: AsyncSession = Depends(get_async_session)
):

    from datetime import datetime, timezone, timedelta
    from sqlalchemy import and_
    
    # Получаем сегодняшнюю дату в UTC
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)
    
    # Ищем незавершённые задачи с дедлайном сегодня
    result = await db.execute(
        select(Task).where(
            and_(
                Task.completed == False,
                Task.deadline_at.isnot(None),
                Task.deadline_at >= today_start,
                Task.deadline_at < today_end
            )
        ).order_by(Task.deadline_at)
    )
    
    tasks = result.scalars().all()
    
    # Добавляем вычисляемые поля к каждой задаче
    tasks_with_fields = []
    for task in tasks:
        days = calculate_days_until_deadline(task.deadline_at)
        
        task_dict = task.__dict__.copy()
        task_dict['days_until_deadline'] = days
        
        if days is not None and days < 0:
            task_dict['status_message'] = "Задача просрочена"
        else:
            task_dict['status_message'] = "Все идет по плану!"
        
        tasks_with_fields.append(TaskResponse(**task_dict))
    
    return tasks_with_fields

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session)
):

    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    days_deadline = calculate_days_until_deadline(task.deadline_at)
    task_dict = task.__dict__.copy()
    
    task_dict['days_until_deadline'] = days_deadline

    if task.deadline_at is not None and days_deadline is not None and days_deadline < 0:
        task_dict['status_message'] = "Задача просрочена"  
    else:
        task_dict['status_message'] = "Все идет по плану!"
    return TaskResponse(**task_dict)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    # Пересчитываем срочность и квадрант, если изменилась важность или дедлайн
    if "is_important" in update_data or "deadline_at" in update_data:
        task.is_urgent = calculate_urgency(task.deadline_at)
        task.quadrant = determine_quadrant(task.is_important, task.is_urgent)

    await db.commit()
    await db.refresh(task)

    response = TaskResponse.model_validate(task)
    response.days_until_deadline = calculate_days_until_deadline(task.deadline_at)

    return response

@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(404, "Задача не найдена")

    await db.delete(task)
    await db.commit()

    return {
        "message": "Задача успешно удалена",
        "id": task.id,
        "title": task.title
    }

@router.post("/", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_session)
):
    # Определяем срочность на основе дедлайна
    is_urgent = calculate_urgency(task.deadline_at)
    quadrant = determine_quadrant(task.is_important, is_urgent)

    new_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        is_urgent=is_urgent,
        quadrant=quadrant,
        completed=False,
        deadline_at=task.deadline_at
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    # Добавляем вычисляемое поле для ответа
    response = TaskResponse.model_validate(new_task)
    response.days_until_deadline = calculate_days_until_deadline(new_task.deadline_at)

    return response

@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(404, "Задача не найдена")

    task.completed = True
    task.completed_at = datetime.now()

    await db.commit()
    await db.refresh(task)
    return task

