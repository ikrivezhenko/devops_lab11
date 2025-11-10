from http.client import HTTPException

from fastapi import FastAPI, Depends
from requests import Session

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
    try:
        users = db.query(models.User).all()
        return [user.to_dict() for user in users]

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
        raise HTTPException(500, "Ошибка сервера")

# Возвращает пользователя по ID
@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return user.to_dict()

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
        raise HTTPException(500, "Ошибка сервера")


@app.post("/users", status_code=201)
def post_user(user_data: dict, db: Session = Depends(get_db)):
    try:
        if not user_data.get('username') or not user_data.get('email'):
            raise HTTPException(status_code=400, detail="Некорректные данные")

        user = models.User(
            username=user_data['username'],
            email=user_data['email'],
            full_name=user_data.get('full_name', '')
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.to_dict()

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
        raise HTTPException(500, "Ошибка сервера")


# Обновление пользователя (PUT)
@app.put("/users/{user_id}")
def update_user(user_id: int, user_data: dict, db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Обновляем только переданные поля
        if 'username' in user_data:
            user.username = user_data['username']
        if 'email' in user_data:
            user.email = user_data['email']
        if 'full_name' in user_data:
            user.full_name = user_data['full_name']

        db.commit()
        return user.to_dict()

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
        raise HTTPException(500, "Ошибка сервера")


# Удаление пользователя (DELETE)
@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        db.delete(user)
        db.commit()
        return {"message": "Пользователь удален"}

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
        raise HTTPException(500, "Ошибка сервера")


# Получить все задачи
@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    try:
        tasks = db.query(models.Task).all()
        return [task.to_dict() for task in tasks]

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
        raise HTTPException(500, "Ошибка сервера")


# Получить задачу по ID
@app.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    try:
        task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        return task.to_dict()

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
        raise HTTPException(500, "Ошибка сервера")


# Создать задачу
@app.post("/tasks", status_code=201)
def create_task(task_data: dict, db: Session = Depends(get_db)):
    try:
        if not task_data.get('name'):
            raise HTTPException(status_code=400, detail="Название задачи обязательно")

        task = models.Task(
            name=task_data['name'],
            description=task_data.get('description', ''),
            done_flag=task_data.get('done_flag', False),
            user_id=task_data.get('user_id')  # Может быть None
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task.to_dict()

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
        raise HTTPException(500, "Ошибка сервера")


# Обновить задачу
@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_data: dict, db: Session = Depends(get_db)):
    try:
        task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Задача не найдена")

        if 'name' in task_data:
            task.name = task_data['name']
        if 'description' in task_data:
            task.description = task_data['description']
        if 'done_flag' in task_data:
            task.done_flag = task_data['done_flag']
        if 'user_id' in task_data:
            task.user_id = task_data['user_id']

        db.commit()
        return task.to_dict()

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
        raise HTTPException(500, "Ошибка сервера")


# Удалить задачу
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    try:
        task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Задача не найдена")

        db.delete(task)
        db.commit()
        return {"message": "Задача удалена"}

    except Exception as e:
        db.rollback()
        print(f"ERROR: {str(e)}")
        raise HTTPException(500, "Ошибка сервера")
