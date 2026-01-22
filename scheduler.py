from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from database import get_async_session  # Импортируем зависимость для сессии
from models import Task
from utils import calculate_urgency, determine_quadrant

async def update_task_urgency():
    print(f"[{datetime.now()}] 🕐 Запуск автоматического обновления срочности задач...")

    # Создаем новую сессию для этой задачи
    async for db in get_async_session():
        try:
            # Получаем все незавершённые задачи
            result = await db.execute(
                select(Task).where(Task.completed == False)
            )
            tasks = result.scalars().all()

            updated_count = 0

            for task in tasks:
                # Вычисляем новую срочность на основе дедлайна
                new_urgency = calculate_urgency(task.deadline_at)
                new_quadrant = determine_quadrant(task.is_important, new_urgency)

                # Обновляем, только если значения изменились
                if task.is_urgent != new_urgency or task.quadrant != new_quadrant:
                    task.is_urgent = new_urgency
                    task.quadrant = new_quadrant
                    updated_count += 1

            if updated_count > 0:
                await db.commit()
                print(f"✅ Обновлено задач: {updated_count} из {len(tasks)}")
            else:
                print(f"📊 Изменений не требуется. Проверено задач: {len(tasks)}")

        except Exception as e:
            print(f"❌ Ошибка при обновлении срочности: {e}")
            await db.rollback()
        finally:
            await db.close()
        break  # Выходим из цикла async for


def start_scheduler():
    scheduler = AsyncIOScheduler()

    # ✅ ОСНОВНАЯ ЗАДАЧА: запуск каждый день в 09:00 утра
    scheduler.add_job(
        update_task_urgency,
        trigger="cron",
        hour=9,
        minute=0,
        id="update_urgency_daily",
        name="Ежедневное обновление срочности задач",
        replace_existing=True
    )

    # 🧪 ДЛЯ ТЕСТИРОВАНИЯ: запуск каждые 5 минут
    # Раскомментируйте для проверки работы
    #scheduler.add_job(
    #    update_task_urgency,
    #    trigger="interval",
    #    minutes=5,
    #    id="update_urgency_test",
    #    name="Тестовое обновление срочности (каждые 5 мин)",
    #    replace_existing=True
    #)

    # Запускаем планировщик
    scheduler.start()
    print("✅ Планировщик APScheduler запущен!")
    print("📅 Задачи:")
    print("   - Ежедневно в 09:00: обновление срочности")
    print("   - Каждые 5 минут: тестовое обновление (закомментируйте после теста)")

    return scheduler