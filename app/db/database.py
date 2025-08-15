from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os
from app.config import settings
from loguru import logger

# Create database directory if it doesn't exist
def ensure_db_directory():
    """Ensure the database directory exists"""
    if settings.DATABASE_URL.startswith("sqlite:///"):
        db_path = settings.DATABASE_URL.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_path)
        if db_dir:  # Only create directory if there's a path
            os.makedirs(db_dir, exist_ok=True)

ensure_db_directory()

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO_LOG,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True
)

# Create database session
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise

# Create database tables
def create_db_and_tables():
    logger.info(f"Creating database tables using {settings.DATABASE_URL}")
    SQLModel.metadata.create_all(engine)

# Initialize database
async def init_db():
    """Initialize database with required initial data"""
    create_db_and_tables()
    
    from app.services.user_service import UserService
    from app.services.room_service import RoomService
    from sqlmodel import Session
    
    with Session(engine) as session:
        # Create initial admin user if no users exist
        user_service = UserService(session)
        user_service.create_initial_admin(
            email=settings.INITIAL_ADMIN_EMAIL,
            password=settings.INITIAL_ADMIN_PASSWORD,
            full_name="System Administrator"
        )
        
        # Seed initial room data if no rooms exist
        room_service = RoomService(session)
        await room_service.seed_rooms()
        
        logger.info("Database initialized with initial data")