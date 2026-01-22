from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import init_db, get_async_session
from routers import tasks, stats

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(" Запуск приложения...")
    print(" Инициализация базы данных...")
    
    await init_db()
    print(" Приложение готово к работе!")
    yield # Здесь приложение работает
    
    print(" Остановка приложения...")

app = FastAPI(
    title="ToDo лист API",
    description="API для управления задачами по матрице Эйзенхауэра",
    version="2.0.0",
    lifespan=lifespan
)

app.include_router(tasks.router, prefix="/api/v2")
app.include_router(stats.router, prefix="/api/v2")

@app.get("/")
async def root():
    return {
        "message": "Task Manager API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_async_session)
):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "database": db_status
    }
