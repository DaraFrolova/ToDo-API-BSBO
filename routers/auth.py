from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_async_session
from models.user import User, UserRole
from schemas_auth import UserCreate, UserResponse, Token, ChangePasswordRequest, AdminUserResponse
from auth_utils import verify_password, get_password_hash, create_access_token
from dependencies import get_current_user, get_current_admin
from models.task import Task

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_session)
):
    # Проверка email
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    # Проверка nickname
    result = await db.execute(select(User).where(User.nickname == user_data.nickname))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким никнеймом уже существует"
        )
    new_user = User(
        nickname=user_data.nickname,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=UserRole.USER
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user

@router.patch("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    passwords: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    if not verify_password(passwords.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Старый пароль неверен"
        )
    current_user.hashed_password = get_password_hash(passwords.new_password)
    await db.commit()
    return {"message": "Пароль успешно изменён"}

# Эндпоинт для администраторов
@router.get("/admin/users", response_model=list[AdminUserResponse])
async def get_all_users(
    db: AsyncSession = Depends(get_async_session),
    admin_user: User = Depends(get_current_admin)
):
    from sqlalchemy.orm import joinedload
    result = await db.execute(
        select(User).options(joinedload(User.tasks))
    )
    users = result.unique().scalars().all()
    response = []
    for user in users:
        response.append(
            AdminUserResponse(
                id=user.id,
                nickname=user.nickname,
                email=user.email,
                role=user.role.value,
                task_count=len(user.tasks)
            )
        )
    return response