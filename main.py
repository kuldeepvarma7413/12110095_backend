from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Task model
class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    is_completed = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

# Pydantic schemas
class TaskCreate(BaseModel):
    title: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    is_completed: Optional[bool] = None

class Task(BaseModel):
    id: int
    title: str
    is_completed: bool

    class Config:
        orm_mode = True

class TaskList(BaseModel):
    tasks: List[Task]

class TaskId(BaseModel):
    id: int

class BulkTaskCreate(BaseModel):
    tasks: List[TaskCreate]

class BulkTaskDelete(BaseModel):
    tasks: List[TaskId]

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

# Create a new task
@app.post("/v1/tasks", status_code=201, response_model=TaskId)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = TaskModel(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return {"id": db_task.id}

# List all tasks
@app.get("/v1/tasks", response_model=TaskList)
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(TaskModel).all()
    return {"tasks": tasks}

# Get a specific task
@app.get("/v1/tasks/{task_id}", response_model=Task)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="There is no task at that id")
    return task

# Delete a specific task
@app.delete("/v1/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
    return

# Edit a specific task
@app.put("/v1/tasks/{task_id}", status_code=204)
def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="There is no task at that id")
    update_data = task.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    db.commit()
    return

# Bulk add tasks (Extra Credit)
@app.post("/v1/tasks", status_code=201, response_model=TaskList)
def bulk_create_tasks(tasks: BulkTaskCreate, db: Session = Depends(get_db)):
    db_tasks = [TaskModel(**task.dict()) for task in tasks.tasks]
    db.add_all(db_tasks)
    db.commit()
    for task in db_tasks:
        db.refresh(task)
    return {"tasks": [{"id": task.id} for task in db_tasks]}

# Bulk delete tasks (Extra Credit)
@app.delete("/v1/tasks", status_code=204)
def bulk_delete_tasks(tasks: BulkTaskDelete, db: Session = Depends(get_db)):
    task_ids = [task.id for task in tasks.tasks]
    db.query(TaskModel).filter(TaskModel.id.in_(task_ids)).delete(synchronize_session=False)
    db.commit()
    return