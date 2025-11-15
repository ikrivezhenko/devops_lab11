from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import database
from .models import User, Task, UserCreate, UserUpdate, UserResponse, TaskCreate, TaskUpdate, TaskResponse
from .database import get_db

app = FastAPI(title="User Task API", version="1.0.0")


# Создаем таблицы при запуске
@app.on_event("startup")
def startup():
    database.create_tables()


# Возвращает всех пользователей
@app.get("/users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


# Возвращает пользователя по ID
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user


# Создание пользователя
@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def post_user(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        # Проверка на уникальность username
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким username уже существует"
            )

        # Проверка на уникальность email
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email уже существует"
            )

        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name or ""
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким username или email уже существует"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error creating user: {str(e)}")  # Для отладки
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


# Полное обновление пользователя (PUT)
@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        # Проверяем, что хотя бы одно поле для обновления передано
        if not any([user_data.username, user_data.email, user_data.full_name is not None]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не передано ни одного поля для обновления"
            )

        # Обновляем только переданные поля
        if user_data.username is not None:
            # Проверка уникальности username
            existing_username = db.query(User).filter(
                User.username == user_data.username,
                User.id != user_id
            ).first()
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким username уже существует"
                )
            user.username = user_data.username

        if user_data.email is not None:
            # Проверка уникальности email
            existing_email = db.query(User).filter(
                User.email == user_data.email,
                User.id != user_id
            ).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким email уже существует"
                )
            user.email = user_data.email

        if user_data.full_name is not None:
            user.full_name = user_data.full_name

        db.commit()
        db.refresh(user)
        return user

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким username или email уже существует"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error updating user: {str(e)}")  # Для отладки
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


# Удаление пользователя (DELETE)
@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        db.delete(user)
        db.commit()
        return None

    except Exception as e:
        db.rollback()
        print(f"Error deleting user: {str(e)}")  # Для отладки
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


# Получить все задачи
@app.get("/tasks", response_model=list[TaskResponse])
def get_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    return tasks


# Получить задачу по ID
@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена"
        )
    return task


# Создать задачу
@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    try:
        # Если передан user_id, проверяем существование пользователя
        if task_data.user_id:
            user = db.query(User).filter(User.id == task_data.user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Указанный пользователь не существует"
                )

        task = Task(
            name=task_data.name,
            description=task_data.description,
            done_flag=task_data.done_flag,
            user_id=task_data.user_id
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error creating task: {str(e)}")  # Для отладки
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


# Обновить задачу
@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_data: TaskUpdate, db: Session = Depends(get_db)):
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Задача не найдена"
            )

        # Проверяем, что хотя бы одно поле для обновления передано
        if not any([task_data.name, task_data.description is not None, task_data.done_flag is not None,
                    task_data.user_id is not None]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не передано ни одного поля для обновления"
            )

        # Обновляем только переданные поля
        if task_data.name is not None:
            task.name = task_data.name

        if task_data.description is not None:
            task.description = task_data.description

        if task_data.done_flag is not None:
            task.done_flag = task_data.done_flag

        if task_data.user_id is not None:
            # Проверяем существование пользователя
            user = db.query(User).filter(User.id == task_data.user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Указанный пользователь не существует"
                )
            task.user_id = task_data.user_id

        db.commit()
        db.refresh(task)
        return task

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error updating task: {str(e)}")  # Для отладки
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


# Удалить задачу
@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Задача не найдена"
            )

        db.delete(task)
        db.commit()
        return None

    except Exception as e:
        db.rollback()
        print(f"Error deleting task: {str(e)}")  # Для отладки
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )