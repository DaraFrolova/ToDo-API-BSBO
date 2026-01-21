import asyncio
from database import engine, init_db
from sqlalchemy import text

async def test_connection():
    print("Проверка подключения к локальному PostgreSQL...")
    
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Подключение успешно!")
            print(f" Результат тествого запроса: {result.scalar()}")
            
        print("\n Создание таблиц...")
        await init_db()
            
        print("\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("База данных готова к работе.")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА ПОДКЛЮЧЕНИЯ:")
        print(f"{e}")
        print("\nПроверьте:")
        print("1. Запущен ли PostgreSQL: sudo systemctl status postgresql")
        print("2. Правильно ли указан DATABASE_URL в .env")
        print("3. Существует ли база данных fastapi_db")
        print("4. Правильный ли пароль у пользователя fastapi_user")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())