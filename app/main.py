from fastapi import FastAPI, Depends, HTTPException, status
from typing import List
import asyncpg
from asyncpg.exceptions import UniqueViolationError, ForeignKeyViolationError

from .models import (
    UserCreate, UserUpdate, UserResponse,
    TaskCreate, TaskUpdate, TaskResponse
)
from .database import get_db, create_tables

app = FastAPI(title="User Task API", version="1.0.0")


@app.on_event("startup")
async def startup():
    await create_tables()


# Простой обработчик ошибок без декоратора
async def handle_db_errors(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except UniqueViolationError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Конфликт данных: запись с такими уникальными полями уже существует"
        )
    except ForeignKeyViolationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ошибка внешнего ключа: связанный объект не существует"
        )
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


# Эндпоинты для пользователей
@app.get("/users", response_model=List[UserResponse])
async def get_users(db=Depends(get_db)):
    try:
        rows = await db.fetch("SELECT * FROM users ORDER BY id")
        users = []
        for row in rows:
            users.append(UserResponse(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                full_name=row['full_name'],
                created_at=row.get('created_at'),
                updated_at=row.get('updated_at')
            ))
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db=Depends(get_db)):
    try:
        row = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        return UserResponse(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            full_name=row['full_name'],
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db=Depends(get_db)):
    try:
        row = await db.fetchrow(
            """INSERT INTO users (username, email, full_name) 
            VALUES ($1, $2, $3) RETURNING *""",
            user_data.username, user_data.email, user_data.full_name
        )
        return UserResponse(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            full_name=row['full_name'],
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    except UniqueViolationError as e:
        if "username" in str(e):
            detail_msg = "Пользователь с таким username уже существует"
        elif "email" in str(e):
            detail_msg = "Пользователь с таким email уже существует"
        else:
            detail_msg = "Пользователь с такими данными уже существует"

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail_msg
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_data: UserUpdate, db=Depends(get_db)):
    try:
        # Проверяем существование пользователя
        existing = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        # Проверяем обновляемые поля
        update_data = user_data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нет данных для обновления"
            )

        # Проверяем уникальность username если он обновляется
        if user_data.username and user_data.username != existing["username"]:
            username_exists = await db.fetchrow(
                "SELECT 1 FROM users WHERE username = $1 AND id != $2",
                user_data.username, user_id
            )
            if username_exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким username уже существует"
                )

        # Проверяем уникальность email если он обновляется
        if user_data.email and user_data.email != existing["email"]:
            email_exists = await db.fetchrow(
                "SELECT 1 FROM users WHERE email = $1 AND id != $2",
                user_data.email, user_id
            )
            if email_exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким email уже существует"
                )

        # Выполняем обновление
        row = await db.fetchrow(
            """UPDATE users 
            SET username = COALESCE($1, username), 
                email = COALESCE($2, email), 
                full_name = COALESCE($3, full_name)
            WHERE id = $4 
            RETURNING *""",
            user_data.username, user_data.email, user_data.full_name, user_id
        )

        return UserResponse(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            full_name=row['full_name'],
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db=Depends(get_db)):
    try:
        # Проверяем существование пользователя
        existing = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        # Проверяем есть ли у пользователя задачи
        has_tasks = await db.fetchrow("SELECT 1 FROM tasks WHERE user_id = $1 LIMIT 1", user_id)
        if has_tasks:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Невозможно удалить пользователя с задачами"
            )

        # Удаляем пользователя
        await db.execute("DELETE FROM users WHERE id = $1", user_id)
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Эндпоинты для задач
@app.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(db=Depends(get_db)):
    try:
        rows = await db.fetch("SELECT * FROM tasks ORDER BY task_id")
        tasks = []
        for row in rows:
            tasks.append(TaskResponse(
                task_id=row['task_id'],
                name=row['name'],
                description=row['description'],
                done_flag=row['done_flag'],
                user_id=row['user_id'],
                created_at=row.get('created_at'),
                updated_at=row.get('updated_at')
            ))
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db=Depends(get_db)):
    try:
        row = await db.fetchrow("SELECT * FROM tasks WHERE task_id = $1", task_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Задача не найдена"
            )
        return TaskResponse(
            task_id=row['task_id'],
            name=row['name'],
            description=row['description'],
            done_flag=row['done_flag'],
            user_id=row['user_id'],
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate, db=Depends(get_db)):
    try:
        # Проверка существования пользователя если указан user_id
        if task_data.user_id:
            user_exists = await db.fetchrow("SELECT 1 FROM users WHERE id = $1", task_data.user_id)
            if not user_exists:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Указанный пользователь не существует"
                )

        row = await db.fetchrow(
            """INSERT INTO tasks (name, description, done_flag, user_id) 
            VALUES ($1, $2, $3, $4) RETURNING *""",
            task_data.name, task_data.description, task_data.done_flag, task_data.user_id
        )
        return TaskResponse(
            task_id=row['task_id'],
            name=row['name'],
            description=row['description'],
            done_flag=row['done_flag'],
            user_id=row['user_id'],
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_data: TaskUpdate, db=Depends(get_db)):
    try:
        # Проверяем существование задачи
        existing = await db.fetchrow("SELECT * FROM tasks WHERE task_id = $1", task_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Задача не найдена"
            )

        # Проверяем обновляемые поля
        update_data = task_data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нет данных для обновления"
            )

        # Проверка пользователя если обновляется user_id
        if task_data.user_id is not None and task_data.user_id != existing["user_id"]:
            if task_data.user_id:  # Если не None и не 0
                user_exists = await db.fetchrow("SELECT 1 FROM users WHERE id = $1", task_data.user_id)
                if not user_exists:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Указанный пользователь не существует"
                    )

        # Выполняем обновление
        row = await db.fetchrow(
            """UPDATE tasks 
            SET name = COALESCE($1, name),
                description = COALESCE($2, description),
                done_flag = COALESCE($3, done_flag),
                user_id = $4
            WHERE task_id = $5
            RETURNING *""",
            task_data.name, task_data.description, task_data.done_flag, task_data.user_id, task_id
        )

        return TaskResponse(
            task_id=row['task_id'],
            name=row['name'],
            description=row['description'],
            done_flag=row['done_flag'],
            user_id=row['user_id'],
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db=Depends(get_db)):
    try:
        # Проверяем существование задачи
        existing = await db.fetchrow("SELECT * FROM tasks WHERE task_id = $1", task_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Задача не найдена"
            )

        await db.execute("DELETE FROM tasks WHERE task_id = $1", task_id)
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/tasks", response_model=List[TaskResponse])
async def get_user_tasks(user_id: int, db=Depends(get_db)):
    try:
        # Проверяем существование пользователя
        user_exists = await db.fetchrow("SELECT 1 FROM users WHERE id = $1", user_id)
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        rows = await db.fetch(
            "SELECT * FROM tasks WHERE user_id = $1 ORDER BY task_id",
            user_id
        )
        tasks = []
        for row in rows:
            tasks.append(TaskResponse(
                task_id=row['task_id'],
                name=row['name'],
                description=row['description'],
                done_flag=row['done_flag'],
                user_id=row['user_id'],
                created_at=row.get('created_at'),
                updated_at=row.get('updated_at')
            ))
        return tasks
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "User Task API"}

@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)