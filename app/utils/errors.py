from fastapi import HTTPException, status
from typing import Optional, Dict, Any, Type
from pydantic import BaseModel, ValidationError

# Custom exception classes
class NotFoundError(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class BadRequestError(HTTPException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class UnauthorizedError(HTTPException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class ConflictError(HTTPException):
    def __init__(self, detail: str = "Conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class ServerError(HTTPException):
    def __init__(self, detail: str = "Internal server error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

# Error handler for validation errors
def handle_validation_error(exc: ValidationError, model: Type[BaseModel]) -> Dict[str, Any]:
    errors = {}
    for error in exc.errors():
        field_name = error["loc"][0]
        errors[field_name] = error["msg"]
    
    return {
        "success": False,
        "error": "Validation error",
        "details": errors
    }

# Function to handle database errors
def handle_db_error(exc: Exception) -> Dict[str, Any]:
    error_message = str(exc)
    
    # Handle specific database errors
    if "UNIQUE constraint failed" in error_message:
        return {
            "success": False,
            "error": "Resource already exists",
            "details": {"message": error_message}
        }
    elif "FOREIGN KEY constraint failed" in error_message:
        return {
            "success": False,
            "error": "Referenced resource not found",
            "details": {"message": error_message}
        }
    else:
        return {
            "success": False,
            "error": "Database error",
            "details": {"message": error_message}
        }