from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_
from datetime import datetime, timezone
from database import get_async_session
from models.task import Task
from models.user import User, UserRole
from schemas import TimingStatsResponse
from dependencies import get_current_user, get_current_admin

router = APIRouter(
    prefix="/stats",
    tags=["statistics"]
)

@router.get("/", response_model=dict)
async def get_tasks_stats(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    # 1. Определяем условия фильтрации в зависимости от роли
    if current_user.role == UserRole.ADMIN:
        # Админ - видит все задачи
        base_condition = True
        count_query = select(func.count(Task.id))
        quadrant_query = select(Task.quadrant, func.count(Task.id).label('count'))
        status_query = select(
            func.count(case((Task.completed == True, 1))).label('completed'),
            func.count(case((Task.completed == False, 1))).label('pending')
        )
    else:
        # Обычный пользователь - видит только свои задачи
        base_condition = Task.user_id == current_user.id
        count_query = select(func.count(Task.id)).where(Task.user_id == current_user.id)
        quadrant_query = select(Task.quadrant, func.count(Task.id).label('count')) \
            .where(Task.user_id == current_user.id)
        status_query = select(
            func.count(case((Task.completed == True, 1))).label('completed'),
            func.count(case((Task.completed == False, 1))).label('pending')
        ).where(Task.user_id == current_user.id)
    
    # 2. Выполняем запросы
    total_result = await db.execute(count_query)
    total_tasks = total_result.scalar() or 0
    
    quadrant_result = await db.execute(quadrant_query.group_by(Task.quadrant))
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    for row in quadrant_result:
        if row.quadrant in by_quadrant:
            by_quadrant[row.quadrant] = row.count
    
    status_result = await db.execute(status_query)
    status_row = status_result.one()
    by_status = {
        "completed": status_row.completed or 0,
        "pending": status_row.pending or 0
    }
    
    # 3. Возвращаем результат с информацией о пользователе
    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": by_status,
        "user_role": current_user.role.value,
        "user_id": current_user.id
    }

@router.get("/timing", response_model=TimingStatsResponse)
async def get_deadline_stats(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    now_utc = datetime.now(timezone.utc)
    
    # 1. Определяем базовое условие для фильтрации
    if current_user.role == UserRole.ADMIN:
        base_condition = True
    else:
        base_condition = Task.user_id == current_user.id
    
    # 2. SQL запрос для подсчета статистики по срокам
    statement = select(
        func.sum(
            case((
                and_(
                    Task.completed == True,
                    Task.completed_at <= Task.deadline_at
                ), 1
            ), else_=0)
        ).label("completed_on_time"),
        func.sum(
            case((
                and_(
                    Task.completed == True,
                    Task.completed_at > Task.deadline_at
                ), 1
            ), else_=0)
        ).label("completed_late"),
        func.sum(
            case((
                and_(
                    Task.completed == False,
                    Task.deadline_at.isnot(None),
                    Task.deadline_at > now_utc
                ), 1
            ), else_=0)
        ).label("on_plan_pending"),
        func.sum(
            case((
                and_(
                    Task.completed == False,
                    Task.deadline_at.isnot(None),
                    Task.deadline_at <= now_utc
                ), 1
            ), else_=0)
        ).label("overdue_pending")
    ).where(base_condition)
    
    # 3. Выполняем запрос
    result = await db.execute(statement)
    stats_row = result.one()
    
    # 4. Возвращаем результат
    return TimingStatsResponse(
        completed_on_time=stats_row.completed_on_time or 0,
        completed_late=stats_row.completed_late or 0,
        on_plan_pending=stats_row.on_plan_pending or 0,
        overdue_pending=stats_row.overdue_pending or 0
    )

@router.get("/users")
async def get_users_stats(
    current_user: User = Depends(get_current_admin),  # ТОЛЬКО ДЛЯ АДМИНОВ
    db: AsyncSession = Depends(get_async_session)
):
    # 1. Запрос для получения всех пользователей с количеством их задач
    result = await db.execute(
        select(
            User.id,
            User.nickname,
            User.email,
            User.role,
            func.count(Task.id).label('task_count')
        ).outerjoin(Task, User.id == Task.user_id)
         .group_by(User.id)
         .order_by(User.id)
    )
    
    # 2. Формируем ответ
    users_stats = []
    for row in result:
        users_stats.append({
            "id": row.id,
            "nickname": row.nickname,
            "email": row.email,
            "role": row.role.value,
            "task_count": row.task_count
        })
    
    # 3. Возвращаем результат
    return {
        "total_users": len(users_stats),
        "users": users_stats
    }