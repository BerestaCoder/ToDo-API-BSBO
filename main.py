# Главный файл приложения
from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Any
from datetime import datetime

app = FastAPI(
    title="ToDo лист API",
    description="API для управления задачами с использованием матрицы Эйзенхауэра",
    version="1.0.0",
    contact={
        "name": "Акифьев М.О.",
    }
)

# Временное хранилище (позже будет заменено на PostgreSQL)
tasks_db: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Сдать проект по FastAPI",
        "description": "Завершить разработку API и написать документацию",
        "is_important": True,
        "is_urgent": True,
        "quadrant": "Q1",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 2,
        "title": "Изучить SQLAlchemy",
        "description": "Прочитать документацию и попробовать примеры",
        "is_important": True,
        "is_urgent": False,
        "quadrant": "Q2",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 3,
        "title": "Сходить на лекцию",
        "description": None,
        "is_important": False,
        "is_urgent": True,
        "quadrant": "Q3",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 4,
        "title": "Посмотреть сериал",
        "description": "Новый сезон любимого сериала",
        "is_important": False,
        "is_urgent": False,
        "quadrant": "Q4",
        "completed": True,
        "created_at": datetime.now()
    },
]

@app.get("/")
async def welcome() -> dict:
    return { 
        "title": app.title,
        "description": app.description, 
        "version": app.version,
        "contact": app.contact
        }

@app.get("/tasks")
async def get_all_tasks() -> dict:
    return { 
        "count": len(tasks_db),
        "dtasks": tasks_db
        }

# Получение статистики по задачам
@app.get("/tasks/stats")
async def get_tasks_stats() -> dict:
    total_tasks = len(tasks_db)
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    completed = 0
    
    for task in tasks_db:
        quad = task.get("quadrant")
        by_quadrant[quad] += 1
        if task.get("completed"):
            completed += 1
            
    pending = total_tasks - completed
    
    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": {
            "completed": completed,
            "pending": pending
        }
    }

# Получение заданий по ключевому слову в названии и описании
@app.get("/tasks/search")
async def serch_tasks(q: str = Query(min_length=2)) -> dict:
    filtered_tasks = []
    for task in tasks_db:
        title = task.get("title")
        description = task.get("description")
        if title is not None and q in title:
            filtered_tasks.append(task)
        elif description is not None and q in description:
            filtered_tasks.append(task)
    if filtered_tasks:
        return {
            "query": q,
            "count": len(filtered_tasks),
            "tasks": filtered_tasks
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="Задания не найдены."
        )

# Получение заданий по статусу
@app.get("/tasks/status/{status}")
async def get_tasks_by_status(status: str) -> dict:
    if status not in ["completed", "pending"]:
        raise HTTPException(status_code=404, detail="Статус не найден.")
    
    completed = (status == "completed")

    filtered_tasks = []
    for task in tasks_db:
        if task.get("completed") == completed:
            filtered_tasks.append(task)
    
    return {
        "status": status,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }

# Получение задачи по квадранту
@app.get("/tasks/quadrant/{quadrant}")
async def get_tasks_by_quadrant(quadrant: str) -> dict:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4"
        )
    filtered_tasks = [
        task
        for task in tasks_db
        if task["quadrant"] == quadrant
    ]
    return {
        "quadrant": quadrant,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }

# Получение задачи по ID
@app.get("/tasks/{task_id}")
async def get_task(task_id: int) -> dict:
    for task in tasks_db:
        if task["id"] == task_id:
            return task
    raise HTTPException(
        status_code=404,
        detail="Задача не найдена."
    )