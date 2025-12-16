from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_async_session
from models import User, Task
from dependencies import get_current_user

router = APIRouter(
    prefix="/admin",
    tags=["administration"]
    )

@router.get("/users") # Список пользователей с количеством задач
async def register(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.value != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен",
        )
    result = await db.execute(
        select(User.id, User.nickname, User.email, func.count(Task.id).label("task_count"))
        .select_from(User)
        .outerjoin(Task, User.id == Task.user_id)
        .group_by(User.id)
    )
    users = [
        {
            "id": row.id,
            "nickname": row.nickname,
            "email": row.email,
            "task_count": row.task_count
        }
        for row in result
    ]
    return users