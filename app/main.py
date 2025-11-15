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
    try:
        users = db.query(User).all()
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка пользователей"
        )


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
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании пользователя"
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

        # Проверяем, что переданы данные для обновления
        update_data = user_data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления"
            )

        # Проверка уникальности username
        if 'username' in update_data:
            existing_username = db.query(User).filter(
                User.username == update_data['username'],
                User.id != user_id
            ).first()
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким username уже существует"
                )
            user.username = update_data['username']

        # Проверка уникальности email
        if 'email' in update_data:
            existing_email = db.query(User).filter(
                User.email == update_data['email'],
                User.id != user_id
            ).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким email уже существует"
                )
            user.email = update_data['email']

        if 'full_name' in update_data:
            user.full_name = update_data['full_name']

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении пользователя"
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении пользователя"
        )


# Получить все задачи
@app.get("/tasks", response_model=list[TaskResponse])
def get_tasks(db: Session = Depends(get_db)):
    try:
        tasks = db.query(Task).all()
        return tasks
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка задач"
        )


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
        if task_data.user_id is not None:
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании задачи"
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

        # Проверяем, что переданы данные для обновления
        update_data = task_data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления"
            )

        # Обновляем поля
        if 'name' in update_data:
            task.name = update_data['name']

        if 'description' in update_data:
            task.description = update_data['description']

        if 'done_flag' in update_data:
            task.done_flag = update_data['done_flag']

        if 'user_id' in update_data:
            if update_data['user_id'] is not None:
                user = db.query(User).filter(User.id == update_data['user_id']).first()
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Указанный пользователь не существует"
                    )
            task.user_id = update_data['user_id']

        db.commit()
        db.refresh(task)
        return task

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении задачи"
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении задачи"
        )