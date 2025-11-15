from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import database
from app import models
from .database import get_db

app = FastAPI(title="User Task API", version="1.0.0")

# Создаем таблицы при запуске
@app.on_event("startup")
def startup():
    database.create_tables()

# Возвращает всех пользователей
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [user.to_dict() for user in users]

# Возвращает пользователя по ID
@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    return user.to_dict()

# Создание пользователя
@app.post("/users", status_code=status.HTTP_201_CREATED)
def post_user(user_data: dict, db: Session = Depends(get_db)):
    if not user_data.get('username') or not user_data.get('email'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username и email обязательны"
        )

        # Проверка на уникальность username
    existing_user = db.query(models.User).filter(models.User.username == user_data['username']).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким username уже существует"
        )

    # Проверка на уникальность email
    existing_email = db.query(models.User).filter(models.User.email == user_data['email']).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует"
        )

    user = models.User(
        username=user_data['username'],
        email=user_data['email'],
        full_name=user_data.get('full_name', '')
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.to_dict()

# Полное обновление пользователя (PUT)
@app.put("/users/{user_id}")
def update_user(user_id: int, user_data: dict, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    # Валидация обязательных полей для PUT
    if not user_data.get('username') or not user_data.get('email'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username и email обязательны"
        )

    # Проверка уникальности username (исключая текущего пользователя)
    existing_username = db.query(models.User).filter(
        models.User.username == user_data['username'],
        models.User.id != user_id
    ).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким username уже существует"
        )

    # Проверка уникальности email (исключая текущего пользователя)
    existing_email = db.query(models.User).filter(
        models.User.email == user_data['email'],
        models.User.id != user_id
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует"
        )

    # Полное обновление
    user.username = user_data['username']
    user.email = user_data['email']
    user.full_name = user_data.get('full_name', '')

    db.commit()
    return user.to_dict()

# Удаление пользователя (DELETE)
@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    db.delete(user)
    db.commit()
    return {"message": "Пользователь удален"}

# Получить все задачи
@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    tasks = db.query(models.Task).all()
    return [task.to_dict() for task in tasks]

# Получить задачу по ID
@app.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена"
        )
    return task.to_dict()

# Создать задачу
@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task_data: dict, db: Session = Depends(get_db)):
    if not task_data.get('name'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Название задачи обязательно"
        )

    # Если передан user_id, проверяем существование пользователя
    if task_data.get('user_id'):
        user = db.query(models.User).filter(models.User.id == task_data['user_id']).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Указанный пользователь не существует"
            )

    task = models.Task(
        name=task_data['name'],
        description=task_data.get('description', ''),
        done_flag=task_data.get('done_flag', False),
        user_id=task_data.get('user_id')
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task.to_dict()

# Обновить задачу
@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_data: dict, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена"
        )

    # Валидация обязательных полей для PUT
    if not task_data.get('name'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Название задачи обязательно"
        )

    # Если передан user_id, проверяем существование пользователя
    if task_data.get('user_id'):
        user = db.query(models.User).filter(models.User.id == task_data['user_id']).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Указанный пользователь не существует"
            )

    # Полное обновление
    task.name = task_data['name']
    task.description = task_data.get('description', '')
    task.done_flag = task_data.get('done_flag', False)
    task.user_id = task_data.get('user_id')

    db.commit()
    return task.to_dict()

# Удалить задачу
@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задача не найдена"
        )

    db.delete(task)
    db.commit()
    return {"message": "Задача удалена"}