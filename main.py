from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import init_db
from routers import tasks, stats, auth
from scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код ДО yield выполняется при ЗАПУСКЕ
    print("🚀 Запуск приложения...")
    print("🔄 Инициализация базы данных...")
    await init_db()

    # Запускаем планировщик задач
    print("⏰ Запуск планировщика задач...")
    scheduler = start_scheduler()

    print("✅ Приложение готово к работе!")
    yield  # Здесь приложение работает

    # Код ПОСЛЕ yield выполняется при ОСТАНОВКЕ
    print("🛑 Остановка приложения...")
    scheduler.shutdown(wait=False)
    print("👋 Планировщик остановлен.")

app = FastAPI(
    title="ToDo лист API",
    description="API для управления задачами с использованием матрицы Эйзенхауэра",
    version="3.0.0",
    lifespan=lifespan
)

app.include_router(auth.router, prefix="/api/v3")
app.include_router(tasks.router, prefix="/api/v3")
app.include_router(stats.router, prefix="/api/v3")

@app.get("/")
async def read_root():
    return {
        "message": "Task Manager API - Управление задачами по матрице Эйзенхауэра",
        "version": "3.0.0",
        "database": "PostgreSQL",
        "docs": "/docs",
        "redoc": "/redoc",
        "scheduler": "APScheduler (ежедневно в 09:00)"
    }