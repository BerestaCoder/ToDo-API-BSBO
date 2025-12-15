from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timedelta, timezone
from schemas import TaskResponse, TaskCreate, TaskUpdate
from models import Task, User, UserRole

from database import get_async_session
from utils import calculate_urgency, determine_quadrant, calculate_days_until_deadline
from dependencies import get_current_user

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={400: {"description": "Task not found"}},
)

# GET ALL TASKS - Получить все задачи
@router.get("", response_model=List[TaskResponse])
async def get_all_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    if current_user.role.value == "admin":
        result = await db.execute(select(Task))
    else:
        result = await db.execute(
            select(Task).where(Task.user_id == current_user.id)
        )
    tasks = result.scalars().all()

    task_with_days = []
    for task in tasks:
        task_dict = task.__dict__.copy()
        task_dict['days_until_deadline'] = calculate_days_until_deadline(task.deadline_at)
        task_with_days.append(TaskResponse(**task_dict))

        return task_with_days

# GET TASKS BY QUADRANT - Получить задачи по квадранту
@router.get("/quadrant/{quadrant}", response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4"
        )
    
    if current_user.role.value == "admin":
        result = await db.execute(
            select(Task).where(Task.quadrant == quadrant)
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.quadrant == quadrant,
                Task.user_id == current_user.id
            )
        )   
    
    tasks = result.scalars().all()
    return tasks

@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    keyword = f"%{q.lower()}%"
    if current_user.role.value == "admin":
        result = await db.execute(
            select(Task).where(
                (Task.title.ilike(keyword)) |
                (Task.description.ilike(keyword))
            )
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                (Task.title.ilike(keyword)) |
                (Task.description.ilike(keyword))
            )
        )
    tasks = result.scalars().all()
    if not tasks:
        raise HTTPException(
            status_code=404,
            detail="По данному запросу ничего не найдено"
        )
    return tasks

# GET TASKS BY STATUS - Получить задачи по статусу
@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(
    status: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    if status not in ["completed", "pending"]:
        raise HTTPException(status_code=404, detail="Недопустимый статус. Используйте: completed или pending")
    is_completed = (status == "completed")
    if current_user.role.value == "admin":
        result = await db.execute(
            select(Task).where(
                Task.completed == is_completed
            )
        )
    else:
        result = await db.execute(
            select(Task).where(
                Task.completed == is_completed,
                Task.user_id == current_user.id
            )
        )
    tasks = result.scalars().all()
    return tasks

# Задания, заканчивающиеся сегодня
@router.get("/today", response_model=List[TaskResponse])
async def get_tasks_ending_today(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    result = await db.execute(
        select(Task).where(Task.user_id == current_user.id).filter(Task.deadline_at >= today_start, Task.deadline_at < tomorrow_start)
    )
    tasks = result.scalars().all()
    if not tasks:
        raise HTTPException(
            status_code=404,
            detail="По данному запросу ничего не найдено"
        )
    return tasks

# GET TASK BY ID - Получить задачу по ID
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )
    
    days_deadline = calculate_days_until_deadline(task.deadline_at)
    task_dict = task.__dict__.copy()
    task_dict['days_until_deadline'] = days_deadline

    if task.deadline_at is not None and days_deadline is not None and days_deadline < 0:
        task_dict['status_message'] = "Задача просрочена"
    else:
        task_dict['status_message'] = "Всё идёт по плану!"
    return TaskResponse(**task_dict)

# POST - СОЗДАНИЕ НОВОЙ ЗАДАЧИ
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    is_urgent = calculate_urgency(task.deadline_at)
    quadrant = determine_quadrant(task.is_important, is_urgent)
    
    new_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        is_urgent=is_urgent,
        quadrant=quadrant,
        completed=False,
        deadline_at=task.deadline_at,
        user_id = current_user.id
    )
 
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    return new_task

# PUT - ОБНОВЛЕНИЕ ЗАДАЧИ
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Задача не найдена"
        )
    
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )
    
    update_data = task_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(task, field, value) # task.field = value
    
    if "is_important" in update_data or "deadline_at" in update_data:
        task.is_urgent = calculate_urgency(task.deadline_at)
        task.quadrant = quadrant = determine_quadrant(task.is_important, task.is_urgent)
    
    await db.commit()
    await db.refresh(task)

    task_dict = task.__dict__.copy()
    task_dict['days_until_deadline'] = calculate_days_until_deadline(task.deadline_at)
 
    return TaskResponse(**task_dict)

# DELETE - УДАЛЕНИЕ ЗАДАЧИ
@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )

    deleted_task_info = {
        "id": task.id,
        "title": task.title
    }
    await db.delete(task)
    await db.commit()
    return {
        "message": "Задача успешно удалена",
        "id": deleted_task_info["id"],
        "title": deleted_task_info["title"]
    }

# PATCH - ОТМЕТИТЬ ЗАДАЧУ ВЫПОЛНЕННОЙ
@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    if current_user.role.value != "admin" and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой задаче"
        )
    
    task.completed = True
    task.completed_at = datetime.now()
 
    await db.commit()
    await db.refresh(task)

    task_dict = task.__dict__.copy()
    task_dict['days_until_deadline'] = calculate_days_until_deadline(task.deadline_at)
 
    return task