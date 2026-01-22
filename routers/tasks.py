from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from database import get_async_session
from models.task import Task
from models.user import User, UserRole
from schemas import TaskCreate, TaskUpdate, TaskResponse
from utils import calculate_urgency, determine_quadrant, calculate_days_until_deadline
from dependencies import get_current_user, get_current_admin

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"]
)

@router.get("", response_model=List[TaskResponse])
async def get_all_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.ADMIN:
        # Админ видит все задачи
        result = await db.execute(select(Task))
    else:
        # Обычный пользователь видит только свои задачи
        result = await db.execute(
            select(Task).where(Task.user_id == current_user.id)
        )
    
    tasks = result.scalars().all()
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Проверка прав доступа
    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )
    
    # Расчет дней до дедлайна и статуса
    days_deadline = calculate_days_until_deadline(task.deadline_at)
    task_dict = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "is_important": task.is_important,
        "is_urgent": task.is_urgent,
        "quadrant": task.quadrant,
        "completed": task.completed,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
        "deadline_at": task.deadline_at,
        "user_id": task.user_id,
        "days_until_deadline": days_deadline,
        "status_message": "Задача просрочена" if (task.deadline_at and days_deadline and days_deadline < 0) else "Все идет по плану!"
    }
    
    return TaskResponse(**task_dict)


@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    keyword = f"%{q.lower()}%"
    
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(
            select(Task).where(
                or_(
                    Task.title.ilike(keyword),
                    Task.description.ilike(keyword)
                )
            )
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                or_(
                    Task.title.ilike(keyword),
                    Task.description.ilike(keyword)
                )
            )
        )
    
    tasks = result.scalars().all()
    if not tasks:
        raise HTTPException(status_code=404, detail="По данному запросу ничего не найдено")
    
    return tasks


@router.get("/quadrant/{quadrant}", response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(status_code=400, detail="Неверный квадрат. Используйте: Q1, Q2, Q3, Q4")
    
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(
            select(Task).where(Task.quadrant == quadrant)
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                Task.quadrant == quadrant
            )
        )
    
    tasks = result.scalars().all()
    return tasks

@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(
    status: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    if status not in ["completed", "pending"]:
        raise HTTPException(status_code=400, detail="Недопустимый статус. Используйте: completed или pending")
    
    is_completed = (status == "completed")
    
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(
            select(Task).where(Task.completed == is_completed)
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                Task.completed == is_completed
            )
        )
    
    tasks = result.scalars().all()
    return tasks

@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    # Расчет срочности и квадранта
    is_urgent = calculate_urgency(task_data.deadline_at)
    quadrant = determine_quadrant(task_data.is_important, is_urgent)
    
    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        is_important=task_data.is_important,
        is_urgent=is_urgent,
        quadrant=quadrant,
        deadline_at=task_data.deadline_at,
        completed=False,
        user_id=current_user.id  # Привязываем к текущему пользователю
    )
    
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Проверка прав доступа
    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )
    
    # Обновляем только переданные поля
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    # Пересчитываем квадрат, если изменились важность или дедлайн
    if "is_important" in update_data or "deadline_at" in update_data:
        task.is_urgent = calculate_urgency(task.deadline_at)
        task.quadrant = determine_quadrant(task.is_important, task.is_urgent)
    
    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Проверка прав доступа
    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )
    
    deleted_task_info = {
        "id": task.id,
        "title": task.title
    }
    
    await db.delete(task)
    await db.commit()
    
    return {
        "message": "Задача успешно удалена",
        "id": deleted_task_info["id"],
        "title": deleted_task_info["title"]
    }


@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Проверка прав доступа
    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )
    
    task.completed = True
    task.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/today", response_model=List[TaskResponse])
async def get_tasks_due_today(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(
            select(Task).where(
                Task.deadline_at.between(today_start, today_end),
                Task.completed == False
            ).order_by(Task.deadline_at)
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                Task.deadline_at.between(today_start, today_end),
                Task.completed == False
            ).order_by(Task.deadline_at)
        )
    
    tasks = result.scalars().all()
    
    # Добавляем расчет дней до дедлайна
    response_tasks = []
    for task in tasks:
        days_deadline = calculate_days_until_deadline(task.deadline_at)
        task_dict = task.to_dict()
        task_dict['days_until_deadline'] = days_deadline
        task_dict['status_message'] = "Срок истекает сегодня!"
        response_tasks.append(TaskResponse(**task_dict))
    
    return response_tasks