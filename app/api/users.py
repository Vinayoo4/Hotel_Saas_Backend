from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.db.database import get_session
from app.schemas.schemas import UserCreate, UserRead, UserUpdate, Token, UserList
from app.services.user_service import UserService
from app.services.email_service import EmailService
from app.auth.auth import (
    get_current_active_user,
    get_current_admin_user,
    create_access_token,
    verify_password,
    get_password_hash
)
from app.utils.errors import NotFoundError, BadRequestError, UnauthorizedError
from loguru import logger

router = APIRouter(prefix="/users", tags=["users"])
auth_router = APIRouter(tags=["auth"])

@auth_router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """Authenticate user and return JWT token"""
    user_service = UserService(session)
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_admin_user)
):
    """Create a new user (admin only)"""
    user_service = UserService(session)
    try:
        return await user_service.create_user(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=UserList)
async def get_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_admin_user)
):
    """Get all users (admin only)"""
    user_service = UserService(session)
    users = await user_service.get_users(limit, skip)
    return {"users": users, "total": len(users)}

@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_active_user)
):
    """Get current user information"""
    user_service = UserService(session)
    user = await user_service.get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_admin_user)
):
    """Get a specific user by ID (admin only)"""
    user_service = UserService(session)
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User not found: {user_id}")
    return user

@router.put("/me", response_model=UserRead)
async def update_current_user(
    user_update: UserUpdate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_active_user)
):
    """Update current user information"""
    user_service = UserService(session)
    try:
        user = await user_service.get_user_by_email(current_user["email"])
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # Prevent role change through this endpoint
        if user_update.role and user_update.role != user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to change role"
            )
        
        return await user_service.update_user(user.id, user_update)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_admin_user)
):
    """Update a specific user (admin only)"""
    user_service = UserService(session)
    try:
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User not found: {user_id}")
        
        return await user_service.update_user(user_id, user_update)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_admin_user)
):
    """Delete a user (admin only)"""
    user_service = UserService(session)
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User not found: {user_id}")
    
    # Prevent deleting the last admin user
    if user.role == "admin":
        admin_count = await user_service.count_admin_users()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin user"
            )
    
    await user_service.delete_user(user_id)

@router.post("/reset-password/request")
async def request_password_reset(
    email: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """Request a password reset link"""
    user_service = UserService(session)
    email_service = EmailService()
    
    user = await user_service.get_user_by_email(email)
    if not user:
        # Don't reveal if email exists or not for security reasons
        return {"message": "If your email is registered, you will receive a password reset link"}
    
    # Generate reset token
    reset_token = await user_service.create_password_reset_token(user.id)
    
    # Send email with reset link in background
    background_tasks.add_task(
        email_service.send_password_reset_email,
        user.email,
        user.full_name,
        reset_token
    )
    
    return {"message": "If your email is registered, you will receive a password reset link"}

@router.post("/reset-password/confirm")
async def confirm_password_reset(
    token: str,
    new_password: str,
    session: Session = Depends(get_session)
):
    """Reset password using the token received via email"""
    user_service = UserService(session)
    
    try:
        user_id = await user_service.verify_password_reset_token(token)
        if not user_id:
            raise BadRequestError("Invalid or expired token")
        
        await user_service.update_password(user_id, new_password)
        return {"message": "Password has been reset successfully"}
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password"
        )

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_active_user)
):
    """Change user's password (requires current password)"""
    user_service = UserService(session)
    
    try:
        user = await user_service.get_user_by_email(current_user["email"])
        if not user:
            raise NotFoundError("User not found")
        
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect")
        
        # Update password
        await user_service.update_password(user.id, new_password)
        return {"message": "Password changed successfully"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))