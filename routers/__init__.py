from .auth import router as auth_router
from .tasks import router as tasks_router
from .stats import router as stats_router

# Список всех роутеров для удобного импорта
__all__ = [
    "auth_router",
    "tasks_router", 
    "stats_router",
]