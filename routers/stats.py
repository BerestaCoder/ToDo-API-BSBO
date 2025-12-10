from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from models import Task
from typing import List
from database import get_async_session
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/stats",
    tags=["statistics"]
)
@router.get("/", response_model=dict)
async def get_tasks_stats(db: AsyncSession = Depends(get_async_session)) -> dict:
    result = await db.execute(select(Task))
    tasks = result.scalars().all() 
    total_tasks = len(tasks)
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    by_status = {"completed": 0, "pending": 0}
    
    for task in tasks:
        if task.quadrant in by_quadrant:
            by_quadrant[task.quadrant] += 1
        if task.completed:
            by_status["completed"] += 1
        else:
            by_status["pending"] += 1

    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": by_status
    }

@router.get("/urgent", response_model=List[dict])
async def get_tasks_stats(db: AsyncSession = Depends(get_async_session)) -> dict:
    now = datetime.now()
    result = await db.execute(
        select(Task).where(and_(
            Task.deadline_at >= now,
            Task.deadline_at <= now + timedelta(days=3)
            )
        )
    )
    tasks = result.scalars().all()
    formatted_tasks = []
    for task in tasks:
        remaining_days = (task.deadline_at - now).days
        
        formatted_tasks.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "remaining_days": max(remaining_days, 0)  # предотвращаем отрицательные дни
        })

    return formatted_tasks

    return formated_tasks