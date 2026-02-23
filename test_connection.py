import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    try:
        conn = await asyncpg.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        print("✅ Подключение к PostgreSQL успешно!")
        await conn.close()
    except Exception as e:
        print(f"❌ Ошибка: {e}")

asyncio.run(test())
