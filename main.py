# Главный файл приложения
from fastapi import FastAPI
from routers import tasks, stats

app = FastAPI(
    title="ToDo лист API",
    description="API для управления задачами с использованием матрицы Эйзенхауэра",
    version="1.0.0",
    contact = {
        "name": "Ваше Имя"
    }
)

app.include_router(tasks.router, prefix="/api/v1")

app.include_router(stats.router, prefix="/api/v1")

@app.get("/")
async def welcome() -> dict:
    return {"message": "Привет, студент!",
            "api_title": app.title,
            "api_description": app.description,
            "api_version": app.version,
            "api_autor": app.contact["name"]}

