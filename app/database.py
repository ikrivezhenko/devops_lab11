import asyncpg
import os

# URL для подключения к базе данных
DATABASE_URL = "postgresql://ikrivezhenko:password@db:5432/user_db"


async def get_db():
    """
    Зависимость для получения соединения с БД
    """
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()


async def create_tables():
    """
    Создание таблиц в базе данных
    """
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Создаем таблицу пользователей
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                full_name VARCHAR(100),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создаем таблицу задач
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                done_flag BOOLEAN DEFAULT FALSE,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создаем индексы
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_done_flag ON tasks(done_flag)')

        # Создаем триггеры для обновления временных меток
        await conn.execute('''
            CREATE OR REPLACE FUNCTION update_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        ''')

        await conn.execute('''
            DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
            CREATE TRIGGER trigger_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at()
        ''')

        await conn.execute('''
            DROP TRIGGER IF EXISTS trigger_tasks_updated_at ON tasks;
            CREATE TRIGGER trigger_tasks_updated_at
            BEFORE UPDATE ON tasks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at()
        ''')

    finally:
        await conn.close()