from typing import List, Optional
from datetime import datetime, timedelta
import secrets
from sqlmodel import Session, select

from app.models.models import User
from app.schemas.schemas import UserCreate, UserUpdate
from app.auth.auth import get_password_hash, verify_password
from app.utils.errors import NotFoundError, BadRequestError
from loguru import logger

class UserService:
    def __init__(self, session: Session):
        self.session = session
        self.password_reset_tokens = {}  # In-memory storage for reset tokens
    
    async def create_user(self, user_data: UserCreate) -> User:
        # Check if email already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role
        )
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        
        logger.info(f"Created new user: {user.email} with role {user.role}")
        return user
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    async def get_user(self, user_id: int) -> Optional[User]:
        statement = select(User).where(User.id == user_id)
        results = self.session.exec(statement)
        return results.first()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        statement = select(User).where(User.email == email)
        results = self.session.exec(statement)
        return results.first()
    
    async def get_users(self, limit: int = 100, skip: int = 0) -> List[User]:
        statement = select(User).offset(skip).limit(limit)
        results = self.session.exec(statement)
        return results.all()
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError(f"User not found: {user_id}")
        
        # Update fields if provided
        if user_data.email is not None:
            # Check if email is being changed and if it already exists
            if user_data.email != user.email:
                existing_user = await self.get_user_by_email(user_data.email)
                if existing_user:
                    raise ValueError(f"User with email {user_data.email} already exists")
            user.email = user_data.email
        
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        
        if user_data.role is not None:
            user.role = user_data.role
        
        if user_data.password is not None:
            user.hashed_password = get_password_hash(user_data.password)
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        
        logger.info(f"Updated user: {user.id}")
        return user
    
    async def delete_user(self, user_id: int) -> None:
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError(f"User not found: {user_id}")
        
        self.session.delete(user)
        self.session.commit()
        
        logger.info(f"Deleted user: {user.id}")
    
    async def count_admin_users(self) -> int:
        statement = select(User).where(User.role == "admin")
        results = self.session.exec(statement)
        return len(results.all())
    
    async def create_password_reset_token(self, user_id: int) -> str:
        # Generate a secure token
        token = secrets.token_urlsafe(32)
        
        # Store token with expiration time (24 hours)
        expiration = datetime.utcnow() + timedelta(hours=24)
        self.password_reset_tokens[token] = {"user_id": user_id, "expires": expiration}
        
        logger.info(f"Created password reset token for user: {user_id}")
        return token
    
    async def verify_password_reset_token(self, token: str) -> Optional[int]:
        # Check if token exists and is valid
        token_data = self.password_reset_tokens.get(token)
        if not token_data:
            return None
        
        # Check if token has expired
        if datetime.utcnow() > token_data["expires"]:
            # Remove expired token
            del self.password_reset_tokens[token]
            return None
        
        # Token is valid, return user ID
        return token_data["user_id"]
    
    async def update_password(self, user_id: int, new_password: str) -> None:
        user = await self.get_user(user_id)
        if not user:
            raise NotFoundError(f"User not found: {user_id}")
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        
        self.session.add(user)
        self.session.commit()
        
        logger.info(f"Updated password for user: {user_id}")
        
        # Remove any reset tokens for this user
        for token, data in list(self.password_reset_tokens.items()):
            if data["user_id"] == user_id:
                del self.password_reset_tokens[token]
    
    async def create_initial_admin(self, email: str, password: str, full_name: str) -> User:
        """Create initial admin user if no users exist"""
        # Check if any users exist
        statement = select(User)
        results = self.session.exec(statement)
        if results.first():
            logger.info("Initial admin creation skipped - users already exist")
            return None
        
        # Create admin user
        admin = UserCreate(
            email=email,
            password=password,
            full_name=full_name,
            role="admin"
        )
        
        user = await self.create_user(admin)
        logger.info(f"Created initial admin user: {user.email}")
        return user