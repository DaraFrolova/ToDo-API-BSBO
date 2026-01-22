from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, or_
from datetime import datetime, timezone
from models import Task
from database import get_async_session
from schemas import TimingStatsResponse  # Импортируем новую схему

router = APIRouter(
    prefix="/stats",
    tags=["statistics"]
)

@router.get("/", response_model=dict)
async def get_tasks_stats(db: AsyncSession = Depends(get_async_session)) -> dict:

    # 1. Общее количество задач
    total_result = await db.execute(select(func.count(Task.id)))
    total_tasks = total_result.scalar()

    # 2. Подсчет по квадрантам (одним запросом)
    quadrant_result = await db.execute(
        select(
            Task.quadrant,
            func.count(Task.id).label('count')
        ).group_by(Task.quadrant)
    )
    
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    for row in quadrant_result:
        if row.quadrant in by_quadrant:
            by_quadrant[row.quadrant] = row.count

    # 3. Подсчет по статусу выполнения (одним запросом)
    status_result = await db.execute(
        select(
            func.count(case((Task.completed == True, 1))).label('completed'),
            func.count(case((Task.completed == False, 1))).label('pending')
        )
    )
    
    status_row = status_result.one()
    by_status = {
        "completed": status_row.completed or 0,
        "pending": status_row.pending or 0
    }

    return {
        "total_tasks": total_tasks or 0,
        "by_quadrant": by_quadrant,
        "by_status": by_status
    }


@router.get("/timing", response_model=TimingStatsResponse)
async def get_deadline_stats(db: AsyncSession = Depends(get_async_session)) -> TimingStatsResponse:
    """
    Статистика по срокам выполнения задач
    """
    now_utc = datetime.now(timezone.utc)  # Получаем текущее время в UTC

    # Формируем SQL-запрос с агрегацией (COUNT + CASE)
    statement = select(
        func.sum(
            case(
                (and_(Task.completed == True, Task.completed_at <= Task.deadline_at), 1),
                else_=0
            )
        ).label("completed_on_time"),
        
        func.sum(
            case(
                (and_(Task.completed == True, Task.completed_at > Task.deadline_at), 1),
                else_=0
            )
        ).label("completed_late"),
        
        func.sum(
            case(
                (
                    and_(
                        Task.completed == False,
                        Task.deadline_at.isnot(None),
                        Task.deadline_at > now_utc
                    ),
                    1
                ),
                else_=0
            )
        ).label("on_plan_pending"),
        
        func.sum(
            case(
                (
                    and_(
                        Task.completed == False,
                        Task.deadline_at.isnot(None),
                        Task.deadline_at <= now_utc
                    ),
                    1
                ),
                else_=0
            )
        ).label("overdue_pending"),
    )

    result = await db.execute(statement)
    stats_row = result.one()

    # Возвращаем результат, используя Pydantic-схему
    return TimingStatsResponse(
        completed_on_time=stats_row.completed_on_time or 0,
        completed_late=stats_row.completed_late or 0,
        on_plan_pending=stats_row.on_plan_pending or 0,
        overdue_pending=stats_row.overdue_pending or 0
    )