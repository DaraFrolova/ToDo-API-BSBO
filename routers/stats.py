from fastapi import APIRouter
from typing import Dict
from database import tasks_db  # Импортируем общее хранилище

router = APIRouter(
    prefix="/stats",
    tags=["stats"]
)

@router.get("/")
async def get_tasks_stats() -> Dict:
 # Подсчет задач по квадрантам
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    completed_count = 0
    pending_count = 0
    
    for task in tasks_db:
        quadrant = task["quadrant"]
        if quadrant in by_quadrant:
            by_quadrant[quadrant] += 1
        
        # Подсчет по статусу
        if task["completed"]:
            completed_count += 1
        else:
            pending_count += 1
    
    return {
        "total_tasks": len(tasks_db),
        "by_quadrant": by_quadrant,
        "by_status": {
            "completed": completed_count,
            "pending": pending_count
        }
    }