from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses = {404: {"decripton": "Task not found"}},
    )

# Временное хранилище (позже будет заменено на PostgreSQL)
tasks_db: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Сдать проект по FastAPI",
        "description": "Завершить разработку API и написать документацию",
        "is_important": True,
        "is_urgent": True,
        "quadrant": "Q1",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 2,
        "title": "Изучить SQLAlchemy",
        "description": "Прочитать документацию и попробовать примеры",
        "is_important": True,
        "is_urgent": False,
        "quadrant": "Q2",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 3,
        "title": "Сходить на лекцию",
        "description": None,
        "is_important": False,
        "is_urgent": True,
        "quadrant": "Q3",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 4,
        "title": "Посмотреть сериал",
        "description": "Новый сезон любимого сериала",
        "is_important": False,
        "is_urgent": False,
        "quadrant": "Q4",
        "completed": True,
        "created_at": datetime.now()
    },
]

@router.get("")
async def get_all_tasks() -> dict:
    return {
        "count": len(tasks_db), # считает количество записей в хранилище
        "tasks": tasks_db # выводит всё, чта есть в хранилище
}

@router.get("/quadrant/{quadrant}")
async def get_tasks_by_quadrant(quadrant: str) -> dict:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException( #специальный класс в FastAPI для возврата HTTP ошибок.Не забудьте добавть его вызов в 1 строке
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4" #текст, который будет выведен пользователю
        )
    
    filtered_tasks = [ 
        task # ЧТО добавляем в список
        for task in tasks_db # ОТКУДА берем элементы
        if task["quadrant"] == quadrant # УСЛОВИЕ фильтрации
        ]
    return {
        "quadrant": quadrant,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
        }

@router.get("/stats")
async def get_tasks_stats() -> dict:
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



@router.get("/status/{status_param}")  # Изменили имя в пути
async def get_tasks_by_status(status_param: str) -> dict:  # Изменили имя параметра
    # Проверка валидности статуса
    if status_param not in ["completed", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,  # Теперь 404 вместо 400
            detail='Неверный статус. Используйте: "completed" (выполненные) или "pending" (невыполненные)'
        )
    
    # Определение булевого значения для фильтрации
    is_completed = (status_param == "completed")
    
    # Фильтрация задач
    filtered_tasks = [
        task
        for task in tasks_db
        if task["completed"] == is_completed
    ]
    
    if not filtered_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задачи со статусом '{status_param}' не найдены"
        )
    
    return {
        "status": status_param,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }

@router.get("/search")
async def search_tasks(q: str) -> dict:
    if len(q) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ключевое слово должно содержать минимум 2 символа"
        )
    search_term = q.lower()
    filtered_tasks = []
    for task in tasks_db:
        title_match = task["title"].lower().find(search_term) != -1 if task["title"] else False

        desc_match = False
        if task["description"]:
            desc_match = task["description"].lower().find(search_term) != -1

        if title_match or desc_match:
            filtered_tasks.append(task)
    
    if not filtered_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задачи по запросу '{q}' не найдены"
        )
    return {
        "query": q,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }

@router.get("/{task_id}")
async def get_task_by_id(task_id: int) -> dict:
    for task in tasks_db:
        if task["id"] == task_id:
            return {"task": task}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Задача с ID {task_id} не найдена"
    )