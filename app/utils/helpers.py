import os
import uuid
import csv
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from fastapi import UploadFile
from PIL import Image
import numpy as np

from app.config.config import settings
from loguru import logger

# Date and time helpers
def get_current_time() -> datetime:
    """Get current UTC time"""
    return datetime.utcnow()

def format_date(date: datetime, format_str: str = "%Y-%m-%d") -> str:
    """Format date to string"""
    return date.strftime(format_str)

def parse_date(date_str: str, format_str: str = "%Y-%m-%d") -> datetime:
    """Parse string to date"""
    return datetime.strptime(date_str, format_str)

def get_date_range(start_date: datetime, end_date: datetime) -> List[datetime]:
    """Get list of dates between start and end date"""
    delta = end_date - start_date
    return [start_date + timedelta(days=i) for i in range(delta.days + 1)]

def is_weekend(date: datetime) -> bool:
    """Check if date is weekend (Saturday or Sunday)"""
    return date.weekday() >= 5  # 5 = Saturday, 6 = Sunday

# File helpers
def ensure_directory_exists(directory_path: Union[str, Path]) -> None:
    """Ensure directory exists, create if not"""
    Path(directory_path).mkdir(parents=True, exist_ok=True)

async def save_upload_file(upload_file: UploadFile, destination: Union[str, Path]) -> Path:
    """Save uploaded file to destination"""
    destination_path = Path(destination)
    ensure_directory_exists(destination_path.parent)
    
    # Create a temporary file to store the uploaded content
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        # Copy uploaded file to temporary file
        shutil.copyfileobj(upload_file.file, temp_file)
    
    # Move temporary file to destination
    shutil.move(temp_file.name, destination_path)
    
    return destination_path

def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename with UUID"""
    ext = os.path.splitext(original_filename)[1]
    return f"{uuid.uuid4()}{ext}"

def read_csv_file(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Read CSV file and return list of dictionaries"""
    data = []
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append(row)
    return data

# Image processing helpers for OCR
def preprocess_image_for_ocr(image_path: Union[str, Path]) -> np.ndarray:
    """Preprocess image for OCR to improve text recognition"""
    # Read image with PIL instead of cv2
    img = Image.open(str(image_path))
    
    # Convert to grayscale
    gray = img.convert('L')
    
    # Convert to numpy array
    gray_array = np.array(gray)
    
    # Apply simple threshold
    binary = np.where(gray_array > 150, 255, 0)
    
    return binary

def enhance_image_for_ocr(image_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None) -> Union[str, Path]:
    """Enhance image for OCR and save to output path"""
    # Open image with PIL
    img = Image.open(image_path)
    
    # Convert to grayscale
    img = img.convert('L')
    
    # Increase contrast
    enhancer = Image.enhancer.Contrast(img)
    img = enhancer.enhance(2.0)
    
    # Sharpen image
    enhancer = Image.enhancer.Sharpness(img)
    img = enhancer.enhance(2.0)
    
    # Save enhanced image
    if output_path is None:
        output_path = f"{image_path}_enhanced.jpg"
    
    img.save(output_path)
    return output_path

# Data validation helpers
def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    # Simple validation - can be enhanced based on requirements
    return phone.isdigit() and len(phone) >= 10

def validate_email(email: str) -> bool:
    """Validate email format"""
    # Simple validation - can be enhanced based on requirements
    return '@' in email and '.' in email.split('@')[1]

# ID validation helpers
def validate_id_number(id_type: str, id_number: str) -> bool:
    """Validate ID number based on ID type"""
    if id_type.lower() == "passport":
        # Passport validation logic
        return len(id_number) >= 6 and any(c.isalpha() for c in id_number)
    elif id_type.lower() == "aadhar":
        # Aadhar validation logic (India)
        return len(id_number) == 12 and id_number.isdigit()
    elif id_type.lower() == "driving_license":
        # Driving license validation logic
        return len(id_number) >= 8
    else:
        # Generic validation
        return len(id_number) >= 4

# Generate random data for testing
def generate_test_data(count: int = 10) -> List[Dict[str, Any]]:
    """Generate random test data for development"""
    data = []
    for i in range(count):
        data.append({
            "name": f"Test Guest {i+1}",
            "email": f"guest{i+1}@example.com",
            "phone": f"98765{i:05d}",
            "id_type": "passport",
            "id_number": f"AB{i:06d}",
            "is_premium": i % 3 == 0,
        })
    return data