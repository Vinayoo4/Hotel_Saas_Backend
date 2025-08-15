from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.config.config import settings
from app.db.database import get_session
from app.models.models import User
from app.schemas.schemas import TokenData

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Verify password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Hash password
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Authenticate user
def authenticate_user(session: Session, username: str, password: str) -> Optional[User]:
    # Try to find user by username or email
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        # Try email as fallback
        user = session.exec(select(User).where(User.email == username)).first()
    
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# Create access token
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

# Get current user
async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception
    user = session.exec(select(User).where(User.email == token_data.username)).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user

# Get current active user
async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user

# Check if user is admin
async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not enough permissions"
        )
    return current_user

# Check user role
async def check_user_role(required_role: str, current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.is_superuser or current_user.role == required_role or current_user.role == "admin":
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, 
        detail=f"Role '{required_role}' required"
    )

# Get admin user dependency
def get_admin_user():
    return Depends(get_current_admin_user)

# Get receptionist user dependency
def get_receptionist_user():
    return Depends(lambda user: check_user_role("receptionist", user))

# Get manager user dependency
def get_manager_user():
    return Depends(lambda user: check_user_role("manager", user))