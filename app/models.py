from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import re


# Валидаторы
def validate_username(username: str) -> str:
    """Валидация username"""
    if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
        raise ValueError('Username должен содержать только буквы, цифры и подчеркивания, от 3 до 50 символов')
    return username


def validate_email(email: str) -> str:
    """Валидация email"""
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError('Некорректный формат email')
    return email


def validate_name(name: str) -> str:
    """Валидация названия задачи"""
    if not name.strip():
        raise ValueError('Название задачи не может быть пустым')
    return name.strip()


# Базовые модели пользователей
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username пользователя")
    email: str = Field(..., max_length=100, description="Email пользователя")
    full_name: Optional[str] = Field(None, max_length=100, description="Полное имя")

    @validator('username')
    def validate_username(cls, v):
        return validate_username(v)

    @validator('email')
    def validate_email(cls, v):
        return validate_email(v)


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)

    @validator('username')
    def validate_username(cls, v):
        if v is not None:
            return validate_username(v)
        return v

    @validator('email')
    def validate_email(cls, v):
        if v is not None:
            return validate_email(v)
        return v


class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# Базовые модели задач
class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Название задачи")
    description: Optional[str] = Field(None, max_length=1000, description="Описание задачи")
    done_flag: bool = Field(False, description="Флаг выполнения")
    user_id: Optional[int] = Field(None, description="ID пользователя")

    @validator('name')
    def validate_name(cls, v):
        return validate_name(v)


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    done_flag: Optional[bool] = None
    user_id: Optional[int] = None

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            return validate_name(v)
        return v


class TaskResponse(TaskBase):
    task_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# Модели для ответов с пользователями и их задачами
class UserWithTasksResponse(UserResponse):
    tasks: List[TaskResponse] = []


# Модели для ошибок
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


class ValidationErrorItem(BaseModel):
    loc: List[str]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    detail: str = "Ошибка валидации"
    errors: List[ValidationErrorItem]


# Коды ошибок
class ErrorCodes:
    # Пользователи
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USERNAME_EXISTS = "USERNAME_EXISTS"
    EMAIL_EXISTS = "EMAIL_EXISTS"
    USER_HAS_TASKS = "USER_HAS_TASKS"

    # Задачи
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    INVALID_USER_ID = "INVALID_USER_ID"

    # Общие
    INVALID_DATA = "INVALID_DATA"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTEGRITY_ERROR = "INTEGRITY_ERROR"


# Вспомогательные функции для работы с данными из БД
def user_from_db(row) -> UserResponse:
    """
    Преобразует запись из БД в UserResponse
    """
    return UserResponse(
        id=row['id'],
        username=row['username'],
        email=row['email'],
        full_name=row['full_name'],
        created_at=row.get('created_at'),
        updated_at=row.get('updated_at')
    )


def task_from_db(row) -> TaskResponse:
    """
    Преобразует запись из БД в TaskResponse
    """
    return TaskResponse(
        task_id=row['task_id'],
        name=row['name'],
        description=row['description'],
        done_flag=row['done_flag'],
        user_id=row['user_id'],
        created_at=row.get('created_at'),
        updated_at=row.get('updated_at')
    )


def user_with_tasks_from_db(user_row, task_rows) -> UserWithTasksResponse:
    """
    Преобразует пользователя и его задачи в UserWithTasksResponse
    """
    user_data = user_from_db(user_row)
    tasks = [task_from_db(task_row) for task_row in task_rows]

    return UserWithTasksResponse(
        **user_data.dict(),
        tasks=tasks
    )


# SQL запросы для создания таблиц
CREATE_TABLES_SQL = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            full_name VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "tasks": """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            done_flag BOOLEAN DEFAULT FALSE,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """
}

# SQL запросы для создания индексов
CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
    "CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_tasks_done_flag ON tasks(done_flag);",
    "CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);"
]

# SQL запросы для обновления updated_at
UPDATE_TIMESTAMP_SQL = {
    "users": """
        CREATE OR REPLACE FUNCTION update_users_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
        CREATE TRIGGER trigger_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_users_updated_at();
    """,
    "tasks": """
        CREATE OR REPLACE FUNCTION update_tasks_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trigger_tasks_updated_at ON tasks;
        CREATE TRIGGER trigger_tasks_updated_at
        BEFORE UPDATE ON tasks
        FOR EACH ROW
        EXECUTE FUNCTION update_tasks_updated_at();
    """
}

# Общие SQL запросы
COMMON_QUERIES = {
    "check_user_exists": "SELECT 1 FROM users WHERE id = $1",
    "check_username_exists": "SELECT 1 FROM users WHERE username = $1 AND id != $2",
    "check_email_exists": "SELECT 1 FROM users WHERE email = $1 AND id != $2",
    "check_user_has_tasks": "SELECT 1 FROM tasks WHERE user_id = $1 LIMIT 1"
}