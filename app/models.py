from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(1000), nullable=True)
    done_flag = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('users.id'))

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "done_flag": self.done_flag,
            "user_id": self.user_id
        }

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = ""

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    created_at: Optional[datetime] = None  # Сделать optional
    updated_at: Optional[datetime] = None  # Сделать optional

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    done_flag: Optional[bool] = False
    user_id: Optional[int] = None

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    done_flag: Optional[bool] = None
    user_id: Optional[int] = None

class TaskResponse(BaseModel):
    task_id: int
    name: str
    description: Optional[str]
    done_flag: bool
    user_id: Optional[int]

    class Config:
        from_attributes = True